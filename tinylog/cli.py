"""CLI entry point: tinylog serve."""

from __future__ import annotations

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(prog="tinylog", description="TinyLog — LLM conversation viewer")
    subparsers = parser.add_subparsers(dest="command")

    # serve command
    serve = subparsers.add_parser("serve", help="Start the TinyLog server")
    serve.add_argument("--db", type=str, default=None, help="Path to agno_sessions.db")
    serve.add_argument("--port", type=int, default=None, help="Server port (default: 7890)")
    serve.add_argument("--host", type=str, default=None, help="Server host (default: 0.0.0.0)")
    serve.add_argument("--admin-key", type=str, default=None, help="Admin API key")
    serve.add_argument("--data-dir", type=str, default=None, help="TinyLog data directory")

    args = parser.parse_args()

    if args.command == "serve":
        _serve(args)
    else:
        parser.print_help()
        sys.exit(1)


def _serve(args):
    import uvicorn
    from .config import load_config
    from .app import create_app

    config = load_config(
        db_path=args.db,
        port=args.port,
        host=args.host,
        admin_key=args.admin_key,
        data_dir=args.data_dir,
    )

    if not config.db_path:
        print("Error: --db path is required (or set TINYLOG_DB env var)", file=sys.stderr)
        sys.exit(1)

    app = create_app(config)
    print(f"TinyLog starting on http://{config.host}:{config.port}")
    print(f"  Source: {config.source_type} ({config.db_path})")
    print(f"  Data dir: {config.data_dir}")
    print(f"  Auth: {'enabled' if config.admin_key else 'disabled'}")

    uvicorn.run(app, host=config.host, port=config.port, log_level="info")
