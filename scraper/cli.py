from __future__ import annotations

import argparse
import logging
from pathlib import Path
from urllib.parse import urlparse

from scraper.clients import FixtureClient, HttpClient
from scraper.crawler import PermissionCrawler
from scraper.logging_utils import configure_logging
from scraper.models import AUTHORIZED_USE_WARNING, CrawlOptions, RateLimit, RetryPolicy


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"Permission-based content crawler/downloader. {AUTHORIZED_USE_WARNING}",
    )
    parser.add_argument("start_url", help="Starting URL on a site you own, are authorized to scrape, or a public-domain/open-license source.")
    parser.add_argument("--mode", choices=["full-page", "text-only", "linked-documents", "selected-content"], default="full-page")
    parser.add_argument("--allowed-domains", nargs="+", help="Allowlisted domains. Defaults to the start URL domain.")
    parser.add_argument("--max-pages", type=int, default=25, help="Maximum number of fetched pages.")
    parser.add_argument("--max-depth", type=int, default=1, help="Maximum crawl depth from the start URL.")
    parser.add_argument("--output-dir", default="downloads", help="Folder where downloaded content and manifest are saved.")
    parser.add_argument("--allowed-file-types", nargs="+", default=["html", "txt", "pdf", "epub"], help="Allowed output/document types.")
    parser.add_argument("--include-pattern", action="append", default=[], help="Regex pattern URLs must match to be crawled.")
    parser.add_argument("--exclude-pattern", action="append", default=[], help="Regex pattern URLs must not match.")
    parser.add_argument("--selector", action="append", default=[], help="CSS selector to save in selected-content mode. Repeat for multiple selectors.")
    parser.add_argument("--requests-per-second", type=float, default=1.0, help="Polite request rate limit per host.")
    parser.add_argument("--max-attempts", type=int, default=3, help="Retry attempts for failed requests.")
    parser.add_argument("--base-delay", type=float, default=1.0, help="Base retry backoff delay in seconds.")
    parser.add_argument("--backoff-multiplier", type=float, default=2.0, help="Retry backoff multiplier.")
    parser.add_argument("--manifest-format", choices=["json", "csv"], default="json", help="Manifest output format.")
    parser.add_argument("--fixture-root", help="Optional local fixture root for offline/demo crawling instead of live HTTP requests.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing saved files instead of creating numbered copies.")
    parser.add_argument("--no-follow-links", action="store_true", help="Do not follow links discovered on fetched pages.")
    parser.add_argument("--ignore-robots", action="store_true", help="Disable robots.txt checks. Use only when you are sure permission covers it.")
    parser.add_argument("--log-level", default="INFO", help="Logging level.")
    parser.epilog = AUTHORIZED_USE_WARNING
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    configure_logging(getattr(logging, args.log_level.upper(), logging.INFO))
    start_domain = urlparse(args.start_url).hostname or ""
    allowed_domains = args.allowed_domains or [start_domain]

    if not start_domain:
        raise SystemExit("A valid start URL is required.")
    if args.mode == "selected-content" and not args.selector:
        raise SystemExit("selected-content mode requires at least one --selector.")

    options = CrawlOptions(
        start_url=args.start_url,
        mode=args.mode,
        allowed_domains=allowed_domains,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        output_dir=Path(args.output_dir),
        allowed_file_types=args.allowed_file_types,
        include_patterns=args.include_pattern,
        exclude_patterns=args.exclude_pattern,
        selectors=args.selector,
        follow_links=not args.no_follow_links,
        overwrite=args.overwrite,
        respect_robots=not args.ignore_robots,
        save_format=args.manifest_format,
        rate_limit=RateLimit(requests_per_second=args.requests_per_second),
        retry_policy=RetryPolicy(
            max_attempts=args.max_attempts,
            base_delay_seconds=args.base_delay,
            backoff_multiplier=args.backoff_multiplier,
        ),
    )

    client = FixtureClient(args.fixture_root) if args.fixture_root else HttpClient()
    crawler = PermissionCrawler(client=client)
    manifest_path, summary = crawler.crawl(options)
    print(AUTHORIZED_USE_WARNING)
    print(f"Manifest saved to {manifest_path}")
    if summary.report_path:
        print(f"Crawl report saved to {summary.report_path}")
    print(f"Pages visited: {summary.pages_visited}")
    print(f"Downloads saved: {summary.downloads_saved}")
    if summary.failed_urls:
        print("Failures:")
        for failure in summary.failed_urls:
            print(f"- {failure['url']}: {failure['reason']}")
    if summary.skipped_urls:
        print("Skipped URLs:")
        for skipped in summary.skipped_urls[:10]:
            print(f"- {skipped['url']}: {skipped['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
