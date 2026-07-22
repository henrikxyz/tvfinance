# tvfinance

`tvfinance` is a typed Python toolkit for financial market data research.

This repository is being developed as a clean, unified implementation with
shared synchronous, asynchronous, command-line, and optional MCP interfaces.

## Development

```bash
uv sync --group dev
uv run ruff format .
uv run ruff check .
uv run pytest
uv build
```

## Status

The 2.0 API is under active development and is not yet ready for production
use.
