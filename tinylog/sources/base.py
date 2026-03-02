"""DataSource abstract interface and shared dataclasses."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SessionSummary:
    session_id: str
    created_at: float
    updated_at: float | None
    first_query: str
    message_count: int
    model: str | None
    status: str
    total_tokens: int
    input_tokens: int
    output_tokens: int
    duration: float | None
    ttft: float | None
    tool_names: list[str]
    has_images: bool


@dataclass
class Message:
    index: int
    role: str
    content: str
    created_at: float | None
    reasoning: str | None = None
    token_metrics: dict | None = None
    tool_calls: list[dict] | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    images: list[str] | None = None


@dataclass
class SessionDetail:
    session_id: str
    created_at: float
    model: str | None
    metrics: dict
    messages: list[Message]
    tools: list[dict]
    files: list[dict]


@dataclass
class DailyMetrics:
    date: str
    sessions: int
    messages: int
    total_tokens: int
    input_tokens: int
    output_tokens: int
    avg_duration: float | None
    avg_ttft: float | None


class DataSource(ABC):
    """Abstract data source interface."""

    @abstractmethod
    def list_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        date_from: float | None = None,
        date_to: float | None = None,
        keyword: str | None = None,
        sort: str = "created_at_desc",
    ) -> tuple[list[SessionSummary], int]:
        ...

    @abstractmethod
    def get_session(self, session_id: str) -> SessionDetail | None:
        ...

    @abstractmethod
    def get_daily_metrics(self, date_from: str, date_to: str) -> list[DailyMetrics]:
        ...

    @abstractmethod
    def get_tool_stats(self, date_from: str, date_to: str) -> dict:
        ...
