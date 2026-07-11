from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


AUTHORIZED_USE_WARNING = (
    "Authorized/public-domain use only. Crawl only websites you own, have explicit permission to download from, "
    "or clearly public-domain/open-license sources."
)


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    retryable_statuses: tuple[int, ...] = (408, 429, 500, 502, 503, 504)


@dataclass(slots=True)
class RateLimit:
    requests_per_second: float = 1.0


@dataclass(slots=True)
class CrawlOptions:
    start_url: str
    mode: str
    allowed_domains: list[str]
    max_pages: int
    max_depth: int
    output_dir: Path
    allowed_file_types: list[str] = field(default_factory=lambda: ["html", "txt", "pdf", "epub"])
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    selectors: list[str] = field(default_factory=list)
    follow_links: bool = True
    overwrite: bool = False
    respect_robots: bool = True
    save_format: str = "json"
    rate_limit: RateLimit = field(default_factory=RateLimit)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    user_agent: str = "PermissionCrawler/1.0 (+authorized-use-only)"


@dataclass(slots=True)
class CrawlRequest:
    url: str
    depth: int


@dataclass(slots=True)
class FetchResult:
    url: str
    status_code: int | None
    content: bytes | None
    headers: dict[str, str]
    attempt_count: int
    error: str | None = None
    elapsed_ms: float | None = None

    @property
    def ok(self) -> bool:
        return self.content is not None and self.error is None

    @property
    def content_type(self) -> str:
        return self.headers.get("Content-Type", "")

    @property
    def text(self) -> str:
        return (self.content or b"").decode("utf-8", errors="replace")


@dataclass(slots=True)
class ManifestEntry:
    source_url: str
    title: str
    local_filename: str
    content_type: str
    status: str
    timestamp: str
    note: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "source_url": self.source_url,
            "title": self.title,
            "local_filename": self.local_filename,
            "content_type": self.content_type,
            "status": self.status,
            "timestamp": self.timestamp,
            "note": self.note,
        }


@dataclass(slots=True)
class CrawlSummary:
    pages_requested: int = 0
    pages_visited: int = 0
    downloads_saved: int = 0
    skipped_urls: list[dict[str, str]] = field(default_factory=list)
    failed_urls: list[dict[str, str]] = field(default_factory=list)
    visited_urls: list[str] = field(default_factory=list)
    status_counts: dict[str, int] = field(default_factory=dict)
    response_times_ms: list[float] = field(default_factory=list)
    report_path: str = ""
