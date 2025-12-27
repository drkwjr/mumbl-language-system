"""Unit tests for wiki parser."""

from radio_ingestion.discovery import wiki_parser
from radio_ingestion.discovery.wiki_parser import parse_wiki_page


def test_parse_wiki_page_fallback(monkeypatch):
    html = """
    <html>
      <body>
        <ul>
          <li>Radio One</li>
          <li>Community FM</li>
        </ul>
      </body>
    </html>
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    results = parse_wiki_page(html, {"name": "Test Wiki"}, allow_llm=False)

    assert len(results) == 2
    assert results[0].name == "Radio One"
    assert results[1].name == "Community FM"


def test_parse_wiki_page_minimum_coverage(monkeypatch):
    html = """
    <html>
      <body>
        <ul>
          <li>Station One</li>
          <li>Station Two</li>
          <li>Station Three</li>
          <li>Station Four</li>
          <li>Station Five</li>
          <li>Station Six</li>
        </ul>
      </body>
    </html>
    """
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    def _fake_parse_with_llm(items, source_meta):
        return []

    monkeypatch.setattr(wiki_parser, "parse_with_llm", _fake_parse_with_llm)

    results = parse_wiki_page(html, {"name": "Test Wiki"}, allow_llm=True)

    assert len(results) == 6
