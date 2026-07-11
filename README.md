# Page Crawler

[![Tests](https://github.com/ILikeLumas/Page-Scraper/actions/workflows/tests.yml/badge.svg)](https://github.com/ILikeLumas/Page-Scraper/actions/workflows/tests.yml)

This project is a Python crawler/downloader for authorized websites, public-domain archives, and openly licensed sources.

## Important Safety And Compliance Warning

Use this tool only on:

- websites you own,
- websites where you have explicit permission to crawl/download content,
- clearly public-domain or openly licensed sources.

This project is intentionally designed to be constrained. It does **not** implement:

- login bypass,
- paywall bypass,
- anti-bot evasion,
- CAPTCHA solving,
- credential stuffing,
- proxy rotation,
- stealth features to defeat site protections.

The crawler:

- stays inside an allowlisted domain by default,
- respects `robots.txt` unless you explicitly disable that check,
- skips obvious private areas such as login, account, checkout, cart, and admin pages,
- rate-limits requests and retries failures conservatively.

## Architecture

The crawler is organized into focused modules:

- `scraper/cli.py`: command-line entrypoint and argument parsing.
- `scraper/crawler.py`: traversal, robots checks, rate limiting, retries, duplicate prevention.
- `scraper/filters.py`: URL normalization, domain allowlisting, private-area and pattern filtering.
- `scraper/extractor.py`: link discovery, title extraction, text extraction, CSS selector extraction.
- `scraper/downloader.py`: saves HTML, text, selected content, and linked documents into organized folders.
- `scraper/manifest.py`: writes a JSON or CSV manifest of downloads.
- `scraper/reporting.py`: writes crawl-level measurement and data-quality metrics.
- `scraper/models.py`: crawl options, retry policy, manifest entries, and summary data.
- `scraper/clients.py`: HTTP client and fixture client for tests.

## Setup

Create a virtual environment and install dependencies:

```bash
py -m pip install -r requirements.txt
```

For local development and tests:

```bash
py -m pip install -e ".[dev]"
```

## Optional Executable Build

`PageScrapper.spec` and `build_exe.bat` are kept as source files for local PyInstaller builds. Generated `build/`, `dist/`, and downloaded crawl outputs are intentionally excluded from the repository.

## Usage

General form:

```bash
py -m scraper.cli START_URL [options]
```

Optional offline/demo mode with local fixtures:

```bash
py -m scraper.cli https://authorized.local/library/index.html --mode text-only --allowed-domains authorized.local --fixture-root tests/fixtures --output-dir downloads
```

## Example Output

The included fixtures let you run the crawler without touching a live website:

```bash
py -m scraper.cli https://authorized.local/library/index.html --mode text-only --allowed-domains authorized.local --fixture-root tests/fixtures --output-dir downloads/example --overwrite --requests-per-second 1000 --max-depth 2
```

Actual CLI output from the fixture run:

```text
Authorized/public-domain use only. Crawl only websites you own, have explicit permission to download from, or clearly public-domain/open-license sources.
Manifest saved to downloads\example\manifest.json
Crawl report saved to downloads\example\crawl_report.json
Pages visited: 3
Downloads saved: 3
Skipped URLs:
- https://authorized.local/library/files/book-one.pdf: document skipped for current mode
- https://authorized.local/account/private.html: private-area safeguard
- https://elsewhere.local/book.html: outside allowed domain
- https://authorized.local/library/book-1.html: duplicate
```

Generated output structure:

```text
downloads/example/
  crawl_report.json
  manifest.json
  text/
    book-one.txt
    book-two.txt
    library-index.txt
```

Sample `manifest.json` entry:

```json
{
  "source_url": "https://authorized.local/library/book-1.html",
  "title": "Book One",
  "local_filename": "book-one.txt",
  "content_type": "txt",
  "status": "saved",
  "timestamp": "2026-07-11T05:21:01.917755+00:00",
  "note": ""
}
```

Sample `crawl_report.json`:

```json
{
  "pages_requested": 3,
  "pages_succeeded": 3,
  "pages_failed": 0,
  "downloads_saved": 3,
  "duplicates_removed": 1,
  "records_missing_title": 0,
  "average_response_ms": 0.29,
  "status_counts": {
    "200": 3
  },
  "skipped_by_reason": {
    "document skipped for current mode": 1,
    "duplicate": 1,
    "outside allowed domain": 1,
    "private-area safeguard": 1
  },
  "failed_by_reason": {}
}
```

Examples:

Crawl a single authorized page and save raw HTML:

```bash
py -m scraper.cli https://example.com/archive/page.html --mode full-page --max-pages 1 --max-depth 0 --allowed-domains example.com --output-dir downloads
```

Crawl an authorized site section and save text-only content:

```bash
py -m scraper.cli https://example.com/library/index.html --mode text-only --allowed-domains example.com --max-pages 20 --max-depth 2 --allowed-file-types txt md --output-dir downloads
```

Crawl an index page and download linked PDFs or EPUBs from an authorized or public-domain source:

```bash
py -m scraper.cli https://example.com/library/index.html --mode linked-documents --allowed-domains example.com --allowed-file-types pdf epub --max-pages 30 --max-depth 2 --output-dir downloads
```

Crawl pages and save only content matching a CSS selector:

```bash
py -m scraper.cli https://example.com/library/index.html --mode selected-content --selector article.chapter --selector .download-note --allowed-domains example.com --max-pages 10 --max-depth 1 --output-dir downloads
```

Filter URLs with include/exclude patterns:

```bash
py -m scraper.cli https://example.com/library/index.html --mode text-only --allowed-domains example.com --include-pattern "/library/" --exclude-pattern "/draft/" --output-dir downloads
```

## CLI Options

- `start_url`: required starting URL.
- `--mode`: one of `full-page`, `text-only`, `linked-documents`, `selected-content`.
- `--allowed-domains`: allowlisted domains. Defaults to the start URL domain.
- `--max-pages`: maximum fetched pages.
- `--max-depth`: crawl depth from the starting URL.
- `--output-dir`: folder where downloaded files and manifest are saved.
- `--allowed-file-types`: output or linked-document types to allow, such as `html`, `txt`, `md`, `pdf`, `epub`.
- `--include-pattern`: regex pattern URLs must match.
- `--exclude-pattern`: regex pattern URLs must not match.
- `--selector`: CSS selectors for `selected-content` mode.
- `--requests-per-second`: polite per-host request rate.
- `--max-attempts`: retry attempts for failed requests.
- `--base-delay`: base retry delay in seconds.
- `--backoff-multiplier`: retry backoff multiplier.
- `--manifest-format`: `json` or `csv`.
- `--overwrite`: overwrite existing files instead of creating numbered copies.
- `--no-follow-links`: do not follow discovered links.
- `--ignore-robots`: disable robots.txt checks. Only use this when your authorization explicitly allows it.

## Download Modes

- `full-page`: saves raw HTML for matching pages under `output/html/`.
- `text-only`: extracts readable page text and saves it under `output/text/`.
- `linked-documents`: follows index/content pages and downloads linked files of allowed types under `output/documents/`.
- `selected-content`: saves only content matching CSS selectors under `output/selected/`.

## Output

The crawler writes organized content folders, a manifest, and a crawl report:

- `manifest.json` or `manifest.csv`
- `crawl_report.json`
- `html/`
- `text/`
- `selected/`
- `documents/`

Manifest fields:

- `source_url`
- `title`
- `local_filename`
- `content_type`
- `status`
- `timestamp`
- `note`

Report fields:

- `pages_requested`
- `pages_succeeded`
- `pages_failed`
- `downloads_saved`
- `duplicates_removed`
- `records_missing_title`
- `average_response_ms`
- `status_counts`
- `skipped_by_reason`
- `failed_by_reason`

## Testing

Run tests locally with:

```bash
py -m pytest
```

GitHub Actions also runs `pytest` on every push and pull request through `.github/workflows/tests.yml`.

The tests cover:

- URL normalization,
- duplicate prevention,
- domain restriction,
- selector extraction,
- manifest generation,
- crawl report generation,
- linked-document downloads using fixture HTML and document files.

## License

This project is released under the MIT License. See `LICENSE` for details.
