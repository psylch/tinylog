"""LangChainSource: read-only adapter for LangChain's SQLChatMessageHistory SQLite database."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from .base import (
    DataSource,
    DailyMetrics,
    Message,
    SessionDetail,
    SessionSummary,
)
from .utils import (
    open_readonly_db,
    parse_json,
    ts_to_date,
)


_ROLE_MAP = {
    "human": "user",
    "ai": "assistant",
    "tool": "tool",
    "system": "system",
}


def _parse_message(raw_message: Any) -> dict | None:
    data = parse_json(raw_message)
    if not data or not isinstance(data, dict):
        return None
    return data


def _get_role(msg: dict) -> str:
    return _ROLE_MAP.get(msg.get("type", ""), "unknown")


def _get_content(msg: dict) -> str:
    data = msg.get("data", {})
    content = data.get("content", "")
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


def _get_token_usage(msg: dict) -> dict[str, int] | None:
    if msg.get("type") != "ai":
        return None
    data = msg.get("data", {})
    resp_meta = data.get("response_metadata", {}) or {}
    usage = resp_meta.get("token_usage")
    if usage and isinstance(usage, dict):
        return {
            "input_tokens": usage.get("prompt_tokens", 0) or 0,
            "output_tokens": usage.get("completion_tokens", 0) or 0,
            "total_tokens": usage.get("total_tokens", 0) or 0,
        }
    usage_meta = data.get("usage_metadata") or resp_meta.get("usage_metadata")
    if usage_meta and isinstance(usage_meta, dict):
        return {
            "input_tokens": usage_meta.get("input_tokens", 0) or 0,
            "output_tokens": usage_meta.get("output_tokens", 0) or 0,
            "total_tokens": usage_meta.get("total_tokens", 0) or 0,
        }
    return None


def _get_tool_calls(msg: dict) -> list[dict] | None:
    if msg.get("type") != "ai":
        return None
    data = msg.get("data", {})
    kwargs = data.get("additional_kwargs", {}) or {}
    raw_calls = kwargs.get("tool_calls")
    if not raw_calls:
        return None
    calls = []
    for tc in raw_calls:
        fn = tc.get("function", {})
        calls.append({
            "id": tc.get("id"),
            "name": fn.get("name"),
            "args": fn.get("arguments"),
        })
    return calls or None


def _get_model(msg: dict) -> str | None:
    if msg.get("type") != "ai":
        return None
    data = msg.get("data", {})
    resp_meta = data.get("response_metadata", {}) or {}
    return resp_meta.get("model_name") or resp_meta.get("model")


def _is_visible(msg: dict) -> bool:
    return msg.get("type") != "system"


class LangChainSource(DataSource):
    """Read-only adapter for LangChain's SQLChatMessageHistory SQLite database."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = open_readonly_db(db_path)

    def _load_session_messages(self, session_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, message FROM message_store WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        messages = []
        for row in rows:
            msg = _parse_message(row["message"])
            if msg:
                messages.append(msg)
        return messages

    def _aggregate_tokens(self, messages: list[dict]) -> tuple[int, int, int]:
        total = inp = out = 0
        for m in messages:
            usage = _get_token_usage(m)
            if usage:
                total += usage["total_tokens"]
                inp += usage["input_tokens"]
                out += usage["output_tokens"]
        return total, inp, out

    def list_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        date_from: float | None = None,
        date_to: float | None = None,
        keyword: str | None = None,
        sort: str = "created_at_desc",
    ) -> tuple[list[SessionSummary], int]:
        # LangChain has no timestamps, so date filters are ignored
        all_session_ids = [
            row[0] for row in self._conn.execute(
                "SELECT DISTINCT session_id FROM message_store"
            ).fetchall()
        ]

        from .utils import ordered_unique

        sessions: list[dict] = []
        for sid in all_session_ids:
            messages = self._load_session_messages(sid)
            visible = [m for m in messages if _is_visible(m)]

            if keyword:
                found = any(keyword.lower() in _get_content(m).lower() for m in messages)
                if not found:
                    continue

            total_tokens, input_tokens, output_tokens = self._aggregate_tokens(messages)

            tool_names = ordered_unique(
                tc.get("name", "")
                for m in messages
                for tc in (_get_tool_calls(m) or [])
            )

            model = None
            for m in messages:
                model = _get_model(m)
                if model:
                    break

            # First human query
            first_query = ""
            for m in messages:
                if m.get("type") == "human":
                    first_query = _get_content(m)[:200]
                    break

            sessions.append({
                "session_id": sid,
                "first_query": first_query,
                "message_count": len(visible),
                "model": model,
                "total_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "tool_names": tool_names,
            })

        if sort == "tokens_desc":
            sessions.sort(key=lambda s: s["total_tokens"], reverse=True)
        elif sort == "tokens_asc":
            sessions.sort(key=lambda s: s["total_tokens"])
        elif sort == "created_at_asc":
            pass
        else:
            sessions.reverse()

        total = len(sessions)
        offset = (page - 1) * page_size
        page_sessions = sessions[offset : offset + page_size]

        items = [
            SessionSummary(
                session_id=s["session_id"],
                created_at=0,
                updated_at=None,
                first_query=s["first_query"],
                message_count=s["message_count"],
                model=s["model"],
                status="COMPLETED",
                total_tokens=s["total_tokens"],
                input_tokens=s["input_tokens"],
                output_tokens=s["output_tokens"],
                duration=None,
                ttft=None,
                tool_names=s["tool_names"],
                has_images=False,
            )
            for s in page_sessions
        ]

        return items, total

    def get_session(self, session_id: str) -> SessionDetail | None:
        messages = self._load_session_messages(session_id)
        if not messages:
            return None

        total_tokens, input_tokens, output_tokens = self._aggregate_tokens(messages)

        model = None
        for m in messages:
            model = _get_model(m)
            if model:
                break

        msg_list: list[Message] = []
        tool_results: dict[str, str] = {}

        for m in messages:
            if m.get("type") == "tool":
                data = m.get("data", {})
                tcid = data.get("tool_call_id")
                if tcid:
                    tool_results[tcid] = _get_content(m)

        idx = 0
        for m in messages:
            if not _is_visible(m):
                continue

            role = _get_role(m)
            content = _get_content(m)
            tool_calls = _get_tool_calls(m)
            token_metrics = _get_token_usage(m)

            tool_name = None
            tool_call_id = None
            if m.get("type") == "tool":
                data = m.get("data", {})
                tool_name = data.get("name")
                tool_call_id = data.get("tool_call_id")

            if tool_calls:
                for tc in tool_calls:
                    tc_id = tc.get("id")
                    if tc_id and tc_id in tool_results:
                        tc["result"] = tool_results[tc_id]

            msg_list.append(Message(
                index=idx,
                role=role,
                content=content,
                created_at=None,
                token_metrics=token_metrics,
                tool_calls=tool_calls,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
            ))
            idx += 1

        tools: list[dict] = []
        for m in messages:
            calls = _get_tool_calls(m)
            if calls:
                for tc in calls:
                    tc_id = tc.get("id")
                    tools.append({
                        "tool_call_id": tc_id,
                        "tool_name": tc.get("name"),
                        "tool_args": tc.get("args"),
                        "result": tool_results.get(tc_id) if tc_id else None,
                        "created_at": None,
                    })

        metrics = {
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

        return SessionDetail(
            session_id=session_id,
            created_at=0,
            model=model,
            metrics=metrics,
            messages=msg_list,
            tools=tools,
            files=[],
        )

    def get_daily_metrics(self, date_from: str, date_to: str) -> list[DailyMetrics]:
        epoch_date = ts_to_date(0)

        all_session_ids = [
            row[0] for row in self._conn.execute(
                "SELECT DISTINCT session_id FROM message_store"
            ).fetchall()
        ]

        total_messages = 0
        total_tokens = 0
        input_tokens_sum = 0
        output_tokens_sum = 0

        for sid in all_session_ids:
            messages = self._load_session_messages(sid)
            visible = [m for m in messages if _is_visible(m)]
            total_messages += len(visible)
            t, i, o = self._aggregate_tokens(messages)
            total_tokens += t
            input_tokens_sum += i
            output_tokens_sum += o

        if not all_session_ids:
            return []

        return [DailyMetrics(
            date=epoch_date,
            sessions=len(all_session_ids),
            messages=total_messages,
            total_tokens=total_tokens,
            input_tokens=input_tokens_sum,
            output_tokens=output_tokens_sum,
            avg_duration=None,
            avg_ttft=None,
        )]

    def get_tool_stats(self, date_from: str, date_to: str) -> dict:
        epoch_date = ts_to_date(0)

        all_session_ids = [
            row[0] for row in self._conn.execute(
                "SELECT DISTINCT session_id FROM message_store"
            ).fetchall()
        ]

        summary: dict[str, int] = defaultdict(int)

        for sid in all_session_ids:
            messages = self._load_session_messages(sid)
            for m in messages:
                calls = _get_tool_calls(m)
                if calls:
                    for tc in calls:
                        name = tc.get("name", "unknown")
                        summary[name] += 1

        daily_list: list[dict[str, Any]] = []
        if summary:
            entry: dict[str, Any] = {"date": epoch_date}
            entry.update(summary)
            daily_list.append(entry)

        return {"summary": dict(summary), "daily": daily_list}


# Register this source adapter
from . import register_source  # noqa: E402

register_source("langchain", LangChainSource)
