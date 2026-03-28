from __future__ import annotations

from bs4 import BeautifulSoup

from scraper.filters import normalize_url


def extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    discovered: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        absolute = normalize_url(base_url, anchor.get("href", ""))
        if absolute and absolute not in seen:
            discovered.append(absolute)
            seen.add(absolute)
    return discovered


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)
    h1 = soup.select_one("h1")
    if h1:
        return h1.get_text(" ", strip=True)
    return "untitled"


def extract_text_content(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()

    preferred = soup.select_one("main") or soup.select_one("article") or soup.body or soup
    for node in preferred.select("nav, header, footer, aside"):
        node.decompose()

    text = preferred.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def extract_selected_content(html: str, selectors: list[str]) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    extracted: dict[str, str] = {}
    for selector in selectors:
        matches = [node.get_text("\n", strip=True) for node in soup.select(selector)]
        if matches:
            extracted[selector] = "\n\n".join(match for match in matches if match.strip())
    return extracted
