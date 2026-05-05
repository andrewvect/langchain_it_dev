import json
import os
from pathlib import Path
from typing import Any

# ─── LLM Configuration (overridable via env vars) ────────────────────────────
# groq | anthropic | copilot
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.3"))

# ─── Graph Configuration ──────────────────────────────────────────────────────
MAX_REVIEW_ITERATIONS = int(os.environ.get("MAX_REVIEW_ITERATIONS", "5"))
HUMAN_IN_THE_LOOP = os.environ.get(
    "HUMAN_IN_THE_LOOP", "True").lower() not in ("false", "0", "no")
AGENT_TIMEOUT = int(os.environ.get("AGENT_TIMEOUT", "3000"))

# ─── Database ─────────────────────────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "it_team.db")

# ─── Secrets ──────────────────────────────────────────────────────────────────
_SECRETS_PATH = Path("~/.agent_keys/secrets.json")


def load_secrets() -> dict[str, Any]:
    with open(_SECRETS_PATH) as f:
        return json.load(f)  # type: ignore[no-any-return]


def get_jira_config() -> dict[str, str]:
    secrets = load_secrets()
    jira = secrets.get("jira", {})
    return {
        "base_url": jira.get("base_url", ""),
        "email": jira.get("email", ""),
        "api_token": jira.get("api_token", ""),
    }


def get_llm_api_key() -> str:
    if LLM_PROVIDER == "copilot":
        return ""  # token is fetched via `gh auth token` in llm_factory
    secrets = load_secrets()
    mapping: dict[str, Any] = {
        "groq": secrets.get("groq", {}).get("api_key") or secrets.get("groq"),
        "anthropic": secrets.get("anthropic"),
    }
    key: Any = mapping.get(LLM_PROVIDER)
    if isinstance(key, dict):
        key = key.get("api_key")
    if not key:
        raise ValueError(
            f"API key for provider '{LLM_PROVIDER}' not found in secrets.json")
    return str(key)
