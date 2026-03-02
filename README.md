# TinyLog

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://www.python.org/)
[![PyPI version](https://img.shields.io/pypi/v/tinylog-llm.svg)](https://pypi.org/project/tinylog-llm/)

**One command to see how your AI app is being used.**

Lightweight LLM conversation viewer and analytics dashboard. No heavy infrastructure, no vendor lock-in, no code changes.

## Why TinyLog?

Tools like LangSmith and OpenTelemetry are powerful — but they require SDK integration, cloud accounts, and config overhead. TinyLog takes a different approach:

- **Zero config** — Point it at your existing database and go
- **Read-only** — Never modifies your data, safe to run in production
- **Works with existing DBs** — No need to instrument your code or switch logging formats
- **No vendor lock-in** — Self-hosted, open-source, runs anywhere
- **Instant setup** — `pip install` and one command, nothing else

## Features

- **Conversation Replay** — Browse and replay full chat histories with bubble-style UI
- **Analytics Dashboard** — Session count, message volume, token usage, TTFT trends
- **Tool Call Tracking** — See which tools your agent called, with args and results
- **Image Storage** — Persist and view images from multimodal conversations
- **Dark / Light Theme** — Clean, modern UI with system-aware theming
- **Zero Intrusion** — Reads your existing database in read-only mode, no code changes needed

## Screenshots

<!-- TODO: add screenshots -->

Screenshots coming soon.

## Quick Start

```bash
pip install tinylog-llm
```

```bash
# Agno
tinylog serve --db ./agno_sessions.db

# Claude Code / Agent SDK
tinylog serve --db ~/.claude/projects --source-type claude-agent-sdk

# AutoGen (auto-detected)
tinylog serve --db ./chat_completions.db

# LangChain
tinylog serve --db ./langchain_messages.db

# Google ADK
tinylog serve --db ./adk_sessions.db --source-type google-adk

# JSON Import
tinylog serve --db ./conversations.json --source-type json

# Open http://localhost:7890
```

## Supported Data Sources

TinyLog auto-detects the source type in most cases. Use `--source-type` to override.

| Source | Format | Status |
|--------|--------|--------|
| [Agno](https://github.com/agno-agi/agno) | `agno_sessions.db` | ✅ Supported |
| [LangChain](https://github.com/langchain-ai/langchain) | SQLChatMessageHistory | ✅ Supported |
| [AutoGen](https://github.com/microsoft/autogen) | runtime_logging | ✅ Supported |
| [Google ADK](https://github.com/google/adk-python) | DatabaseSessionService | ✅ Supported |
| [Claude Code / Agent SDK](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code) | JSONL sessions | ✅ Supported |
| JSON Import | Generic JSON format | ✅ Supported |

## Configuration

CLI flags, environment variables, or a `tinylog.toml` file:

```bash
# CLI
tinylog serve --db ./agno_sessions.db --port 7890 --admin-key mysecret --source-type agno

# Environment variables
TINYLOG_DB=./agno_sessions.db
TINYLOG_PORT=7890
TINYLOG_ADMIN_KEY=mysecret
TINYLOG_DATA_DIR=./tinylog_data
```

```toml
# tinylog.toml
[server]
port = 7890
admin_key = ""

[source]
type = "agno"
db_path = "./agno_sessions.db"
```

## Docker

```bash
docker compose up -d
# Mount your database as read-only
```

```yaml
services:
  tinylog:
    build: .
    ports:
      - "7890:7890"
    volumes:
      - ./agno_sessions.db:/data/agno_sessions.db:ro
    environment:
      - TINYLOG_DB=/data/agno_sessions.db
```

## Development

```bash
# Backend
uv sync
uv run pytest tests/ -v
uv run tinylog serve --db /path/to/agno_sessions.db

# Frontend
cd frontend
npm install
npm run dev    # → http://localhost:5173 (proxies /api to :7890)
npm run build  # → dist/ (copy to tinylog/frontend/ for packaging)
```

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / SQLite (read-only)
- **Frontend**: React 19 / Vite / Custom CSS Design System (no framework) / Recharts
- **Packaging**: pip installable, frontend bundled as static files

## License

MIT
