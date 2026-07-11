from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scraper.models import CrawlSummary, ManifestEntry


def build_crawl_report(summary: CrawlSummary, entries: list[ManifestEntry]) -> dict[str, object]:
    skipped_counts = Counter(item.get("reason", "unknown") for item in summary.skipped_urls)
    failed_counts = Counter(item.get("reason", "unknown") for item in summary.failed_urls)
    average_response_ms = (
        round(sum(summary.response_times_ms) / len(summary.response_times_ms), 2)
        if summary.response_times_ms
        else None
    )

    return {
        "pages_requested": summary.pages_requested,
        "pages_succeeded": summary.pages_visited,
        "pages_failed": len(summary.failed_urls),
        "downloads_saved": summary.downloads_saved,
        "duplicates_removed": skipped_counts.get("duplicate", 0),
        "records_missing_title": _count_missing_titles(entries),
        "average_response_ms": average_response_ms,
        "status_counts": dict(sorted(summary.status_counts.items())),
        "skipped_by_reason": dict(sorted(skipped_counts.items())),
        "failed_by_reason": dict(sorted(failed_counts.items())),
    }


def write_crawl_report(output_dir: Path, report: dict[str, object]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "crawl_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def _count_missing_titles(entries: list[ManifestEntry]) -> int:
    return sum(1 for entry in entries if not entry.title.strip() or entry.title.strip().lower() == "untitled")
