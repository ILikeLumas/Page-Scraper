# Page Crawler

This project is a Python crawler/downloader for authorized websites, public-domain archives, and openly licensed sources.

## Important Safety And Compliance Warning

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
- `scraper/models.py`: crawl options, retry policy, manifest entries, and summary data.
- `scraper/clients.py`: HTTP client and fixture client for tests.

## Setup

Create a virtual environment and install dependencies:

```bash
py -m pip install -r requirements.txt
```

## Usage

General form:

```bash
py -m scraper.cli START_URL [options]
```

Optional offline/demo mode with local fixtures:

```bash
py -m scraper.cli https://authorized.local/library/index.html --mode text-only --allowed-domains authorized.local --fixture-root tests/fixtures --output-dir downloads
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

The crawler writes organized content folders plus a manifest:

- `manifest.json` or `manifest.csv`
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

## Safe/Legal Example Use Cases

- Download pages from your own documentation site for offline review.
- Crawl a public-domain library section that openly provides downloadable PDFs or EPUBs.
- Archive openly licensed articles from a site that explicitly permits crawling.

## Testing

Run tests locally with:

```bash
py -m pytest
```

The tests cover:

- URL normalization,
- duplicate prevention,
- domain restriction,
- selector extraction,
- manifest generation,
- linked-document downloads using fixture HTML and document files.
