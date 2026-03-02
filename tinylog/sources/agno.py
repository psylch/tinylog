"""AgnoSource: read-only adapter for Agno's agno_sessions.db."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .base import (
    DataSource,
    DailyMetrics,
    Message,
    SessionDetail,
    SessionSummary,
)


def _ts_to_date(ts: int | float) -> str:
    """Unix timestamp to YYYY-MM-DD string."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def _date_to_ts(date_str: str) -> float:
    """YYYY-MM-DD to start-of-day unix timestamp."""
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


def _parse_json(raw: Any) -> Any:
    """Parse JSON that may be double-encoded."""
    if raw is None:
        return None
    if isinstance(raw, str):
        parsed = json.loads(raw)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        return parsed
    return raw


def _extract_session_metrics(session_data: Any) -> dict:
    """Extract session_metrics from session_data JSON."""
    data = _parse_json(session_data)
    if not data:
        return {}
    return data.get("session_metrics", {}) or {}


def _extract_model(agent_data: Any) -> str | None:
    """Extract model ID from agent_data JSON."""
    data = _parse_json(agent_data)
    if not data:
        return None
    model = data.get("model", {})
    if isinstance(model, dict):
        return model.get("id")
    return None


def _filter_messages(messages: list[dict]) -> list[dict]:
    """Filter out system messages and from_history messages."""
    return [
        m for m in messages
        if m.get("role") != "system" and not m.get("from_history")
    ]


def _extract_first_query(messages: list[dict]) -> str:
    """Get first user message content, truncated to 200 chars."""
    for m in messages:
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, str):
                return content[:200]
    return ""


def _extract_tool_names(runs: list[dict]) -> list[str]:
    """Get deduplicated tool names from all runs."""
    names: list[str] = []
    seen: set[str] = set()
    for run in runs:
        for tool in run.get("tools", []) or []:
            name = tool.get("tool_name", "")
            if name and name not in seen:
                seen.add(name)
                names.append(name)
    return names


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
            fn = tc.get("function", {})
            tool_calls.append({
                "id": tc.get("id"),
                "name": fn.get("name"),
                "args": fn.get("arguments"),
            })

    # Token metrics from assistant messages
    token_metrics = None
    raw_metrics = m.get("metrics")
    if raw_metrics and isinstance(raw_metrics, dict) and raw_metrics:
        token_metrics = raw_metrics

    return Message(
        index=idx,
        role=role,
        content=content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
        created_at=m.get("created_at"),
        reasoning=m.get("reasoning_content") or None,
        token_metrics=token_metrics,
        tool_calls=tool_calls,
        tool_name=m.get("tool_name"),
        tool_call_id=m.get("tool_call_id"),
    )


