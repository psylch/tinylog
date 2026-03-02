"""Source adapter registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import DataSource

SOURCES: dict[str, type[DataSource]] = {}


def register_source(name: str, cls: type[DataSource]) -> None:
    """Register a source adapter class under the given name."""
    SOURCES[name] = cls


def get_source(name: str) -> type[DataSource]:
    """Look up a registered source adapter class by name."""
    if name not in SOURCES:
        available = ", ".join(sorted(SOURCES.keys()))
        raise ValueError(f"Unknown source type: {name!r}. Available: {available}")
    return SOURCES[name]


def list_sources() -> list[str]:
    """Return sorted list of registered source type names."""
    return sorted(SOURCES.keys())


# Import all source modules to trigger registration.
# Each module calls register_source() at module level.
from . import agno as _agno  # noqa: E402, F401
from . import langchain as _langchain  # noqa: E402, F401
from . import autogen as _autogen  # noqa: E402, F401
from . import adk as _adk  # noqa: E402, F401
from . import claude_sdk as _claude_sdk  # noqa: E402, F401
from . import json_import as _json_import  # noqa: E402, F401
