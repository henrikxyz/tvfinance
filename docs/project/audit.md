# Architecture and technical-debt audit

## Resolved in the rebuild

- Duplicate HTTP, async, CLI, and MCP implementations were replaced by shared
  provider and domain layers.
- Public return values use immutable typed models with JSON-safe serialization.
- Network calls have bounded timeouts, structured errors, retry policy, and
  header-aware caching.
- Parsing and protocol logic are isolated and covered by deterministic offline
  fixtures.
- Sync code is a thin adapter and explicitly rejects use inside a running event
  loop.
- Optional MCP dependencies are isolated behind the mcp extra.
- Packaging, typing, formatting, tests, documentation, and distribution builds
  are enforced as quality gates.

## Accepted risks

- Upstream endpoints and HTML structure are unofficial and may change.
- Public pages can vary by locale, asset class, region, or permission.
- Anonymous access can be rate-limited and does not expose private account data.
- The default in-memory cache is process-local by design; a persistent SQLite
  adapter is available for shared durable state.

## Mitigations

- Provider-specific code is isolated under providers.
- Parsers tolerate missing optional fields and reject invalid top-level shapes.
- Live endpoint checks remain opt-in; CI uses deterministic offline fixtures.
- Every release is built from the source distribution and smoke-tested before
  publication.
- Weekly live checks retain JUnit diagnostics without increasing pull-request
  traffic to public endpoints.
