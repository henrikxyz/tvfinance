from __future__ import annotations

import json
from typing import Any, cast

import pytest

from tvfinance import api
from tvfinance.cli import _json_default, main
from tvfinance.core import Symbol


def test_cli_version_and_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert "2.0.0.dev0" in capsys.readouterr().out
    assert main([]) == 0
    assert "usage:" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("argv", "name"),
    [
        (["search", "Apple"], "search"),
        (["quote", "NASDAQ:AAPL"], "quote"),
        (["screener", "--limit", "1"], "screener"),
        (
            ["options", "NASDAQ:AAPL", "--expiration", "20261218", "--root", "AAPL"],
            "options_chain",
        ),
        (["news", "NASDAQ:AAPL", "--limit", "1"], "news"),
        (["option-series", "NASDAQ:AAPL"], "option_series"),
        (["history", "NASDAQ:AAPL", "--count", "2"], "history"),
        (["research", "NASDAQ:AAPL", "profile"], "research"),
        (["calendar", "earnings", "--limit", "1"], "corporate_calendar"),
        (["news-markdown", "NASDAQ:AAPL", "--limit", "1"], "news_markdown"),
    ],
)
def test_cli_commands(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    name: str,
) -> None:
    monkeypatch.setattr(api, name, lambda *args, **kwargs: {"ok": True})
    assert main(argv) == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True}


def test_json_default_serializes_models_and_rejects_unknown() -> None:
    assert _json_default(Symbol("NASDAQ", "AAPL")) == {
        "exchange": "NASDAQ",
        "name": "AAPL",
    }
    with pytest.raises(TypeError):
        _json_default(object())


def test_cli_parses_max_count_and_dates(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}

    def history(*args: object, **kwargs: object) -> dict[str, bool]:
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(api, "history", history)
    assert main(["history", "X:Y", "--count", "max"]) == 0
    assert captured["count"] == "max"
    capsys.readouterr()

    def calendar(*args: object, **kwargs: object) -> dict[str, bool]:
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(api, "corporate_calendar", calendar)
    assert main(["calendar", "ipo", "--from-date", "2026-01-01"]) == 0
    assert cast(Any, captured["from_date"]).year == 2026
