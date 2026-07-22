# tvfinance

`tvfinance` provides typed synchronous and asynchronous interfaces for financial
market data research. The package is designed around one domain implementation
shared by Python APIs, command-line tools, and an optional MCP server.

## Design goals

- Predictable typed results instead of loosely structured dictionaries.
- Async-first internals with explicit synchronous adapters.
- Deterministic offline tests for every parser and protocol operation.
- Optional integrations that do not increase the base installation footprint.
- Clear failures with actionable context and no silently discarded errors.

!!! warning

    The 2.0 API is under development. It is not ready for production use or
    financial decision-making.
