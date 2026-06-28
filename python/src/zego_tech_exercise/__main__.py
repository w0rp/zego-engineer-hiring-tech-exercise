from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable

from zego_tech_exercise.crawler import CrawlConfig, PageLinks, crawl_site


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    config = CrawlConfig(
        concurrency=args.concurrency,
        timeout=args.timeout,
        max_pages=args.max_pages,
    )
    print_pages_as_loaded(
        crawl_site(
            args.url,
            config,
            on_error=_print_warning,
        ),
    )

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crawl one domain and print links found on each page.",
    )
    parser.add_argument("url", help="Base HTTP or HTTPS URL to crawl.")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Maximum concurrent page fetches. Defaults to 10.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP request timeout in seconds. Defaults to 10.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of same-domain pages to attempt.",
    )
    return parser


def _print_warning(url: str, exc: Exception) -> None:
    print(f"warning: failed to crawl {url}: {exc}", file=sys.stderr)


def print_pages_as_loaded(pages: Iterable[PageLinks]) -> None:
    for page in pages:
        print(page.url)
        for link in page.links:
            print(f"  {link}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())  # pragma: no cover
