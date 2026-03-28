from __future__ import annotations

from pathlib import Path

from scraper.models import CrawlOptions


def ensure_output_path(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def describe_options(options: CrawlOptions) -> dict:
    return {
        "start_url": options.start_url,
        "mode": options.mode,
        "allowed_domains": options.allowed_domains,
        "max_pages": options.max_pages,
        "max_depth": options.max_depth,
        "output_dir": str(options.output_dir),
        "allowed_file_types": options.allowed_file_types,
        "include_patterns": options.include_patterns,
        "exclude_patterns": options.exclude_patterns,
        "selectors": options.selectors,
        "follow_links": options.follow_links,
        "overwrite": options.overwrite,
        "respect_robots": options.respect_robots,
        "save_format": options.save_format,
    }
