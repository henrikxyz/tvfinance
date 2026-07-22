# Improvement roadmap

This document records the completed rebuild and its verification status for
version 26.0.0.dev0.

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
| Cross-asset contract fixtures | Complete | Eight asset and locale cases |
| Persistent cache | Complete | SQLite TTL, LRU, migration tests |
| Scheduled compatibility checks | Complete | Weekly workflow and JUnit artifact |
| Compatibility management | Complete | Capability inventory and change procedure |
| Coverage hardening | Complete | 100% statements and branches |

The public search and quote contract was tested successfully on 2026-07-22.

## Release sequence

1. Continue development under version 26.0.0.dev0.
2. Run the complete offline quality gate before every commit.
3. Run the opt-in public endpoint test before a release candidate.
4. Change to 26.0.0rc1 only when a release candidate is requested.
5. Tag and publish only after explicit approval.

## Completion condition

The continuation plan is complete. New roadmap items should only be added when
a new feature request, provider change, or release objective is approved.
