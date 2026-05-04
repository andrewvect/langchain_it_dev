"""LLM call helpers: Claude CLI and GitHub Copilot API."""

import shutil
import subprocess

from config import AGENT_TIMEOUT

_CLAUDE_BIN = shutil.which("claude") or "claude"
_COPILOT_CODE_MODEL = "gpt-5.4"
_COPILOT_FAST_MODEL = "gpt-5-mini"

_first_claude_call = True


def reset_claude_session() -> None:
    """Reset the first-call flag so the next Claude call clears old session memory."""
    global _first_claude_call
    _first_claude_call = True


def call(system: str, human: str, agent_name: str = "", cwd: str | None = None) -> str:
    """Run a single Claude CLI call. System prompt is prepended to the message.

    Args:
        cwd: Working directory for the Claude process. When set, Claude only
             sees files inside that folder, preventing it from picking up
             context from other VS Code projects.
    """
    global _first_claude_call
    prompt = f"{system}\n\n{human}"
    if agent_name:
        print(
            f"  ⏳ [{agent_name}] thinking... (claude, timeout={AGENT_TIMEOUT}s, Ctrl+C to skip)",
            flush=True,
        )
    cmd = [_CLAUDE_BIN, "-p", prompt, "--dangerously-skip-permissions"]
    if _first_claude_call:
        cmd.append("--no-session-persistence")
        _first_claude_call = False
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=AGENT_TIMEOUT,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        print(
            f"\n  ⚠️  [{agent_name}] timed out after {AGENT_TIMEOUT}s — skipping", flush=True)
        return f"[TIMEOUT: {agent_name} did not respond in {AGENT_TIMEOUT}s]"
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI error:\n{result.stderr.strip()}")
    return result.stdout.strip()


def _gh_token() -> str:
    result = subprocess.run(["gh", "auth", "token"],
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _call_copilot(
    system: str,
    human: str,
    agent_name: str = "",
    model: str = _COPILOT_FAST_MODEL,
    cwd: str | None = None,
) -> str:
    """Call GitHub Copilot API (OpenAI-compatible).

    Args:
        cwd: Unused by the HTTP call, accepted for interface parity with ``call()``.
    """
    import openai

    if agent_name:
        print(f"  ⏳ [{agent_name}] thinking... (copilot/{model})", flush=True)
    try:
        client = openai.OpenAI(api_key=_gh_token(),
                               base_url="https://api.githubcopilot.com")
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": human},
            ],
            timeout=AGENT_TIMEOUT,
        )
        return resp.choices[0].message.content or ""
    except openai.APITimeoutError:
        print(f"\n  ⚠️  [{agent_name}] timed out — skipping", flush=True)
        return f"[TIMEOUT: {agent_name} did not respond in {AGENT_TIMEOUT}s]"


def get_available_copilot_models() -> list[str]:
    """Return model IDs available via the GitHub Copilot API."""
    import openai

    client = openai.OpenAI(api_key=_gh_token(),
                           base_url="https://api.githubcopilot.com")
    return [m.id for m in client.models.list().data]
