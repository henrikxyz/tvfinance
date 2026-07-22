# Changelog

## 26.0.0.dev0

- Rebuilt the package around typed async-first domain services.
- Unified sync, async, CLI, and optional MCP interfaces.
- Added resilient transport, retry, in-memory cache, and structured errors.
- Added quotes, streaming updates, history, screening, options, calendars,
  news, and symbol research services.
- Added strict Ruff, mypy, pytest coverage, documentation, and build gates.
- Consolidated MCP installation under the tvfinance[mcp] extra.

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Clean package foundation for the 2.0 implementation.
- Optional `cli`, `mcp`, and `all` installation extras.
- Deterministic quality and documentation workflows.
