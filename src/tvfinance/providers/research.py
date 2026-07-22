"""Resilient HTML extraction for public symbol research pages."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any, cast
from urllib.parse import urljoin

from lxml import html  # type: ignore[import-untyped]

from tvfinance.core.models import ResearchData, Symbol
from tvfinance.core.types import JsonValue

SITE_ROOT = "https://www.tradingview.com"

RESEARCH_SLUGS = {
    "bonds": "bonds",
    "etfs": "etfs",
    "documents": "financials-filings",
    "holdings": "holdings",
    "ideas": "ideas",
    "financials": "financials-overview",
    "forecast": "forecast",
    "technicals": "technicals",
    "profile": "company-profile",
}


def research_url(symbol: Symbol, section: str) -> str:
    """Build a canonical symbol research URL."""
    slug = RESEARCH_SLUGS.get(section)
    if slug is None:
        raise ValueError(f"Unsupported research section: {section}")
    return f"{SITE_ROOT}/symbols/{symbol.exchange}-{symbol.name}/{slug}/"


def parse_research_html(markup: str, symbol: Symbol, section: str) -> ResearchData:
    """Extract tables, cards, metadata, and embedded structured data."""
    document = html.fromstring(markup or "<html></html>")
    for node in document.xpath("//script|//style|//noscript|//svg"):
        if node.tag != "script":
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)

    records = _table_records(document)
    if not records:
        records = _card_records(document)
    summary = _metadata(document)
    embedded = _embedded_data(document)
    if embedded:
        summary["structured_data"] = embedded
    return ResearchData(symbol, section, tuple(records), summary)


def article_html_to_markdown(markup: str, *, title: str = "") -> str | None:
    """Convert a public article body into conservative Markdown."""
    document = html.fromstring(markup or "<html></html>")
    candidates = document.xpath(
        "//article | //*[@data-qa-id='news-story-content'] | //main"
    )
    root = candidates[0] if candidates else document
    lines: list[str] = []
    for node in root.xpath(".//h1|.//h2|.//h3|.//p|.//li|.//blockquote"):
        text = _text(node)
        if not text or text == title:
            continue
        tag = str(node.tag).lower()
        if tag.startswith("h"):
            level = min(int(tag[1]), 3)
            lines.append(f"{'#' * level} {text}")
        elif tag == "li":
            lines.append(f"- {text}")
        elif tag == "blockquote":
            lines.append(f"> {text}")
        else:
            lines.append(text)
    cleaned = "\n\n".join(dict.fromkeys(lines)).strip()
    return cleaned or None


def _table_records(document: Any) -> list[dict[str, JsonValue]]:
    records: list[dict[str, JsonValue]] = []
    for table in document.xpath("//table"):
        rows = table.xpath(".//tr")
        if not rows:
            continue
        headers = [_key(_text(cell)) for cell in rows[0].xpath("./th|./td")]
        for row in rows[1:]:
            cells = row.xpath("./th|./td")
            if not cells:
                continue
            item: dict[str, JsonValue] = {}
            for index, cell in enumerate(cells):
                key = headers[index] if index < len(headers) else f"column_{index}"
                item[key] = _text(cell)
                links = cell.xpath(".//a[@href]/@href")
                if links:
                    item[f"{key}_url"] = urljoin(SITE_ROOT, str(links[0]))
            records.append(item)
    return records


def _card_records(document: Any) -> list[dict[str, JsonValue]]:
    records: list[dict[str, JsonValue]] = []
    for node in document.xpath("//article"):
        title = _first_text(node.xpath(".//h1|.//h2|.//h3|.//a[@title]"))
        body = _text(node)
        links = node.xpath(".//a[@href]/@href")
        if not title and not body:
            continue
        item: dict[str, JsonValue] = {"title": title, "text": body}
        if links:
            item["url"] = urljoin(SITE_ROOT, str(links[0]))
        records.append(item)
    return records


def _metadata(document: Any) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {}
    for node in document.xpath("//meta[@content]"):
        key = node.get("property") or node.get("name")
        content = node.get("content")
        if key in {"description", "og:title", "og:description", "og:image"}:
            result[_key(str(key))] = str(content)
    return result


def _embedded_data(document: Any) -> JsonValue:
    values: list[JsonValue] = []
    for node in document.xpath("//script[@type='application/ld+json']"):
        try:
            values.append(cast(JsonValue, json.loads(node.text or "")))
        except ValueError:
            continue
    return values


def _first_text(nodes: Iterable[Any]) -> str:
    for node in nodes:
        value = _text(node)
        if value:
            return value
    return ""


def _text(node: Any) -> str:
    return re.sub(r"\s+", " ", " ".join(node.xpath(".//text()"))).strip()


def _key(value: str) -> str:
    key = re.sub(r"[^0-9a-z]+", "_", value.lower()).strip("_")
    return key or "value"
