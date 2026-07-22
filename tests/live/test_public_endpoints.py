from __future__ import annotations

import os

import pytest

from tvfinance import AsyncClient
from tvfinance.core import ClientSettings

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("TVFINANCE_LIVE") != "1",
        reason="set TVFINANCE_LIVE=1 to run public endpoint checks",
    ),
]


@pytest.mark.asyncio
async def test_search_and_quote_public_contracts() -> None:
    async with AsyncClient(settings=ClientSettings(timeout=15)) as client:
        results = await client.search("Apple")
        assert any(item.symbol.name == "AAPL" for item in results)
        quote = await client.quote("NASDAQ:AAPL")
        assert quote.symbol.ticker == "NASDAQ:AAPL"
        assert quote.last is not None
