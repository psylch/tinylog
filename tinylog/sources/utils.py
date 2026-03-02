"""Shared utilities for source adapters."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable

from .base import DailyMetrics, Message


def ts_to_date(ts: int | float) -> str:
    """Unix timestamp to YYYY-MM-DD string."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def date_to_ts(date_str: str) -> float:
    """YYYY-MM-DD to start-of-day unix timestamp."""
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


def date_range_to_ts(date_from: str, date_to: str) -> tuple[float, float]:
    """Convert date range strings to (start_ts, end_of_day_ts) tuple."""
    return date_to_ts(date_from), date_to_ts(date_to) + 86400


def parse_json(raw: Any) -> Any:
    """Parse JSON that may be double-encoded."""
    if raw is None:
        return None
    if isinstance(raw, str):
        parsed = json.loads(raw)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        return parsed
    return raw


def stringify_content(content: Any) -> str:
    """Ensure content is a string — serialize non-strings as JSON."""
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False) if content else ""


def open_readonly_db(db_path: str) -> sqlite3.Connection:
    """Open a SQLite database in read-only mode with Row factory."""
    conn = sqlite3.connect(
        f"file:{db_path}?mode=ro", uri=True, check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def ordered_unique(items: Iterable[str]) -> list[str]:
    """Return unique items preserving first-occurrence order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def extract_first_query(messages: list[dict], max_len: int = 200) -> str:
    """Find the first user message content, truncated to max_len."""
    for m in messages:
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, str) and content.strip():
                return content[:max_len]
    return ""


def extract_openai_tool_calls(msg: dict) -> list[dict] | None:
    """Extract tool_calls from an OpenAI-format message dict."""
    raw_calls = msg.get("tool_calls")
    if not raw_calls:
        return None
    calls: list[dict] = []
    for tc in raw_calls:
        fn = tc.get("function", {})
        calls.append({
            "id": tc.get("id"),
            "name": fn.get("name"),
            "args": fn.get("arguments", "{}"),
        })
    return calls or None


def attach_tool_results(messages: list[Message], results: dict[str, str]) -> None:
    """Attach tool result content to matching tool_calls on Message objects."""
    for msg in messages:
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tc_id = tc.get("id")
                if tc_id and tc_id in results:
                    tc["result"] = results[tc_id]


def build_tool_stats_result(
    summary: dict[str, int],
    daily_tools: dict[str, dict[str, int]],
) -> dict:
    """Build the standard tool stats return dict from accumulated data."""
    daily_list: list[dict] = []
    for date in sorted(daily_tools.keys()):
        entry: dict[str, Any] = {"date": date}
        entry.update(daily_tools[date])
        daily_list.append(entry)
    return {"summary": dict(summary), "daily": daily_list}


def build_daily_metrics(
    daily: dict[str, dict],
) -> list[DailyMetrics]:
    """Convert daily buckets dict into sorted list of DailyMetrics.

    Each bucket must have: sessions, messages, total_tokens, input_tokens,
    output_tokens. Optional: durations (list[float]), ttfts (list[float]).
    """
    result: list[DailyMetrics] = []
    for date in sorted(daily.keys()):
        d = daily[date]
        durations = d.get("durations", [])
        ttfts = d.get("ttfts", [])
        result.append(DailyMetrics(
            date=date,
            sessions=d["sessions"],
            messages=d["messages"],
            total_tokens=d["total_tokens"],
            input_tokens=d["input_tokens"],
            output_tokens=d["output_tokens"],
            avg_duration=sum(durations) / len(durations) if durations else None,
            avg_ttft=sum(ttfts) / len(ttfts) if ttfts else None,
        ))
    return result


def new_daily_bucket() -> dict:
    """Create a fresh daily metrics accumulation bucket."""
    return {
        "sessions": 0,
        "messages": 0,
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "durations": [],
        "ttfts": [],
    }
