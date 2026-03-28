import json

from scraper.clients import FixtureClient
from scraper.crawler import PermissionCrawler
from scraper.models import CrawlOptions, RateLimit, RetryPolicy


def build_options(tmp_path, mode="text-only"):
    return CrawlOptions(
        start_url="https://authorized.local/library/index.html",
        mode=mode,
        allowed_domains=["authorized.local"],
        max_pages=5,
        max_depth=2,
        output_dir=tmp_path,
        allowed_file_types=["html", "txt", "pdf", "epub", "md"],
        selectors=[".chapter"],
        follow_links=True,
        overwrite=True,
        save_format="json",
        rate_limit=RateLimit(requests_per_second=1000),
        retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.01, backoff_multiplier=2.0),
    )


def test_crawler_prevents_duplicate_visits_and_respects_domain(tmp_path):
    crawler = PermissionCrawler(client=FixtureClient("tests/fixtures"), sleep_fn=lambda _seconds: None, jitter_fn=lambda _a, _b: 0)

    manifest_path, summary = crawler.crawl(build_options(tmp_path, mode="text-only"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert summary.pages_visited == 3
    assert "https://authorized.local/library/book-1.html" in summary.visited_urls
    assert any(item["reason"] == "outside allowed domain" for item in summary.skipped_urls)
    assert any(item["reason"] == "duplicate" for item in summary.skipped_urls)
    assert len(manifest) == 3


def test_crawler_linked_documents_mode_downloads_allowed_documents(tmp_path):
    crawler = PermissionCrawler(client=FixtureClient("tests/fixtures"), sleep_fn=lambda _seconds: None, jitter_fn=lambda _a, _b: 0)
    options = build_options(tmp_path, mode="linked-documents")
    options.allowed_file_types = ["pdf", "epub"]

    manifest_path, summary = crawler.crawl(options)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert summary.downloads_saved == 1
    assert (tmp_path / "documents").exists()
    assert any(entry["content_type"] == "pdf" for entry in manifest)
