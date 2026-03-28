from scraper.filters import domain_allowed, normalize_url


def test_normalize_url_resolves_relative_and_drops_fragment():
    url = normalize_url("https://authorized.local/library/index.html", "../library/book-1.html#top")

    assert url == "https://authorized.local/library/book-1.html"


def test_domain_allowed_blocks_non_allowlisted_domains():
    assert domain_allowed("https://authorized.local/library/book-1.html", ["authorized.local"]) is True
    assert domain_allowed("https://elsewhere.local/book.html", ["authorized.local"]) is False
