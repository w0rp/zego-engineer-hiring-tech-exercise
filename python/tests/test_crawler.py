import sys
from threading import Event

import httpx
import pytest
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from zego_tech_exercise.__main__ import main, print_pages_as_loaded
from zego_tech_exercise.crawler import (
    CrawlConfig,
    PageLinks,
    crawl_site,
    default_fetch_page,
    extract_links,
    normalize_url,
)


def test_normalize_url_resolves_relative_links_and_removes_fragments() -> None:
    assert (
        normalize_url(
            "../About?x=1#team",
            base_url="HTTPS://Example.test:443/a/b/",
        )
        == "https://example.test/a/About?x=1"
    )


def test_normalize_url_ignores_non_http_urls() -> None:
    assert normalize_url("mailto:hello@example.test") is None
    assert normalize_url("javascript:void(0)") is None


def test_extract_links_reads_anchor_href_values_only() -> None:
    html = """
    <a href="/about">About</a>
    <area href="/ignored">
    <a href="#fragment">Same page</a>
    <a href="https://other.test/">External</a>
    <a href="/about">Duplicate</a>
    """

    assert extract_links(html, "https://example.test/") == (
        "https://example.test/",
        "https://example.test/about",
        "https://other.test/",
    )


def test_default_fetch_page_uses_httpx_client() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"]
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text='<a href="/about">About</a>',
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert (
            default_fetch_page(client, "https://example.test/", timeout=1)
            == '<a href="/about">About</a>'
        )


def test_default_fetch_page_skips_non_html() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            text='{"ok": true}',
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert default_fetch_page(client, "https://example.test/", 1) == ""


def test_crawl_site_crawls_same_domain_links_only() -> None:
    pages = {
        "https://example.test/": """
            <a href="/about">About</a>
            <a href="https://blog.example.test/">Blog</a>
            <a href="https://external.test/">External</a>
        """,
        "https://example.test/about": '<a href="/">Home</a>',
    }

    def fake_fetch(url: str, timeout: float) -> str:
        del timeout
        return pages[url]

    result = list(
        crawl_site(
            "https://example.test",
            CrawlConfig(concurrency=2),
            fetch_page=fake_fetch,
        ),
    )

    assert result == [
        PageLinks(
            url="https://example.test/",
            links=(
                "https://blog.example.test/",
                "https://example.test/about",
                "https://external.test/",
            ),
        ),
        PageLinks(
            url="https://example.test/about",
            links=("https://example.test/",),
        ),
    ]


def test_crawl_site_yields_pages_as_they_are_parsed() -> None:
    def fake_fetch(url: str, timeout: float) -> str:
        del timeout
        if url == "https://example.test/":
            return '<a href="/about">About</a>'
        return ""

    pages = crawl_site(
        "https://example.test",
        CrawlConfig(concurrency=1),
        fetch_page=fake_fetch,
    )

    assert [page.url for page in pages] == [
        "https://example.test/",
        "https://example.test/about",
    ]


def test_crawl_site_submits_discovered_links_before_yielding_page() -> None:
    child_fetch_started = Event()

    def fake_fetch(url: str, timeout: float) -> str:
        del timeout
        if url == "https://example.test/":
            return '<a href="/about">About</a>'

        child_fetch_started.set()
        return ""

    pages = crawl_site(
        "https://example.test",
        CrawlConfig(concurrency=2),
        fetch_page=fake_fetch,
    )

    assert next(pages).url == "https://example.test/"
    assert child_fetch_started.wait(timeout=1)


def test_crawl_site_honours_max_pages() -> None:
    pages = {
        "https://example.test/": """
            <a href="/a">A</a>
            <a href="/b">B</a>
        """,
        "https://example.test/a": "",
        "https://example.test/b": "",
    }

    def fake_fetch(url: str, timeout: float) -> str:
        del timeout
        return pages[url]

    result = list(
        crawl_site(
            "https://example.test/",
            CrawlConfig(concurrency=1, max_pages=2),
            fetch_page=fake_fetch,
        ),
    )

    assert [page.url for page in result] == [
        "https://example.test/",
        "https://example.test/a",
    ]


def test_crawl_site_reports_fetch_errors() -> None:
    errors: list[tuple[str, str]] = []

    def fake_fetch(url: str, timeout: float) -> str:
        del timeout
        if url == "https://example.test/broken":
            raise RuntimeError("boom")
        return '<a href="/broken">Broken</a>'

    result = list(
        crawl_site(
            "https://example.test/",
            CrawlConfig(concurrency=1),
            fetch_page=fake_fetch,
            on_error=lambda url, exc: errors.append((url, str(exc))),
        ),
    )

    assert result == [
        PageLinks(
            url="https://example.test/",
            links=("https://example.test/broken",),
        ),
    ]
    assert errors == [("https://example.test/broken", "boom")]


def test_print_pages_as_loaded(capsys: CaptureFixture[str]) -> None:
    print_pages_as_loaded(
        [
            PageLinks(
                url="https://example.test/",
                links=("https://example.test/about",),
            ),
            PageLinks(url="https://example.test/about", links=()),
        ],
    )

    assert capsys.readouterr().out == (
        "https://example.test/\n"
        "  https://example.test/about\n"
        "https://example.test/about\n"
    )


def test_main(
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "zego_tech_exercise",
            "https://example.test",
            "--max-pages",
            "1",
        ],
    )
    exit_code = main()

    assert exit_code == 0
    output = capsys.readouterr()
    assert output.out == ""
    assert "failed to crawl https://example.test/" in output.err


def test_main_rejects_invalid_urls(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["zego_tech_exercise", "not-a-url"])

    with pytest.raises(ValueError, match="absolute HTTP or HTTPS URL"):
        main()
