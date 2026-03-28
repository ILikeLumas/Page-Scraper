import json

from scraper.manifest import ManifestWriter
from scraper.models import ManifestEntry


def test_manifest_writer_creates_json_manifest(tmp_path):
    writer = ManifestWriter(tmp_path, format="json")
    path = writer.save(
        [
            ManifestEntry(
                source_url="https://authorized.local/library/book-1.html",
                title="Book One",
                local_filename="book-one.html",
                content_type="html",
                status="saved",
                timestamp="2026-03-27T00:00:00+00:00",
            )
        ]
    )

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.name == "manifest.json"
    assert payload[0]["source_url"] == "https://authorized.local/library/book-1.html"
