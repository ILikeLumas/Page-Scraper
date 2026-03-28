from __future__ import annotations

import csv
import json
from pathlib import Path

from scraper.models import ManifestEntry


class ManifestWriter:
    def __init__(self, output_dir: Path, format: str = "json") -> None:
        self.output_dir = output_dir
        self.format = format

    def save(self, entries: list[ManifestEntry]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.format == "csv":
            return self._save_csv(entries)
        return self._save_json(entries)

    def _save_json(self, entries: list[ManifestEntry]) -> Path:
        path = self.output_dir / "manifest.json"
        path.write_text(json.dumps([entry.to_dict() for entry in entries], indent=2), encoding="utf-8")
        return path

    def _save_csv(self, entries: list[ManifestEntry]) -> Path:
        path = self.output_dir / "manifest.csv"
        rows = [entry.to_dict() for entry in entries]
        fieldnames = list(rows[0].keys()) if rows else ["source_url", "title", "local_filename", "content_type", "status", "timestamp", "note"]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path
