# Testing

The default suite is offline and deterministic.

- **Unit tests** validate models, validation, policies, and pure parsers.
- **Contract tests** replay sanitized HTTP and WebSocket payloads.
- **Integration tests** connect components through in-memory transports.
- **Live tests** verify external protocol compatibility and require explicit
  opt-in.

Fixtures must be minimal, sanitized, and free of cookies, account identifiers,
authorization headers, and unrelated payload fields.

Run the complete offline quality gate:

~~~bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest -q
~~~

Public endpoint contract checks are opt-in:

~~~powershell
$env:TVFINANCE_LIVE = "1"
uv run pytest -m live --no-cov
~~~

They are excluded from normal reliability expectations because availability,
rate limits, and upstream response changes are outside the package.
