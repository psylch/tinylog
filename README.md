# TinyLog

Lightweight LLM conversation viewer and analytics dashboard.

One command to see how your AI app is being used — no heavy infrastructure needed.

## Features

- **Conversation Replay** — Browse and replay full chat histories with bubble-style UI
- **Analytics Dashboard** — Session count, message volume, token usage, TTFT trends
- **Tool Call Tracking** — See which tools your agent called, with args and results
- **Image Storage** — Persist and view images from multimodal conversations
- **Dark / Light Theme** — Clean, modern UI with gold accent
- **Zero Intrusion** — Reads your existing database in read-only mode, no code changes needed

## Quick Start

```bash
pip install tinylog-llm

tinylog serve --db ./agno_sessions.db
# Open http://localhost:7890
```

## Supported Data Sources

| Source | Status |
|--------|--------|
| [Agno](https://github.com/agno-agi/agno) SQLite sessions | Supported |
| LangChain | Planned |
| Generic SQLite / JSON | Planned |

## Configuration

CLI flags, environment variables, or a `tinylog.toml` file:

```bash
# CLI
tinylog serve --db ./agno_sessions.db --port 7890 --admin-key mysecret

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
- **Frontend**: React 19 / Vite / Tailwind CSS v4 / Recharts
- **Packaging**: pip installable, frontend bundled as static files

## License

MIT
