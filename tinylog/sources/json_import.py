"""JSONImportSource: reads a directory of JSON files as session data."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from .base import (
    DataSource,
    DailyMetrics,
    Message,
    SessionDetail,
    SessionSummary,
)
from .utils import (
    build_daily_metrics,
    build_tool_stats_result,
    date_range_to_ts,
    extract_first_query,
    new_daily_bucket,
    ordered_unique,
    stringify_content,
    ts_to_date,
)


def _load_session_file(path: Path) -> dict | None:
    """Load and parse a single JSON session file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        # Fall back session_id to filename stem
        if "session_id" not in data:
            data["session_id"] = path.stem
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _get_created_at(data: dict, path: Path) -> float:
    """Get created_at from data, first message, or file mtime."""
    if "created_at" in data and data["created_at"] is not None:
        return float(data["created_at"])
    messages = data.get("messages", [])
    if messages and "created_at" in messages[0] and messages[0]["created_at"] is not None:
        return float(messages[0]["created_at"])
    return os.path.getmtime(path)


def _get_updated_at(data: dict) -> float | None:
    if "updated_at" in data and data["updated_at"] is not None:
        return float(data["updated_at"])
    messages = data.get("messages", [])
    if messages and "created_at" in messages[-1] and messages[-1]["created_at"] is not None:
        return float(messages[-1]["created_at"])
    return None


def _aggregate_tokens(messages: list[dict]) -> tuple[int, int, int]:
    """Sum token usage across all messages."""
    total = input_t = output_t = 0
    for m in messages:
        usage = m.get("usage")
        if usage and isinstance(usage, dict):
            total += usage.get("total_tokens", 0) or 0
            input_t += usage.get("input_tokens", 0) or 0
            output_t += usage.get("output_tokens", 0) or 0
    return total, input_t, output_t


def _extract_tool_names(messages: list[dict]) -> list[str]:
    """Get deduplicated tool names from messages."""
    def _names():
        for m in messages:
            for tc in m.get("tool_calls", []) or []:
                yield tc.get("name", "")
            if m.get("role") == "tool":
                yield m.get("tool_name", "")
    return ordered_unique(_names())


def _compute_duration(messages: list[dict]) -> float | None:
    """Compute session duration from first to last message timestamps."""
    timestamps = [
        float(m["created_at"]) for m in messages
        if m.get("created_at") is not None
    ]
    if len(timestamps) >= 2:
        return round(max(timestamps) - min(timestamps), 2)
    return None


def _build_message(idx: int, m: dict) -> Message:
    """Convert a raw message dict to a Message dataclass."""
    role = m.get("role", "unknown")
    content = m.get("content", "")

    # Tool calls on assistant messages
    tool_calls = None
    raw_tc = m.get("tool_calls")
    if raw_tc:
        tool_calls = []
        for tc in raw_tc:
            tool_calls.append({
                "id": tc.get("id"),
                "name": tc.get("name"),
                "args": tc.get("arguments"),
            })

    # Token metrics from usage
    token_metrics = None
    usage = m.get("usage")
    if usage and isinstance(usage, dict):
        token_metrics = usage

    return Message(
        index=idx,
        role=role,
        content=stringify_content(content),
        created_at=float(m["created_at"]) if m.get("created_at") is not None else None,
        token_metrics=token_metrics,
        tool_calls=tool_calls,
        tool_name=m.get("tool_name") if role == "tool" else None,
        tool_call_id=m.get("tool_call_id") if role == "tool" else None,
    )


# Cached session entry for list_sessions
class _CachedSession:
    __slots__ = ("session_id", "created_at", "updated_at", "model", "messages",
                 "first_query", "message_count", "total_tokens", "input_tokens",
                 "output_tokens", "duration", "tool_names", "path")

    def __init__(self, data: dict, path: Path):
        messages = data.get("messages", [])
        total, input_t, output_t = _aggregate_tokens(messages)
        self.session_id: str = data["session_id"]
        self.created_at: float = _get_created_at(data, path)
        self.updated_at: float | None = _get_updated_at(data)
        self.model: str | None = data.get("model")
        self.messages: list[dict] = messages
        self.first_query: str = extract_first_query(messages)
        self.message_count: int = len(messages)
        self.total_tokens: int = total
        self.input_tokens: int = input_t
        self.output_tokens: int = output_t
        self.duration: float | None = _compute_duration(messages)
        self.tool_names: list[str] = _extract_tool_names(messages)
        self.path: Path = path


