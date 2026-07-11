from scraper.models import CrawlSummary, ManifestEntry
from scraper.reporting import build_crawl_report


def test_build_crawl_report_summarizes_quality_metrics():
    summary = CrawlSummary(
        pages_requested=4,
        pages_visited=3,
        downloads_saved=2,
        skipped_urls=[
            {"url": "https://authorized.local/a", "reason": "duplicate"},
            {"url": "https://elsewhere.local/b", "reason": "outside allowed domain"},
        ],
        failed_urls=[{"url": "https://authorized.local/missing", "reason": "non-retryable status 404"}],
        status_counts={"200": 3, "404": 1},
        response_times_ms=[10.0, 20.0, 30.0],
    )
    entries = [
        ManifestEntry("https://authorized.local/a", "Book A", "a.txt", "txt", "saved", "2026-03-27T00:00:00+00:00"),
        ManifestEntry("https://authorized.local/b", "untitled", "b.txt", "txt", "saved", "2026-03-27T00:00:00+00:00"),
    ]

    report = build_crawl_report(summary, entries)

    assert report["pages_requested"] == 4
    assert report["pages_succeeded"] == 3
    assert report["pages_failed"] == 1
    assert report["duplicates_removed"] == 1
    assert report["records_missing_title"] == 1
    assert report["average_response_ms"] == 20.0
