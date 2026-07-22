# Improvement roadmap

This document records what the rebuild delivered and separates it from optional
future improvements. Items in the final section are not missing requirements
for version 26.0.0.dev0.

## 26.0.0.dev0 delivery status

| Area | Status | Verification |
| --- | --- | --- |
| Typed core and transport | Complete | Ruff, mypy, offline tests |
| Sync and native async APIs | Complete | Namespace and client tests |
| Quotes and live updates | Complete | Protocol fixtures and public live test |
| History and options | Complete | Protocol and parser fixtures |
| News, calendars, and research | Complete | HTTP and HTML fixtures |
| CLI and optional MCP | Complete | Command and server registration tests |
| Packaging and documentation | Complete | Strict docs and wheel smoke test |
| CI and release workflows | Complete | Local syntax validation |

The public search and quote contract was tested successfully on 2026-07-22.

## Release sequence

1. Continue development under version 26.0.0.dev0.
2. Run the complete offline quality gate before every commit.
3. Run the opt-in public endpoint test before a release candidate.
4. Change to 26.0.0rc1 only when a release candidate is requested.
5. Tag and publish only after explicit approval.

## Optional future improvements

- Broaden recorded fixtures across more asset classes and locales.
- Add a scheduled, conservatively rate-limited live compatibility workflow.
- Add a persistent cache adapter while preserving the current domain API.
- Publish compatibility notes when upstream response fields change.

These are hardening opportunities, not unfinished 26.0.0.dev0 functionality.
