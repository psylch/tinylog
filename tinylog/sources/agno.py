"""AgnoSource: read-only adapter for Agno's agno_sessions.db."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .base import (
    DataSource,
    Message,
    SessionDetail,
    SessionSummary,
)
from .utils import (
    attach_tool_results,
    build_daily_metrics,
    build_tool_stats_result,
    date_range_to_ts,
    extract_first_query,
    new_daily_bucket,
    open_readonly_db,
    parse_json,
    stringify_content,
    ts_to_date,
)


def _extract_session_metrics(session_data: Any) -> dict:
    """Extract session_metrics from session_data JSON."""
    data = parse_json(session_data)
    if not data:
        return {}
    return data.get("session_metrics", {}) or {}


def _extract_model(agent_data: Any) -> str | None:
    """Extract model ID from agent_data JSON."""
    data = parse_json(agent_data)
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


def _extract_tool_names(runs: list[dict]) -> list[str]:
    """Get deduplicated tool names from all runs."""
    from .utils import ordered_unique
    return ordered_unique(
        tool.get("tool_name", "")
        for run in runs
        for tool in run.get("tools", []) or []
    )


def _build_message(idx: int, m: dict) -> Message:
    """Convert a raw message dict to a Message dataclass."""
    from .utils import extract_openai_tool_calls
    role = m.get("role", "unknown")
    content = m.get("content", "")

    token_metrics = None
    raw_metrics = m.get("metrics")
    if raw_metrics and isinstance(raw_metrics, dict):
        token_metrics = raw_metrics

    return Message(
        index=idx,
        role=role,
        content=stringify_content(content),
        created_at=m.get("created_at"),
        reasoning=m.get("reasoning_content") or None,
        token_metrics=token_metrics,
        tool_calls=extract_openai_tool_calls(m),
        tool_name=m.get("tool_name"),
        tool_call_id=m.get("tool_call_id"),
    )


class AgnoSource(DataSource):
    """Read-only adapter for Agno's agno_sessions.db."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = open_readonly_db(db_path)

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

        sort_map = {
            "created_at_desc": "created_at DESC",
            "created_at_asc": "created_at ASC",
            "tokens_desc": "json_extract(session_data, '$.session_metrics.total_tokens') DESC",
            "tokens_asc": "json_extract(session_data, '$.session_metrics.total_tokens') ASC",
        }
        order_by = sort_map.get(sort, "created_at DESC")

        total = self._conn.execute(
            f"SELECT COUNT(*) FROM agno_sessions {where}", params
        ).fetchone()[0]

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
            runs = parse_json(row["runs"]) or []
            all_messages = []
            for run in runs:
                all_messages.extend(run.get("messages", []))
            filtered = _filter_messages(all_messages)

            ttft = None
            if runs:
                run_metrics = runs[0].get("metrics", {}) or {}
                ttft = run_metrics.get("time_to_first_token")

            status = "COMPLETED"
            if runs:
                status = runs[0].get("status", "COMPLETED") or "COMPLETED"

            items.append(SessionSummary(
                session_id=row["session_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                first_query=extract_first_query(filtered),
                message_count=len(filtered),
                model=_extract_model(row["agent_data"]),
                status=status,
                total_tokens=metrics.get("total_tokens", 0) or 0,
                input_tokens=metrics.get("input_tokens", 0) or 0,
                output_tokens=metrics.get("output_tokens", 0) or 0,
                duration=metrics.get("duration"),
                ttft=ttft,
                tool_names=_extract_tool_names(runs),
                has_images=False,
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
        runs = parse_json(row["runs"]) or []

        all_messages: list[dict] = []
        for run in runs:
            all_messages.extend(run.get("messages", []))
        filtered = _filter_messages(all_messages)

        messages = [_build_message(idx, m) for idx, m in enumerate(filtered)]

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

        tool_results = {t["tool_call_id"]: t.get("result") for t in tools if t.get("tool_call_id")}
        attach_tool_results(messages, tool_results)

        return SessionDetail(
            session_id=session_id,
            created_at=row["created_at"],
            model=model,
            metrics=metrics,
            messages=messages,
            tools=tools,
            files=[],
        )

    def get_daily_metrics(self, date_from: str, date_to: str) -> list:
        ts_from, ts_to = date_range_to_ts(date_from, date_to)

        rows = self._conn.execute(
            """SELECT session_id, session_data, runs, created_at
               FROM agno_sessions
               WHERE created_at >= ? AND created_at < ?
               ORDER BY created_at""",
            (int(ts_from), int(ts_to)),
        ).fetchall()

        daily: dict[str, dict] = defaultdict(new_daily_bucket)

        for row in rows:
            date = ts_to_date(row["created_at"])
            d = daily[date]
            d["sessions"] += 1

            metrics = _extract_session_metrics(row["session_data"])
            d["total_tokens"] += metrics.get("total_tokens", 0) or 0
            d["input_tokens"] += metrics.get("input_tokens", 0) or 0
            d["output_tokens"] += metrics.get("output_tokens", 0) or 0
            dur = metrics.get("duration")
            if dur is not None:
                d["durations"].append(dur)

            runs = parse_json(row["runs"]) or []
            for run in runs:
                all_msgs = run.get("messages", [])
                filtered = _filter_messages(all_msgs)
                d["messages"] += len(filtered)
                run_metrics = run.get("metrics", {}) or {}
                ttft = run_metrics.get("time_to_first_token")
                if ttft is not None:
                    d["ttfts"].append(ttft)

        return build_daily_metrics(daily)

    def get_tool_stats(self, date_from: str, date_to: str) -> dict:
        ts_from, ts_to = date_range_to_ts(date_from, date_to)

        rows = self._conn.execute(
            """SELECT runs, created_at
               FROM agno_sessions
               WHERE created_at >= ? AND created_at < ?""",
            (int(ts_from), int(ts_to)),
        ).fetchall()

        summary: dict[str, int] = defaultdict(int)
        daily_tools: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for row in rows:
            date = ts_to_date(row["created_at"])
            runs = parse_json(row["runs"]) or []
            for run in runs:
                for tool in run.get("tools", []) or []:
                    name = tool.get("tool_name", "unknown")
                    summary[name] += 1
                    daily_tools[date][name] += 1

        return build_tool_stats_result(summary, daily_tools)


# Register this source adapter
from . import register_source  # noqa: E402

register_source("agno", AgnoSource)
