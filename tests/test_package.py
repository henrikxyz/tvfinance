from __future__ import annotations

import tvfinance


def test_package_version() -> None:
    assert tvfinance.__version__ == "2.0.0.dev0"
