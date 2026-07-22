# Provider compatibility

Provider interfaces used by the package are publicly reachable but unofficial.
Public reachability does not grant permission to access, process, store, or
redistribute provider data. Review the
[TradingView policy notice](https://github.com/henrikxyz/tvfinance/blob/main/TRADINGVIEW_POLICY.md)
before using them. Contract fixtures protect normalized package behavior;
scheduled live checks detect connectivity and upstream compatibility changes.

| Capability | Transport | Fixture | Scheduled live check |
| --- | --- | --- | --- |
| Search | HTTP JSON | Yes, multi-asset and locale | Yes |
| Quote snapshots | HTTP JSON | Yes | Yes |
| Quote updates | WebSocket | Yes | No |
| History | WebSocket | Yes | No |
| Screener | HTTP JSON | Yes | No |
| Options | HTTP JSON and WebSocket | Yes | No |
| News | HTTP JSON and HTML | Yes | No |
| Calendars | HTTP JSON | Yes | No |
| Research sections | HTTP HTML | Yes | No |

The live workflow intentionally performs only one search and one quote request
per run. It runs weekly and can also be started manually. Its JUnit result is
retained as a diagnostic artifact.

## Change record procedure

When an upstream contract changes:

1. Preserve a minimal sanitized response fixture.
2. Add a regression test that fails with the previous parser.
3. Update the parser and typed mapping.
4. Record affected capabilities and behavior in CHANGELOG.md.
5. Update this matrix if availability or validation strategy changes.

Transport failures, HTTP status failures, malformed protocol messages, and
parse failures remain distinct structured exception categories.
