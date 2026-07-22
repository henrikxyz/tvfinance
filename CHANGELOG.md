# Changelog

## 26.0.1

- Added prominent TradingView policy and AI-generated-content disclosures.
- Clarified provider data rights, restricted uses, and MCP-specific risks.
- Simplified the README and added project status badges.
- Updated project authorship and copyright information.
- Updated GitHub Actions to Node.js 24-based action releases.

## 26.0.0

- Rebuilt the package around typed async-first domain services.
- Unified sync, async, CLI, and optional MCP interfaces.
- Added resilient transport, retry, in-memory cache, and structured errors.
- Added quotes, streaming updates, history, screening, options, calendars,
  news, and symbol research services.
- Added strict Ruff, mypy, pytest coverage, documentation, and build gates.
- Consolidated MCP installation under the tvfinance[mcp] extra.
- Raised statement and branch coverage enforcement to 100%.
- Added cross-asset contract fixtures and weekly provider compatibility checks.
- Added a persistent SQLite TTL/LRU cache backend.
- Added a machine-readable capability inventory and compatibility procedure.
- Added declared and CI-tested support for Python 3.14.
- Added an AI disclosure covering LLM authorship and required user review.

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Clean package foundation for the 2.0 implementation.
- Optional `cli`, `mcp`, and `all` installation extras.
- Deterministic quality and documentation workflows.
