from __future__ import annotations

import json

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
