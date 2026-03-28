from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import requests


class HttpClient:
    def get(self, url: str, headers: dict[str, str], timeout: float) -> requests.Response:
        return requests.get(url, headers=headers, timeout=timeout)


class FixtureClient:
    def __init__(self, fixture_root: str | Path) -> None:
        self.fixture_root = Path(fixture_root)

    def get(self, url: str, headers: dict[str, str], timeout: float) -> requests.Response:
        parsed = urlparse(url)
        target = self.fixture_root / parsed.netloc / parsed.path.strip("/")
        if target.is_dir():
            target = target / "index.html"
        if not target.suffix:
            target = target.with_suffix(".html")

        response = requests.Response()
        response.url = url
        if not target.exists():
            response.status_code = 404
            response._content = b""
            response.headers["Content-Type"] = "text/plain"
            return response

        response.status_code = 200
        response._content = target.read_bytes()
        response.headers["Content-Type"] = mimetypes.guess_type(str(target))[0] or "text/html"
        return response
