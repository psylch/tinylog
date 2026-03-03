# Contributing to TinyLog

Thanks for your interest in contributing! This guide will help you get started.

## Prerequisites

- Python 3.11+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Development Setup

```bash
# Clone the repo
git clone https://github.com/psylch/tinylog.git
cd tinylog

# Install Python dependencies
uv sync --extra dev

# Install frontend dependencies
cd frontend
npm install
cd ..
```

## Running Locally

Start the backend and frontend in separate terminals:

```bash
# Terminal 1 — Backend
uv run tinylog --db /path/to/your/sessions.db --port 7891

# Terminal 2 — Frontend (Vite dev server with API proxy)
cd frontend
npm run dev
```

Make sure the proxy target port in `frontend/vite.config.ts` matches your backend port.

## Running Tests

```bash
# Python tests
uv run pytest

# Python linting
uv run ruff check .

# Frontend lint + type check
cd frontend
npm run lint

# Frontend production build (catches TS errors)
npm run build
```

## Adding a New Source Adapter

TinyLog uses a plugin-style adapter system for different LLM frameworks. To add a new one:

1. Create `tinylog/sources/your_adapter.py`
2. Subclass `DataSource` from `tinylog/sources/base.py` and implement:
   - `list_sessions()` — paginated session listing
   - `get_session()` — single session with messages and tool calls
   - `get_daily_metrics()` — daily aggregated stats
   - `get_tool_stats()` — tool usage breakdown
3. Call `register_source("your-adapter", YourAdapterClass)` at module level
4. Add the import to `tinylog/sources/__init__.py`
5. Add detection logic to `tinylog/sources/detect.py`
6. Add a test fixture in `tests/` with sample data

Look at any existing adapter (e.g., `agno.py`, `langchain.py`) as a reference.

## Pull Request Guidelines

- Branch from `main`
- Include tests for new functionality
- Run the full lint and test suite before submitting
- Keep PRs focused — one feature or fix per PR
- Write a clear description of what changed and why

## Code Style

- **Python**: Formatted and linted with [ruff](https://docs.astral.sh/ruff/) (line length 100, target Python 3.11)
- **TypeScript**: Linted with ESLint
- **CSS**: Pure vanilla CSS with CSS variables — **no Tailwind**. All styles live in `frontend/src/styles/index.css`. Use existing CSS variables (`--bg-*`, `--text-*`, `--accent-*`, etc.) and semantic classes (`.card`, `.btn-*`, `.input-field`). Never hardcode color values.
- **Commits**: Use conventional-style messages (e.g., `feat:`, `fix:`, `docs:`)

## Questions?

Open an issue on GitHub if anything is unclear. We are happy to help!
