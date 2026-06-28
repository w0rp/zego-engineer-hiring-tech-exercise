from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterator
from concurrent.futures import (
    FIRST_COMPLETED,
    Future,
    ThreadPoolExecutor,
    wait,
)
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import SplitResult, urldefrag, urljoin, urlsplit, urlunsplit

import httpx

FetchPage = Callable[[str, float], str]
ErrorHandler = Callable[[str, Exception], None]
USER_AGENT = "zego-tech-exercise-crawler/0.1"


@dataclass(frozen=True)
class CrawlConfig:
    concurrency: int = 10
    timeout: float = 10.0
    max_pages: int | None = None

    def __post_init__(self) -> None:
        if self.concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        if self.timeout <= 0:
            raise ValueError("timeout must be greater than 0")
        if self.max_pages is not None and self.max_pages < 1:
            raise ValueError("max-pages must be at least 1")


@dataclass(frozen=True)
class PageLinks:
    url: str
    links: tuple[str, ...]


class _AnchorParser(HTMLParser):
    """A parser for grabbing links from <a> tags."""
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._base_url = base_url
        self._seen: set[str] = set()

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "a":
            return

        for name, value in attrs:
            if name.lower() == "href" and value:
                url = normalize_url(value, base_url=self._base_url)
                if url is not None:
                    self._seen.add(url)
                return

    def links(self) -> tuple[str, ...]:
        """Grab parsed links from the parser."""
        return tuple(sorted(self._seen))


def crawl_site(
    base_url: str,
    config: CrawlConfig | None = None,
    *,
    fetch_page: FetchPage | None = None,
    on_error: ErrorHandler | None = None,
) -> Iterator[PageLinks]:
    """
    Crawl a site and yield pages with links as they are parsed.

    Results for links that are followed might appear in any order as pages
    are loaded.
    """
    crawl_config = config or CrawlConfig()
    normalized_base_url = normalize_url(base_url)
    if normalized_base_url is None:
        raise ValueError("base URL must be an absolute HTTP or HTTPS URL")

    base_hostname = _hostname(normalized_base_url)
    if base_hostname is None:
        raise ValueError("base URL must include a hostname")

    queue: deque[str] = deque([normalized_base_url])
    scheduled = {normalized_base_url}

    if fetch_page is not None:
        yield from _crawl_with_fetcher(
            crawl_config,
            fetch_page,
            base_hostname,
            queue,
            scheduled,
            on_error,
        )
        return

    limits = httpx.Limits(
        max_connections=crawl_config.concurrency,
        max_keepalive_connections=crawl_config.concurrency,
    )
    with httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        limits=limits,
    ) as client:
        def fetch_with_client(url: str, timeout: float) -> str:
            return default_fetch_page(client, url, timeout)

        yield from _crawl_with_fetcher(
            crawl_config,
            fetch_with_client,
            base_hostname,
            queue,
            scheduled,
            on_error,
        )


def default_fetch_page(
    client: httpx.Client,
    url: str,
    timeout: float,
) -> str:
    response = client.get(url, timeout=timeout)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").split(";")[0]
    if content_type.strip().lower() not in {
        "text/html",
        "application/xhtml+xml",
    }:
        return ""

    return response.text


def _crawl_with_fetcher(
    config: CrawlConfig,
    fetch_page: FetchPage,
    base_hostname: str,
    queue: deque[str],
    scheduled: set[str],
    on_error: ErrorHandler | None,
) -> Iterator[PageLinks]:
    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        pending: dict[Future[PageLinks], str] = {}

        while queue or pending:
            _submit_pending(
                executor,
                queue,
                pending,
                config,
                fetch_page,
            )
            if not pending:
                break

            completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                url = pending.pop(future)
                try:
                    page_links = future.result()
                except Exception as exc:
                    if on_error is not None:
                        on_error(url, exc)
                    continue

                _queue_same_domain_links(
                    page_links,
                    base_hostname,
                    scheduled,
                    queue,
                    config.max_pages,
                )
                _submit_pending(
                    executor,
                    queue,
                    pending,
                    config,
                    fetch_page,
                )
                yield page_links


def extract_links(html: str, base_url: str) -> tuple[str, ...]:
    parser = _AnchorParser(base_url)
    parser.feed(html)
    parser.close()
    return parser.links()


def normalize_url(raw_url: str, *, base_url: str | None = None) -> str | None:
    stripped_url = raw_url.strip()
    if not stripped_url:
        return None

    joined_url = urljoin(base_url, stripped_url) if base_url else stripped_url
    defragmented_url, _ = urldefrag(joined_url)
    split_url = urlsplit(defragmented_url)
    if split_url.scheme.lower() not in {"http", "https"}:
        return None
    if split_url.hostname is None:
        return None

    return urlunsplit(_normalized_parts(split_url))


def _submit_pending(
    executor: ThreadPoolExecutor,
    queue: deque[str],
    pending: dict[Future[PageLinks], str],
    config: CrawlConfig,
    fetch_page: FetchPage,
) -> None:
    while queue and len(pending) < config.concurrency:
        url = queue.popleft()
        future = executor.submit(_crawl_one, url, config.timeout, fetch_page)
        pending[future] = url


def _crawl_one(
    url: str,
    timeout: float,
    fetch_page: FetchPage,
) -> PageLinks:
    html = fetch_page(url, timeout)
    return PageLinks(url=url, links=extract_links(html, url))


def _queue_same_domain_links(
    page_links: PageLinks,
    base_hostname: str,
    scheduled: set[str],
    queue: deque[str],
    max_pages: int | None,
) -> None:
    for link in page_links.links:
        if _hostname(link) != base_hostname:
            continue
        if link in scheduled:
            continue
        if max_pages is not None and len(scheduled) >= max_pages:
            continue

        scheduled.add(link)
        queue.append(link)


def _normalized_parts(
    split_url: SplitResult,
) -> tuple[str, str, str, str, str]:
    scheme = split_url.scheme.lower()
    hostname = split_url.hostname
    if hostname is None:
        msg = "URL must include a hostname"
        raise ValueError(msg)

    port = split_url.port
    default_port = scheme == "http" and port == 80
    default_secure_port = scheme == "https" and port == 443
    netloc = hostname.lower()
    if port is not None and not default_port and not default_secure_port:
        netloc = f"{netloc}:{port}"

    return scheme, netloc, split_url.path or "/", split_url.query, ""


def _hostname(url: str) -> str | None:
    hostname = urlsplit(url).hostname
    return hostname.lower() if hostname else None
