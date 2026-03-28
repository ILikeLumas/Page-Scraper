from __future__ import annotations

import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.parse import urlparse

from scraper.clients import FixtureClient, HttpClient
from scraper.crawler import PermissionCrawler
from scraper.logging_utils import configure_logging
from scraper.models import AUTHORIZED_USE_WARNING, CrawlOptions, RateLimit, RetryPolicy


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


class ScraperApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Page Crawler")
        self.geometry("960x860")
        self.minsize(900, 760)
        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(12, weight=1)

        ttk.Label(container, text="Page Crawler", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            container,
            text=AUTHORIZED_USE_WARNING,
            wraplength=860,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 14))

        self.start_url_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="text-only")
        self.allowed_domains_var = tk.StringVar()
        self.max_pages_var = tk.StringVar(value="25")
        self.max_depth_var = tk.StringVar(value="1")
        self.output_dir_var = tk.StringVar(value="downloads")
        self.allowed_file_types_var = tk.StringVar(value="html, txt, pdf, epub")
        self.include_patterns_var = tk.StringVar()
        self.exclude_patterns_var = tk.StringVar()
        self.selectors_var = tk.StringVar()
        self.requests_per_second_var = tk.StringVar(value="1.0")
        self.max_attempts_var = tk.StringVar(value="3")
        self.base_delay_var = tk.StringVar(value="1.0")
        self.backoff_multiplier_var = tk.StringVar(value="2.0")
        self.fixture_root_var = tk.StringVar()
        self.manifest_format_var = tk.StringVar(value="json")
        self.follow_links_var = tk.BooleanVar(value=True)
        self.respect_robots_var = tk.BooleanVar(value=True)
        self.overwrite_var = tk.BooleanVar(value=False)

        self._add_entry(container, 2, "Start URL", self.start_url_var)
        self._add_combo(container, 3, "Mode", self.mode_var, ["full-page", "text-only", "linked-documents", "selected-content"])
        self._add_entry(container, 4, "Allowed domains", self.allowed_domains_var, "Comma-separated. Blank defaults to the start URL domain.")
        self._add_entry(container, 5, "Output folder", self.output_dir_var)
        self._add_entry(container, 6, "Allowed file types", self.allowed_file_types_var, "Comma-separated, for example: html, txt, pdf, epub")
        self._add_entry(container, 7, "Include URL patterns", self.include_patterns_var, "Optional regex patterns, comma-separated")
        self._add_entry(container, 8, "Exclude URL patterns", self.exclude_patterns_var, "Optional regex patterns, comma-separated")
        self._add_entry(container, 9, "CSS selectors", self.selectors_var, "Used for selected-content mode, comma-separated")
        self._add_entry(container, 10, "Fixture root", self.fixture_root_var, "Optional local fixture folder for offline/demo crawling")

        settings = ttk.Frame(container)
        settings.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(8, 10))
        for column in range(4):
            settings.columnconfigure(column, weight=1)

        self._add_small_entry(settings, 0, 0, "Max pages", self.max_pages_var)
        self._add_small_entry(settings, 0, 1, "Max depth", self.max_depth_var)
        self._add_small_entry(settings, 0, 2, "Requests/sec", self.requests_per_second_var)
        self._add_small_entry(settings, 0, 3, "Max attempts", self.max_attempts_var)
        self._add_small_entry(settings, 2, 0, "Base delay", self.base_delay_var)
        self._add_small_entry(settings, 2, 1, "Backoff multiplier", self.backoff_multiplier_var)

        ttk.Label(settings, text="Manifest format").grid(row=2, column=2, sticky="w", pady=(10, 4))
        ttk.Combobox(settings, textvariable=self.manifest_format_var, values=["json", "csv"], state="readonly").grid(
            row=3, column=2, sticky="ew", padx=(0, 8)
        )

        toggles = ttk.Frame(settings)
        toggles.grid(row=3, column=3, sticky="w")
        ttk.Checkbutton(toggles, text="Follow links", variable=self.follow_links_var).pack(anchor="w")
        ttk.Checkbutton(toggles, text="Respect robots.txt", variable=self.respect_robots_var).pack(anchor="w")
        ttk.Checkbutton(toggles, text="Overwrite files", variable=self.overwrite_var).pack(anchor="w")

        buttons = ttk.Frame(container)
        buttons.grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Button(buttons, text="Load Demo", command=self._load_demo).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Run Crawl", command=self._run_crawl).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Clear Log", command=self._clear_log).pack(side="left")

        ttk.Label(container, text="Run log").grid(row=13, column=0, sticky="nw", pady=(4, 4))
        self.log_text = tk.Text(container, height=16, wrap="word")
        self.log_text.grid(row=13, column=1, sticky="nsew", pady=(4, 4))
        container.rowconfigure(13, weight=1)

    def _add_entry(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, hint: str | None = None) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=4)
        wrapper = ttk.Frame(parent)
        wrapper.grid(row=row, column=1, sticky="ew", pady=4)
        wrapper.columnconfigure(0, weight=1)
        ttk.Entry(wrapper, textvariable=variable).grid(row=0, column=0, sticky="ew")
        if hint:
            ttk.Label(wrapper, text=hint, foreground="#666666").grid(row=1, column=0, sticky="w", pady=(2, 0))

    def _add_combo(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar, values: list[str]) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=4)
        ttk.Combobox(parent, textvariable=variable, values=values, state="readonly").grid(row=row, column=1, sticky="ew", pady=4)

    def _add_small_entry(self, parent: ttk.Frame, row: int, column: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", pady=(0, 4))
        ttk.Entry(parent, textvariable=variable).grid(row=row + 1, column=column, sticky="ew", padx=(0, 8))

    def _append_log(self, message: str) -> None:
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")

    def _clear_log(self) -> None:
        self.log_text.delete("1.0", "end")

    def _load_demo(self) -> None:
        self.start_url_var.set("https://authorized.local/library/index.html")
        self.mode_var.set("text-only")
        self.allowed_domains_var.set("authorized.local")
        self.max_pages_var.set("5")
        self.max_depth_var.set("2")
        self.output_dir_var.set("downloads")
        self.allowed_file_types_var.set("html, txt, pdf, epub, md")
        self.include_patterns_var.set("/library/")
        self.exclude_patterns_var.set("")
        self.selectors_var.set(".chapter")
        self.fixture_root_var.set("tests/fixtures")
        self.requests_per_second_var.set("1.0")
        self.max_attempts_var.set("3")
        self.base_delay_var.set("1.0")
        self.backoff_multiplier_var.set("2.0")
        self.follow_links_var.set(True)
        self.respect_robots_var.set(True)
        self.overwrite_var.set(False)
        self.manifest_format_var.set("json")

    def _build_options(self) -> CrawlOptions:
        start_url = self.start_url_var.get().strip()
        if not start_url:
            raise ValueError("Start URL is required.")

        parsed = urlparse(start_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Start URL must be a valid absolute URL.")

        allowed_domains = _split_csv(self.allowed_domains_var.get().strip()) or [parsed.hostname or ""]
        selectors = _split_csv(self.selectors_var.get().strip())
        if self.mode_var.get() == "selected-content" and not selectors:
            raise ValueError("Selected-content mode requires at least one CSS selector.")

        return CrawlOptions(
            start_url=start_url,
            mode=self.mode_var.get(),
            allowed_domains=allowed_domains,
            max_pages=int(self.max_pages_var.get().strip()),
            max_depth=int(self.max_depth_var.get().strip()),
            output_dir=Path(self.output_dir_var.get().strip() or "downloads"),
            allowed_file_types=_split_csv(self.allowed_file_types_var.get().strip()) or ["html", "txt", "pdf", "epub"],
            include_patterns=_split_csv(self.include_patterns_var.get().strip()),
            exclude_patterns=_split_csv(self.exclude_patterns_var.get().strip()),
            selectors=selectors,
            follow_links=self.follow_links_var.get(),
            overwrite=self.overwrite_var.get(),
            respect_robots=self.respect_robots_var.get(),
            save_format=self.manifest_format_var.get(),
            rate_limit=RateLimit(requests_per_second=float(self.requests_per_second_var.get().strip())),
            retry_policy=RetryPolicy(
                max_attempts=int(self.max_attempts_var.get().strip()),
                base_delay_seconds=float(self.base_delay_var.get().strip()),
                backoff_multiplier=float(self.backoff_multiplier_var.get().strip()),
            ),
        )

    def _run_crawl(self) -> None:
        try:
            options = self._build_options()
        except Exception as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        self._append_log("Starting crawl...")
        self._append_log(AUTHORIZED_USE_WARNING)
        thread = threading.Thread(target=self._run_worker, args=(options,), daemon=True)
        thread.start()

    def _run_worker(self, options: CrawlOptions) -> None:
        try:
            fixture_root = self.fixture_root_var.get().strip()
            client = FixtureClient(fixture_root) if fixture_root else HttpClient()
            crawler = PermissionCrawler(client=client)
            manifest_path, summary = crawler.crawl(options)
            self.after(0, lambda: self._append_log(f"Manifest saved to {manifest_path}"))
            self.after(0, lambda: self._append_log(f"Pages visited: {summary.pages_visited}"))
            self.after(0, lambda: self._append_log(f"Downloads saved: {summary.downloads_saved}"))
            if summary.failed_urls:
                for failure in summary.failed_urls:
                    self.after(0, lambda item=failure: self._append_log(f"Failure: {item['url']} -> {item['reason']}"))
            if summary.skipped_urls:
                for skipped in summary.skipped_urls[:15]:
                    self.after(0, lambda item=skipped: self._append_log(f"Skipped: {item['url']} -> {item['reason']}"))
        except Exception as exc:
            self.after(0, lambda: self._append_log(f"Run failed: {exc}"))
            self.after(0, lambda: messagebox.showerror("Run failed", str(exc)))


def main() -> int:
    configure_logging(logging.INFO)
    app = ScraperApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
