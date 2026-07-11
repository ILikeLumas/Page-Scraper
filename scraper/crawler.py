from __future__ import annotations

import logging
import random
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser

from scraper.downloader import ContentDownloader
from scraper.extractor import extract_links, extract_selected_content, extract_text_content, extract_title
from scraper.filters import detect_file_type, domain_allowed, is_document_url, normalize_url, pattern_allowed, should_skip_private_area
from scraper.manifest import ManifestWriter
from scraper.models import CrawlOptions, CrawlRequest, CrawlSummary, FetchResult, ManifestEntry
from scraper.reporting import build_crawl_report, write_crawl_report

LOGGER = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self) -> None:
        self._last_request_at: dict[str, float] = defaultdict(float)

    def wait(self, hostname: str, requests_per_second: float, sleep_fn=time.sleep) -> None:
        if requests_per_second <= 0:
            return
        min_interval = 1.0 / requests_per_second
        elapsed = time.monotonic() - self._last_request_at[hostname]
        if elapsed < min_interval:
            sleep_fn(min_interval - elapsed)
        self._last_request_at[hostname] = time.monotonic()


class PermissionCrawler:
    def __init__(
        self,
        client,
        *,
        timeout_seconds: float = 15.0,
        sleep_fn=time.sleep,
        jitter_fn=random.uniform,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.client = client
        self.timeout_seconds = timeout_seconds
        self.sleep_fn = sleep_fn
        self.jitter_fn = jitter_fn
        self.rate_limiter = rate_limiter or RateLimiter()
        self._robots_cache: dict[str, RobotFileParser | bool] = {}

    def crawl(self, options: CrawlOptions) -> tuple[Path, CrawlSummary]:
        allowed_domains = options.allowed_domains or [urlparse(options.start_url).hostname or ""]
        downloader = ContentDownloader(options.output_dir, overwrite=options.overwrite)
        manifest_writer = ManifestWriter(options.output_dir, format=options.save_format)
        queue = deque([CrawlRequest(url=options.start_url, depth=0)])
        queued_urls: set[str] = {normalize_url(options.start_url, "") or options.start_url}
        visited: set[str] = set()
        summary = CrawlSummary()
        manifest_entries: list[ManifestEntry] = []

        while queue and summary.pages_visited < options.max_pages:
            current = queue.popleft()
            normalized = normalize_url(current.url, "")
            if not normalized:
                continue
            if normalized in visited:
                summary.skipped_urls.append({"url": current.url, "reason": "duplicate"})
                continue
            if current.depth > options.max_depth:
                summary.skipped_urls.append({"url": current.url, "reason": "depth limit"})
                continue
            if not domain_allowed(normalized, allowed_domains):
                summary.skipped_urls.append({"url": current.url, "reason": "outside allowed domain"})
                continue
            if not pattern_allowed(normalized, options.include_patterns, options.exclude_patterns):
                summary.skipped_urls.append({"url": current.url, "reason": "pattern filtered"})
                continue
            if should_skip_private_area(normalized):
                summary.skipped_urls.append({"url": current.url, "reason": "private-area safeguard"})
                continue
            if options.respect_robots and not self._allowed_by_robots(normalized, options):
                summary.skipped_urls.append({"url": current.url, "reason": "robots.txt disallow"})
                continue

            visited.add(normalized)
            queued_urls.discard(normalized)
            summary.visited_urls.append(normalized)
            summary.pages_requested += 1

            fetch_result = self.fetch(normalized, options)
            if fetch_result.status_code is not None:
                status_key = str(fetch_result.status_code)
                summary.status_counts[status_key] = summary.status_counts.get(status_key, 0) + 1
            if fetch_result.elapsed_ms is not None:
                summary.response_times_ms.append(fetch_result.elapsed_ms)
            if not fetch_result.ok:
                summary.failed_urls.append({"url": normalized, "reason": fetch_result.error or "fetch failure"})
                continue

            summary.pages_visited += 1
            file_type = detect_file_type(normalized, fetch_result.content_type)
            if is_document_url(normalized, options.allowed_file_types, fetch_result.content_type):
                if options.mode == "linked-documents":
                    local_path = downloader.save_binary(
                        normalized,
                        urlparse(normalized).path.split("/")[-1] or "document",
                        fetch_result.content or b"",
                        fetch_result.content_type,
                    )
                    summary.downloads_saved += 1
                    manifest_entries.append(self._entry(normalized, local_path.name, file_type, "saved", title=local_path.stem))
                continue

            html = fetch_result.text
            title = extract_title(html)

            if options.mode == "full-page" and "html" in options.allowed_file_types:
                local_path = downloader.save_html(normalized, title, html)
                summary.downloads_saved += 1
                manifest_entries.append(self._entry(normalized, local_path.name, "html", "saved", title=title))
            elif options.mode == "text-only" and any(item in options.allowed_file_types for item in ("txt", "md")):
                extension = ".md" if "md" in options.allowed_file_types else ".txt"
                text = extract_text_content(html)
                local_path = downloader.save_text(normalized, title, text, extension)
                summary.downloads_saved += 1
                manifest_entries.append(self._entry(normalized, local_path.name, extension.lstrip("."), "saved", title=title))
            elif options.mode == "selected-content":
                selected = extract_selected_content(html, options.selectors)
                if selected:
                    local_path = downloader.save_selected(normalized, title, selected)
                    summary.downloads_saved += 1
                    manifest_entries.append(self._entry(normalized, local_path.name, "selected", "saved", title=title))
                else:
                    manifest_entries.append(self._entry(normalized, "", "selected", "skipped", title=title, note="no selector matches"))

            if options.follow_links and current.depth < options.max_depth:
                for discovered in extract_links(html, normalized):
                    normalized_discovered = normalize_url(discovered, "")
                    if not normalized_discovered:
                        continue
                    if normalized_discovered in visited or normalized_discovered in queued_urls:
                        summary.skipped_urls.append({"url": discovered, "reason": "duplicate"})
                        continue
                    if not domain_allowed(discovered, allowed_domains):
                        summary.skipped_urls.append({"url": discovered, "reason": "outside allowed domain"})
                        continue
                    if should_skip_private_area(discovered):
                        summary.skipped_urls.append({"url": discovered, "reason": "private-area safeguard"})
                        continue
                    if not pattern_allowed(discovered, options.include_patterns, options.exclude_patterns):
                        summary.skipped_urls.append({"url": discovered, "reason": "pattern filtered"})
                        continue
                    if options.mode != "linked-documents" and is_document_url(discovered, options.allowed_file_types):
                        summary.skipped_urls.append({"url": discovered, "reason": "document skipped for current mode"})
                        continue
                    queue.append(CrawlRequest(url=discovered, depth=current.depth + 1))
                    queued_urls.add(normalized_discovered)

        manifest_path = manifest_writer.save(manifest_entries)
        report_path = write_crawl_report(options.output_dir, build_crawl_report(summary, manifest_entries))
        summary.report_path = str(report_path)
        return manifest_path, summary

    def fetch(self, url: str, options: CrawlOptions) -> FetchResult:
        hostname = urlparse(url).hostname or "default"
        headers = {"User-Agent": options.user_agent}
        policy = options.retry_policy
        attempt = 0
        while attempt < policy.max_attempts:
            attempt += 1
            self.rate_limiter.wait(hostname, options.rate_limit.requests_per_second, self.sleep_fn)
            started = time.perf_counter()
            try:
                response = self.client.get(url, headers=headers, timeout=self.timeout_seconds)
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                if response.status_code in policy.retryable_statuses:
                    error = f"retryable status {response.status_code}"
                    LOGGER.warning("Fetch retry for %s attempt %s/%s: %s", url, attempt, policy.max_attempts, error)
                    if attempt >= policy.max_attempts:
                        return FetchResult(url=url, status_code=response.status_code, content=None, headers=dict(response.headers), attempt_count=attempt, error=error, elapsed_ms=elapsed_ms)
                    self._sleep_backoff(policy, attempt)
                    continue
                if response.status_code >= 400:
                    error = f"non-retryable status {response.status_code}"
                    LOGGER.error("Fetch failed for %s: %s", url, error)
                    return FetchResult(url=url, status_code=response.status_code, content=None, headers=dict(response.headers), attempt_count=attempt, error=error, elapsed_ms=elapsed_ms)
                return FetchResult(url=url, status_code=response.status_code, content=response.content, headers=dict(response.headers), attempt_count=attempt, elapsed_ms=elapsed_ms)
            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                LOGGER.warning("Fetch exception for %s attempt %s/%s: %s", url, attempt, policy.max_attempts, exc)
                if attempt >= policy.max_attempts:
                    return FetchResult(url=url, status_code=None, content=None, headers={}, attempt_count=attempt, error=str(exc), elapsed_ms=elapsed_ms)
                self._sleep_backoff(policy, attempt)
        return FetchResult(url=url, status_code=None, content=None, headers={}, attempt_count=attempt, error="exhausted retries")

    def _sleep_backoff(self, policy, attempt: int) -> None:
        delay = policy.base_delay_seconds * (policy.backoff_multiplier ** (attempt - 1))
        jitter = self.jitter_fn(0, policy.base_delay_seconds / 4)
        self.sleep_fn(delay + jitter)

    def _allowed_by_robots(self, url: str, options: CrawlOptions) -> bool:
        parsed = urlparse(url)
        robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
        parser = self._robots_cache.get(robots_url)
        if parser is None:
            response = self.client.get(robots_url, headers={"User-Agent": options.user_agent}, timeout=self.timeout_seconds)
            if response.status_code >= 400:
                self._robots_cache[robots_url] = False
                return True
            robot_parser = RobotFileParser()
            robot_parser.parse(response.text.splitlines())
            self._robots_cache[robots_url] = robot_parser
            parser = robot_parser
        if parser is False:
            return True
        return parser.can_fetch(options.user_agent, url)

    @staticmethod
    def _entry(url: str, filename: str, content_type: str, status: str, *, title: str, note: str = "") -> ManifestEntry:
        return ManifestEntry(
            source_url=url,
            title=title,
            local_filename=filename,
            content_type=content_type,
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            note=note,
        )
