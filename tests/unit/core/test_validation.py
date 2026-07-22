from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from tvfinance.core import Symbol, ValidationError
from tvfinance.core.validation import (
    ensure_utc,
    normalize_locale,
    normalize_symbol,
    normalize_symbols,
    positive_number,
)


def test_normalize_symbol() -> None:
    assert normalize_symbol(" nasdaq:aapl ") == Symbol("NASDAQ", "AAPL")
    existing = Symbol("NYSE", "IBM")
    assert normalize_symbol(existing) is existing


@pytest.mark.parametrize("value", ["AAPL", "A:B:C", "NASDAQ:", "NAS DAQ:AAPL"])
def test_invalid_symbol(value: str) -> None:
    with pytest.raises(ValidationError):
        normalize_symbol(value)


def test_normalize_symbols_deduplicates_in_order() -> None:
    assert normalize_symbols(["NASDAQ:AAPL", "nasdaq:aapl", "NYSE:IBM"]) == (
        Symbol("NASDAQ", "AAPL"),
        Symbol("NYSE", "IBM"),
    )
    with pytest.raises(ValidationError):
        normalize_symbols([])


def test_normalize_locale() -> None:
    assert normalize_locale("zh", "tw") == ("zh", "TW")
    with pytest.raises(ValidationError):
        normalize_locale("z1", "TW")


def test_ensure_utc() -> None:
    assert ensure_utc(date(2026, 7, 22)) == datetime(2026, 7, 22, tzinfo=timezone.utc)
    naive = datetime(2026, 7, 22, 1, 2)
    assert ensure_utc(naive).tzinfo is timezone.utc
    offset = timezone(timedelta(hours=8))
    assert ensure_utc(datetime(2026, 7, 22, 8, tzinfo=offset)) == datetime(
        2026, 7, 22, tzinfo=timezone.utc
    )


def test_positive_number() -> None:
    assert positive_number(1.5, field="timeout") == 1.5
    with pytest.raises(ValidationError):
        positive_number(0, field="timeout")
