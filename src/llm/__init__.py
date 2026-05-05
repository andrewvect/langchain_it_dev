"""LLM subsystem: direct call helpers and LangChain factory."""

from llm.copilot import (
    _COPILOT_CODE_MODEL,
    _COPILOT_FAST_MODEL,
    _COPILOT_SMART_MODEL,
    call_claude,
    call_copilot,
)
from llm.factory import get_llm

__all__ = [
    "call_claude",
    "call_copilot",
    "_COPILOT_CODE_MODEL",
    "_COPILOT_FAST_MODEL",
    "_COPILOT_SMART_MODEL",
    "get_llm",
]