class AgnoSource(DataSource):
    """Read-only adapter for Agno's agno_sessions.db."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(
            f"file:{db_path}?mode=ro", uri=True, check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row

    def list_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        date_from: float | None = None,
        date_to: float | None = None,
        keyword: str | None = None,
        sort: str = "created_at_desc",
    ) -> tuple[list[SessionSummary], int]:
        conditions: list[str] = []
        params: list[Any] = []

        if date_from is not None:
            conditions.append("created_at >= ?")
            params.append(int(date_from))
        if date_to is not None:
            conditions.append("created_at <= ?")
            params.append(int(date_to))
        if keyword:
            conditions.append("runs LIKE ?")
            params.append(f"%{keyword}%")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Sort
        sort_map = {
            "created_at_desc": "created_at DESC",
            "created_at_asc": "created_at ASC",
            "tokens_desc": "json_extract(session_data, '$.session_metrics.total_tokens') DESC",
            "tokens_asc": "json_extract(session_data, '$.session_metrics.total_tokens') ASC",
        }
        order_by = sort_map.get(sort, "created_at DESC")

        # Count
        total = self._conn.execute(
            f"SELECT COUNT(*) FROM agno_sessions {where}", params
        ).fetchone()[0]

        # Fetch page
        offset = (page - 1) * page_size
        rows = self._conn.execute(
            f"""SELECT session_id, session_data, agent_data, runs, created_at, updated_at
                FROM agno_sessions {where}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        ).fetchall()

        items: list[SessionSummary] = []
        for row in rows:
            metrics = _extract_session_metrics(row["session_data"])
            runs = _parse_json(row["runs"]) or []
            all_messages = []
            for run in runs:
                all_messages.extend(run.get("messages", []))
            filtered = _filter_messages(all_messages)

            # TTFT: from first run's metrics
            ttft = None
            if runs:
                run_metrics = runs[0].get("metrics", {}) or {}
                ttft = run_metrics.get("time_to_first_token")

            # Status: from first run
            status = "COMPLETED"
            if runs:
                status = runs[0].get("status", "COMPLETED") or "COMPLETED"

            items.append(SessionSummary(
                session_id=row["session_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                first_query=_extract_first_query(filtered),
                message_count=len(filtered),
                model=_extract_model(row["agent_data"]),
                status=status,
                total_tokens=metrics.get("total_tokens", 0) or 0,
                input_tokens=metrics.get("input_tokens", 0) or 0,
                output_tokens=metrics.get("output_tokens", 0) or 0,
                duration=metrics.get("duration"),
                ttft=ttft,
                tool_names=_extract_tool_names(runs),
                has_images=False,  # TODO: check for images
            ))

        return items, total

    def get_session(self, session_id: str) -> SessionDetail | None:
        row = self._conn.execute(
            "SELECT * FROM agno_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None

        metrics = _extract_session_metrics(row["session_data"])
        model = _extract_model(row["agent_data"])
        runs = _parse_json(row["runs"]) or []

        # Build messages from all runs
        all_messages: list[dict] = []
        for run in runs:
            all_messages.extend(run.get("messages", []))
        filtered = _filter_messages(all_messages)

        messages = [_build_message(idx, m) for idx, m in enumerate(filtered)]

        # Collect tools from all runs
        tools: list[dict] = []
        for run in runs:
            for t in run.get("tools", []) or []:
                tools.append({
                    "tool_call_id": t.get("tool_call_id"),
                    "tool_name": t.get("tool_name"),
                    "tool_args": t.get("tool_args"),
                    "result": t.get("result"),
                    "created_at": t.get("created_at"),
                })

        # Add tool results to assistant message tool_calls
        tool_results = {t["tool_call_id"]: t.get("result") for t in tools if t.get("tool_call_id")}
        for msg in messages:
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_id = tc.get("id")
                    if tc_id and tc_id in tool_results:
                        tc["result"] = tool_results[tc_id]

        return SessionDetail(
            session_id=session_id,
            created_at=row["created_at"],
            model=model,
            metrics=metrics,
            messages=messages,
            tools=tools,
            files=[],  # populated by API layer from tinylog.db
        )

    def get_daily_metrics(self, date_from: str, date_to: str) -> list[DailyMetrics]:
        ts_from = _date_to_ts(date_from)
        ts_to = _date_to_ts(date_to) + 86400  # include the end date

        rows = self._conn.execute(
            """SELECT session_id, session_data, runs, created_at
               FROM agno_sessions
               WHERE created_at >= ? AND created_at < ?
               ORDER BY created_at""",
            (int(ts_from), int(ts_to)),
        ).fetchall()

        # Group by date
        daily: dict[str, dict] = defaultdict(lambda: {
            "sessions": 0,
            "messages": 0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "durations": [],
            "ttfts": [],
        })

        for row in rows:
            date = _ts_to_date(row["created_at"])
            d = daily[date]
            d["sessions"] += 1

            metrics = _extract_session_metrics(row["session_data"])
            d["total_tokens"] += metrics.get("total_tokens", 0) or 0
            d["input_tokens"] += metrics.get("input_tokens", 0) or 0
            d["output_tokens"] += metrics.get("output_tokens", 0) or 0
            dur = metrics.get("duration")
            if dur is not None:
                d["durations"].append(dur)

            runs = _parse_json(row["runs"]) or []
            for run in runs:
                all_msgs = run.get("messages", [])
                filtered = _filter_messages(all_msgs)
                d["messages"] += len(filtered)
                run_metrics = run.get("metrics", {}) or {}
                ttft = run_metrics.get("time_to_first_token")
                if ttft is not None:
                    d["ttfts"].append(ttft)

        result = []
        for date in sorted(daily.keys()):
            d = daily[date]
            avg_dur = sum(d["durations"]) / len(d["durations"]) if d["durations"] else None
            avg_ttft = sum(d["ttfts"]) / len(d["ttfts"]) if d["ttfts"] else None
            result.append(DailyMetrics(
                date=date,
                sessions=d["sessions"],
                messages=d["messages"],
                total_tokens=d["total_tokens"],
                input_tokens=d["input_tokens"],
                output_tokens=d["output_tokens"],
                avg_duration=round(avg_dur, 2) if avg_dur is not None else None,
                avg_ttft=round(avg_ttft, 3) if avg_ttft is not None else None,
            ))

        return result

    def get_tool_stats(self, date_from: str, date_to: str) -> dict:
        ts_from = _date_to_ts(date_from)
        ts_to = _date_to_ts(date_to) + 86400

        rows = self._conn.execute(
            """SELECT runs, created_at
               FROM agno_sessions
               WHERE created_at >= ? AND created_at < ?""",
            (int(ts_from), int(ts_to)),
        ).fetchall()

        summary: dict[str, int] = defaultdict(int)
        daily_tools: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for row in rows:
            date = _ts_to_date(row["created_at"])
            runs = _parse_json(row["runs"]) or []
            for run in runs:
                for tool in run.get("tools", []) or []:
                    name = tool.get("tool_name", "unknown")
                    summary[name] += 1
                    daily_tools[date][name] += 1

        daily_list = []
        for date in sorted(daily_tools.keys()):
            entry = {"date": date}
            entry.update(daily_tools[date])
            daily_list.append(entry)

        return {
            "summary": dict(summary),
            "daily": daily_list,
        }
