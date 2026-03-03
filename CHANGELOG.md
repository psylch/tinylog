# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-03-02

### Added

- Markdown rendering with code syntax highlighting in conversation replay
- Mobile responsive design (hamburger menu, touch-friendly targets, iOS zoom prevention)
- GitHub Actions CI pipeline (Python 3.11/3.12 matrix, ruff, pytest, frontend build)
- Test fixtures for all 6 source adapters (34 tests)
- CLI `--version` flag
- Ambient glow UI effects and card hover animations
- Docker support with multi-stage build

### Changed

- Backend error handling: all API routes wrapped with try/except and structured logging
- ADK adapter: N+1 queries replaced with batch JOIN
- Authentication uses timing-safe `hmac.compare_digest()`
- README rewritten with badges, "Why TinyLog" section, and multi-framework Quick Start

### Fixed

- Shared source utilities refactored to eliminate code duplication across adapters

## [0.1.0] - 2026-03-01

### Added

- Initial release
- Dashboard with session/message/token/TTFT analytics and trend charts
- Sessions list with search, pagination, and detail drawer (with tool call expansion)
- Support for 6 source adapters: Agno, LangChain, AutoGen, Google ADK, Claude Agent SDK, JSON Import
- Dark/Light theme toggle with pure CSS design system
- File management with image grid preview and lightbox

[Unreleased]: https://github.com/psylch/tinylog/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/psylch/tinylog/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/psylch/tinylog/releases/tag/v0.1.0
