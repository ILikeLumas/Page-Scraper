from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from scraper.filters import detect_file_type


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "item"


def make_clean_filename(url: str, title: str, extension: str) -> str:
    parsed = urlparse(url)
    stem = _slugify(title) if title and title != "untitled" else _slugify(Path(parsed.path).stem or parsed.netloc)
    if not extension.startswith("."):
        extension = f".{extension}"
    return f"{stem}{extension}"


class ContentDownloader:
    def __init__(self, output_dir: Path, overwrite: bool = False) -> None:
        self.output_dir = output_dir
        self.overwrite = overwrite

    def save_html(self, url: str, title: str, html: str) -> Path:
        return self._write_text("html", url, title, html, ".html")

    def save_text(self, url: str, title: str, text: str, extension: str = ".txt") -> Path:
        return self._write_text("text", url, title, text, extension)

    def save_selected(self, url: str, title: str, content_by_selector: dict[str, str]) -> Path:
        chunks = [f"## {selector}\n\n{content}" for selector, content in content_by_selector.items()]
        return self._write_text("selected", url, title, "\n\n".join(chunks), ".md")

    def save_binary(self, url: str, title: str, content: bytes, content_type: str) -> Path:
        extension = detect_file_type(url, content_type)
        if extension == "html":
            extension = "bin"
        folder = self.output_dir / "documents"
        folder.mkdir(parents=True, exist_ok=True)
        path = self._resolve_target(folder / make_clean_filename(url, title, extension))
        path.write_bytes(content)
        return path

    def _write_text(self, folder_name: str, url: str, title: str, text: str, extension: str) -> Path:
        folder = self.output_dir / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        path = self._resolve_target(folder / make_clean_filename(url, title, extension))
        path.write_text(text, encoding="utf-8")
        return path

    def _resolve_target(self, path: Path) -> Path:
        if self.overwrite or not path.exists():
            return path
        counter = 2
        while True:
            candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1
