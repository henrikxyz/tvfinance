from __future__ import annotations

import pytest

from tvfinance.core.models import Symbol
from tvfinance.providers.research import (
    article_html_to_markdown,
    parse_research_html,
    research_url,
)


def test_research_url() -> None:
    symbol = Symbol("NASDAQ", "AAPL")
    assert research_url(symbol, "profile").endswith("/company-profile/")
    with pytest.raises(ValueError):
        research_url(symbol, "unknown")


def test_parse_table_metadata_and_structured_data() -> None:
    markup = """
    <html><head>
      <meta property="og:title" content="Apple">
      <meta name="description" content="Profile">
      <script type="application/ld+json">{"name": "Apple"}</script>
      <script type="application/ld+json">bad</script>
    </head><body>
      <style>hidden</style><noscript>hidden</noscript><svg>hidden</svg>
      <table><tr><th>Symbol</th><th>Market Value</th></tr>
      <tr><td><a href="/symbols/NASDAQ-AAPL/">AAPL</a></td><td>3T</td></tr></table>
    </body></html>
    """
    result = parse_research_html(markup, Symbol("NASDAQ", "AAPL"), "profile")
    assert result.records[0]["symbol"] == "AAPL"
    assert str(result.records[0]["symbol_url"]).startswith("https://")
    assert result.summary["og_title"] == "Apple"
    assert result.summary["structured_data"] == [{"name": "Apple"}]


def test_parse_cards_and_empty_document() -> None:
    markup = """
    <main><article><h2>Long idea</h2><p>Buy the dip</p>
    <a href="/chart/ABC">Open</a></article><article></article></main>
    """
    result = parse_research_html(markup, Symbol("X", "Y"), "ideas")
    assert result.records[0]["title"] == "Long idea"
    assert str(result.records[0]["url"]).endswith("/chart/ABC")
    assert parse_research_html("", Symbol("X", "Y"), "ideas").records == ()


def test_article_html_to_markdown() -> None:
    markup = """
    <article><h1>Ignored title</h1><h2>Section</h2><p>Paragraph</p>
    <ul><li>Item</li><li>Item</li></ul><blockquote>Quote</blockquote></article>
    """
    rendered = article_html_to_markdown(markup, title="Ignored title")
    assert rendered == "## Section\n\nParagraph\n\n- Item\n\n> Quote"
    assert article_html_to_markdown("<html></html>") is None
