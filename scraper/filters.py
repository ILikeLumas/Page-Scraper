from __future__ import annotations

import re
from urllib.parse import urljoin, urldefrag, urlparse


PRIVATE_PATH_KEYWORDS = (
    "login",
    "signin",
    "sign-in",
    "signup",
    "sign-up",
    "account",
    "checkout",
    "cart",
    "admin",
    "profile",
    "password",
)


def normalize_url(base_url: str, href: str) -> str | None:
    if href == "":
        cleaned, _fragment = urldefrag(base_url)
        return cleaned
    href = href.strip()
    if not href or href.startswith(("mailto:", "javascript:", "tel:")):
        return None
    absolute = urljoin(base_url, href)
    cleaned, _fragment = urldefrag(absolute)
    return cleaned


def domain_allowed(url: str, allowed_domains: list[str]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == domain.lower() or host.endswith(f".{domain.lower()}") for domain in allowed_domains)


def should_skip_private_area(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(keyword in path for keyword in PRIVATE_PATH_KEYWORDS)


def pattern_allowed(url: str, include_patterns: list[str], exclude_patterns: list[str]) -> bool:
    if include_patterns and not any(re.search(pattern, url) for pattern in include_patterns):
        return False
    if exclude_patterns and any(re.search(pattern, url) for pattern in exclude_patterns):
        return False
    return True


def detect_file_type(url: str, content_type: str = "") -> str:
    path = urlparse(url).path.lower()
    if path.endswith(".pdf") or "application/pdf" in content_type:
        return "pdf"
    if path.endswith(".epub") or "application/epub" in content_type:
        return "epub"
    if path.endswith(".txt") or "text/plain" in content_type:
        return "txt"
    if path.endswith(".md") or "text/markdown" in content_type:
        return "md"
    return "html"


def is_document_url(url: str, allowed_file_types: list[str], content_type: str = "") -> bool:
    file_type = detect_file_type(url, content_type)
    return file_type in {item.lower() for item in allowed_file_types} and file_type != "html"
