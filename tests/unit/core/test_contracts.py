from __future__ import annotations

from tvfinance.core import HttpRequest, HttpResponse


def test_http_contracts() -> None:
    request = HttpRequest("GET", "https://example.test", params={"limit": 1})
    response = HttpResponse(200, b'{"ok": true}', {"content-type": "application/json"})

    assert request.method == "GET"
    assert response.text == '{"ok": true}'
    assert response.json() == {"ok": True}