class JSONImportSource(DataSource):
    """Reads a directory of JSON files, each representing one session."""

    def __init__(self, dir_path: str):
        self.dir_path = Path(dir_path)
        self._sessions: dict[str, _CachedSession] = {}
        self._sorted_ids: list[str] = []
        self._load_all()

    def _load_all(self) -> None:
        sessions: dict[str, _CachedSession] = {}
        for path in self.dir_path.glob("*.json"):
            data = _load_session_file(path)
            if data is None:
                continue
            cached = _CachedSession(data, path)
            sessions[cached.session_id] = cached
        self._sessions = sessions
        # Sort by created_at descending
        self._sorted_ids = sorted(
            sessions.keys(),
            key=lambda sid: sessions[sid].created_at,
            reverse=True,
        )

    def list_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        date_from: float | None = None,
        date_to: float | None = None,
        keyword: str | None = None,
        sort: str = "created_at_desc",
    ) -> tuple[list[SessionSummary], int]:
        # Filter
        filtered: list[_CachedSession] = []
        for sid in self._sorted_ids:
            s = self._sessions[sid]
            if date_from is not None and s.created_at < date_from:
                continue
            if date_to is not None and s.created_at > date_to:
                continue
            if keyword:
                kw = keyword.lower()
                found = False
                for m in s.messages:
                    content = m.get("content", "")
                    if isinstance(content, str) and kw in content.lower():
                        found = True
                        break
                if not found:
                    continue
            filtered.append(s)

        # Sort
        reverse = sort.endswith("_desc")
        if sort.startswith("tokens"):
            filtered.sort(key=lambda s: s.total_tokens, reverse=reverse)
        elif sort.startswith("created_at"):
            filtered.sort(key=lambda s: s.created_at, reverse=reverse)

        total = len(filtered)
        offset = (page - 1) * page_size
        page_items = filtered[offset:offset + page_size]

        items = [
            SessionSummary(
                session_id=s.session_id,
                created_at=s.created_at,
                updated_at=s.updated_at,
                first_query=s.first_query,
                message_count=s.message_count,
                model=s.model,
                status="COMPLETED",
                total_tokens=s.total_tokens,
                input_tokens=s.input_tokens,
                output_tokens=s.output_tokens,
                duration=s.duration,
                ttft=None,
                tool_names=s.tool_names,
                has_images=False,
            )
            for s in page_items
        ]

        return items, total

    def get_session(self, session_id: str) -> SessionDetail | None:
        cached = self._sessions.get(session_id)
        if cached is None:
            return None

        messages = [_build_message(idx, m) for idx, m in enumerate(cached.messages)]

        # Build tools list from tool messages
        tools: list[dict] = []
        for m in cached.messages:
            if m.get("role") == "tool":
                tools.append({
                    "tool_call_id": m.get("tool_call_id"),
                    "tool_name": m.get("tool_name"),
                    "tool_args": None,
                    "result": m.get("content"),
                    "created_at": m.get("created_at"),
                })

        # Enrich assistant tool_calls with args and results from tool messages
        tool_results = {t["tool_call_id"]: t.get("result") for t in tools if t.get("tool_call_id")}
        for msg in messages:
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_id = tc.get("id")
                    if tc_id and tc_id in tool_results:
                        tc["result"] = tool_results[tc_id]

        # Also populate tool_args from assistant tool_calls
        tc_args_map: dict[str, Any] = {}
        for m in cached.messages:
            for tc in m.get("tool_calls", []) or []:
                if tc.get("id"):
                    tc_args_map[tc["id"]] = tc.get("arguments")
        for t in tools:
            tid = t.get("tool_call_id")
            if tid and tid in tc_args_map:
                t["tool_args"] = tc_args_map[tid]

        metrics = {
            "total_tokens": cached.total_tokens,
            "input_tokens": cached.input_tokens,
            "output_tokens": cached.output_tokens,
            "duration": cached.duration,
        }

        return SessionDetail(
            session_id=session_id,
            created_at=cached.created_at,
            model=cached.model,
            metrics=metrics,
            messages=messages,
            tools=tools,
            files=[],
        )

    def get_daily_metrics(self, date_from: str, date_to: str) -> list[DailyMetrics]:
        ts_from, ts_to = date_range_to_ts(date_from, date_to)

        daily: dict[str, dict] = defaultdict(new_daily_bucket)

        for s in self._sessions.values():
            if s.created_at < ts_from or s.created_at >= ts_to:
                continue
            date = ts_to_date(s.created_at)
            d = daily[date]
            d["sessions"] += 1
            d["messages"] += s.message_count
            d["total_tokens"] += s.total_tokens
            d["input_tokens"] += s.input_tokens
            d["output_tokens"] += s.output_tokens
            if s.duration is not None:
                d["durations"].append(s.duration)

        return build_daily_metrics(daily)

    def get_tool_stats(self, date_from: str, date_to: str) -> dict:
        ts_from, ts_to = date_range_to_ts(date_from, date_to)

        summary: dict[str, int] = defaultdict(int)
        daily_tools: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for s in self._sessions.values():
            if s.created_at < ts_from or s.created_at >= ts_to:
                continue
            date = ts_to_date(s.created_at)
            for m in s.messages:
                for tc in m.get("tool_calls", []) or []:
                    name = tc.get("name", "unknown")
                    summary[name] += 1
                    daily_tools[date][name] += 1

        return build_tool_stats_result(summary, daily_tools)


# Register this source adapter
from . import register_source  # noqa: E402

register_source("json-import", JSONImportSource)
