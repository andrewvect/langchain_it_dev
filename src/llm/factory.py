"""
LLM factory — swap provider/model in config.py without touching agents.

Providers:
  groq      — Groq (llama-3, etc.)
  openai    — OpenAI
  anthropic — Anthropic Claude
  copilot   — GitHub Copilot (OpenAI-compatible, token from `gh auth token`)
              Models: gpt-4o, gpt-4o-mini, claude-3.5-sonnet, o1-mini, o3-mini
"""

import subprocess
from typing import cast

from langchain_core.language_models import BaseChatModel

from config import LLM_MODEL, LLM_PROVIDER, LLM_TEMPERATURE, get_llm_api_key


def _get_gh_token() -> str:
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def get_llm() -> BaseChatModel:
    api_key = get_llm_api_key()

    if LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq

        return cast(
            BaseChatModel,
            ChatGroq(model=LLM_MODEL, temperature=LLM_TEMPERATURE, api_key=api_key),  # type: ignore[arg-type]
        )

    if LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI

        return cast(
            BaseChatModel, ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE, api_key=api_key)
        )

    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return cast(
            BaseChatModel,
            ChatAnthropic(model=LLM_MODEL, temperature=LLM_TEMPERATURE, api_key=api_key),
        )

    if LLM_PROVIDER == "copilot":
        from langchain_openai import ChatOpenAI

        return cast(
            BaseChatModel,
            ChatOpenAI(
                model=LLM_MODEL,
                temperature=LLM_TEMPERATURE,
                api_key=_get_gh_token(),
                base_url="https://api.githubcopilot.com",
            ),
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")
