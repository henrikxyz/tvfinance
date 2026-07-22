from __future__ import annotations

from importlib.metadata import metadata

import tvfinance


def test_package_version() -> None:
    assert tvfinance.__version__ == "2.0.0.dev0"


def test_package_declares_optional_interfaces() -> None:
    package_metadata = metadata("tvfinance")
    assert set(package_metadata.get_all("Provides-Extra") or []) == {
        "all",
        "cli",
        "mcp",
    }
