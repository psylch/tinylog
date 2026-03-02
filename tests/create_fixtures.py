"""Generate test fixture databases for all source adapters."""
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def create_agno_db():
    """Create a minimal agno_sessions.db with 2 sessions."""
    db_path = FIXTURES_DIR / "agno_sessions.db"
    db_path.unlink(missing_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE agno_sessions (
        session_id TEXT PRIMARY KEY,
        session_data TEXT,
        agent_data TEXT,
        runs TEXT,
        created_at INTEGER,
        updated_at INTEGER
    )""")
    now = int(time.time())
    for i in range(2):
        session_id = f"test-session-{i + 1}"
        runs = json.dumps([{
            "messages": [
                {"role": "user", "content": f"Hello from session {i + 1}"},
                {"role": "assistant", "content": f"Hi! I'm assistant in session {i + 1}"},
            ],
            "tools": [],
            "metrics": {"time_to_first_token": 0.5},
            "status": "COMPLETED",
        }])
        session_data = json.dumps({"session_metrics": {
            "total_tokens": 100 * (i + 1),
            "input_tokens": 60 * (i + 1),
            "output_tokens": 40 * (i + 1),
        }})
        agent_data = json.dumps({"model": {"id": "gpt-4"}})
        conn.execute(
            "INSERT INTO agno_sessions VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, session_data, agent_data, runs,
             now - 3600 * i, now - 3600 * i + 60),
        )
    conn.commit()
    conn.close()


def create_langchain_db():
    """Create a minimal LangChain message_store DB."""
    db_path = FIXTURES_DIR / "langchain.db"
    db_path.unlink(missing_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE message_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        message TEXT
    )""")
    for sid in ["lc-session-1"]:
        conn.execute(
            "INSERT INTO message_store (session_id, message) VALUES (?, ?)",
            (sid, json.dumps({
                "type": "human",
                "data": {"content": "What is 2+2?"},
            })),
        )
        conn.execute(
            "INSERT INTO message_store (session_id, message) VALUES (?, ?)",
            (sid, json.dumps({
                "type": "ai",
                "data": {
                    "content": "2+2 equals 4.",
                    "response_metadata": {
                        "token_usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 5,
                            "total_tokens": 15,
                        },
                    },
                },
            })),
        )
    conn.commit()
    conn.close()


def create_autogen_db():
    """Create a minimal AutoGen chat_completions DB."""
    db_path = FIXTURES_DIR / "autogen.db"
    db_path.unlink(missing_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE chat_completions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invocation_id TEXT,
        client_id INTEGER,
        wrapper_id INTEGER,
        session_id TEXT,
        request TEXT,
        response TEXT,
        is_cached INTEGER,
        cost REAL,
        start_time TEXT,
        end_time TEXT
    )""")
    request = json.dumps({"messages": [{"role": "user", "content": "Hello"}]})
    response = json.dumps({
        "choices": [{"message": {"role": "assistant", "content": "Hi there!"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        "model": "gpt-4",
    })
    conn.execute(
        "INSERT INTO chat_completions "
        "(invocation_id, client_id, wrapper_id, session_id, request, response, "
        "is_cached, cost, start_time, end_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("inv-1", 1, 1, "ag-session-1", request, response,
         0, 0.001, "2025-01-01 10:00:00", "2025-01-01 10:00:01"),
    )
    conn.commit()
    conn.close()


def create_adk_db():
    """Create a minimal Google ADK DB."""
    db_path = FIXTURES_DIR / "adk.db"
    db_path.unlink(missing_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE StorageSession (
        app_name TEXT, user_id TEXT, id TEXT, state TEXT,
        create_time REAL, update_time REAL,
        PRIMARY KEY (app_name, user_id, id)
    )""")
    conn.execute("""CREATE TABLE StorageEvent (
        app_name TEXT, user_id TEXT, session_id TEXT,
        id TEXT, event_data TEXT, timestamp REAL
    )""")
    now = time.time()
    conn.execute(
        "INSERT INTO StorageSession VALUES (?, ?, ?, ?, ?, ?)",
        ("test-app", "test-user", "adk-session-1", "{}", now, now + 10),
    )
    event1 = json.dumps({"author": "user", "content": {"parts": [{"text": "Hi ADK"}]}})
    event2 = json.dumps({"author": "agent", "content": {"parts": [{"text": "Hello from ADK!"}]}})
    conn.execute(
        "INSERT INTO StorageEvent VALUES (?, ?, ?, ?, ?, ?)",
        ("test-app", "test-user", "adk-session-1", "ev-1", event1, now),
    )
    conn.execute(
        "INSERT INTO StorageEvent VALUES (?, ?, ?, ?, ?, ?)",
        ("test-app", "test-user", "adk-session-1", "ev-2", event2, now + 1),
    )
    conn.commit()
    conn.close()


def create_claude_sdk_fixtures():
    """Create minimal Claude SDK JSONL files."""
    sdk_dir = FIXTURES_DIR / "claude-sdk" / "test-project"
    sdk_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = sdk_dir / "sdk-session-1.jsonl"
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        json.dumps({
            "type": "user",
            "timestamp": now,
            "message": {"role": "user", "content": "What is Python?"},
        }),
        json.dumps({
            "type": "assistant",
            "timestamp": now,
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-20250514",
                "content": [{"type": "text", "text": "Python is a programming language."}],
                "usage": {"input_tokens": 10, "output_tokens": 20},
            },
        }),
    ]
    jsonl_path.write_text("\n".join(lines) + "\n")


def create_json_import_fixtures():
    """Create minimal JSON import files."""
    json_dir = FIXTURES_DIR / "json-import"
    json_dir.mkdir(parents=True, exist_ok=True)
    now = int(time.time())
    session = {
        "session_id": "json-session-1",
        "created_at": now,
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": "Hello JSON", "created_at": now},
            {
                "role": "assistant",
                "content": "Hi from JSON!",
                "created_at": now + 1,
                "usage": {"input_tokens": 5, "output_tokens": 3, "total_tokens": 8},
            },
        ],
    }
    (json_dir / "session-1.json").write_text(json.dumps(session, indent=2))


def main():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    create_agno_db()
    create_langchain_db()
    create_autogen_db()
    create_adk_db()
    create_claude_sdk_fixtures()
    create_json_import_fixtures()
    print(f"Fixtures created in {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
