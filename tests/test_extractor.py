from scraper.extractor import extract_selected_content


def test_selector_extraction_collects_matching_content():
    html = """
    <html><body>
      <article class="chapter"><p>Line one.</p></article>
      <article class="chapter"><p>Line two.</p></article>
    </body></html>
    """

    result = extract_selected_content(html, [".chapter"])

    assert ".chapter" in result
    assert "Line one." in result[".chapter"]
    assert "Line two." in result[".chapter"]
