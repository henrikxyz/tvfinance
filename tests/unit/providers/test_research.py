from __future__ import annotations

from typing import Any, cast

import pytest
from lxml import html  # type: ignore[import-untyped]

from tvfinance.core.models import Symbol
from tvfinance.providers import research
from tvfinance.providers.research import (
    _first_text,
    _key,
    _table_records,
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
    without_link = parse_research_html(
        "<article><h2>Standalone</h2></article>", Symbol("X", "Y"), "ideas"
    )
    assert "url" not in without_link.records[0]


def test_parser_defensive_html_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    document = html.fromstring(
        '<html><head><meta name="viewport" content="wide"></head>'
        "<body><table></table><table><tr><th>H</th></tr><tr></tr></table></body></html>"
    )
    assert _table_records(document) == []
    result = parse_research_html(
        '<meta name="viewport" content="wide"><article><h2>Card</h2></article>',
        Symbol("X", "Y"),
        "profile",
    )
    assert result.records[0]["title"] == "Card"
    nodes = html.fromstring("<div><span></span><span>value</span></div>").xpath(
        ".//span"
    )
    assert _first_text(nodes) == "value"
    assert _key("!!!") == "value"

    class Orphan:
        tag = "style"

        def getparent(self) -> None:
            return None

    class Document:
        def xpath(self, query: str) -> list[Any]:
            if query == "//script|//style|//noscript|//svg":
                return [Orphan()]
            return []

    monkeypatch.setattr(
        cast(Any, research).html,
        "fromstring",
        lambda markup: cast(Any, Document()),
    )
    result = parse_research_html("<ignored>", Symbol("X", "Y"), "profile")
    assert result.records == ()


def test_article_html_to_markdown() -> None:
    markup = """
    <article><h1>Ignored title</h1><h2>Section</h2><p>Paragraph</p>
    <ul><li>Item</li><li>Item</li></ul><blockquote>Quote</blockquote></article>
    """
    rendered = article_html_to_markdown(markup, title="Ignored title")
    assert rendered == "## Section\n\nParagraph\n\n- Item\n\n> Quote"
    assert article_html_to_markdown("<html></html>") is None
