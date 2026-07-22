from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from tvfinance.core import (
    AsyncClientSession,
    ClientSettings,
    HttpRequest,
    HttpResponse,
    Locale,
)
from tvfinance.providers import TradingViewProvider

FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures" / "contracts" / "symbol_search.json"
)
CASES = cast(list[dict[str, Any]], json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


class FixtureTransport:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.request: HttpRequest | None = None

    async def send(self, request: HttpRequest) -> HttpResponse:
        self.request = request
        return HttpResponse(200, json.dumps(self.payload).encode())

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=[str(case["case"]) for case in CASES])
async def test_symbol_search_contract_fixture(case: dict[str, Any]) -> None:
    language, region = cast(list[str], case["locale"])
    transport = FixtureTransport(case["payload"])
    provider = TradingViewProvider(
        AsyncClientSession(
            settings=ClientSettings(locale=Locale(language, region)),
            transport=transport,
        )
    )
    results = await provider.search(str(case["query"]))
    assert results[0].symbol.ticker == case["expected"]
    assert transport.request is not None
    assert transport.request.headers["Accept-Language"].startswith(
        f"{language}-{region}"
    )
