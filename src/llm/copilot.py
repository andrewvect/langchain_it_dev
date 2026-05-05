"""LLM call helpers: Claude CLI and GitHub Copilot CLI."""

import shutil
import subprocess

from config import AGENT_TIMEOUT

_CLAUDE_BIN = shutil.which("claude") or "claude"
_COPILOT_BIN = (
    shutil.which("copilot")
    or "/Users/andrey/.nvm/versions/node/v20.20.2/bin/copilot"
)

# Models available via Copilot CLI
# Developer, Reviewer — best for code
_COPILOT_CODE_MODEL = "claude-sonnet-4.6"
# DevOps, QA, Jira, summaries — fast & cheap
_COPILOT_FAST_MODEL = "gpt-5.4-mini"
_COPILOT_SMART_MODEL = "gpt-5.4"            # Reviewer deep analysis


def call_claude(
    system: str,
    human: str,
    agent_name: str = "",
    cwd: str | None = None,
    allow_tools: bool = False,
) -> str:
    """Run a single Claude CLI call. System prompt is prepended to the message.

    Args:
        cwd: Working directory for the Claude process. When set, Claude only
             sees files inside that folder, preventing it from picking up
             context from other VS Code projects.
        allow_tools: When True, adds --dangerously-skip-permissions so Claude
                     can create/edit files (use only for Developer/Reviewer/CI).
                     Defaults to False to prevent premature file creation by
                     design-phase agents (ProductManager, TeamLead, Architect).
    """
    global _first_claude_call
    prompt = f"{system}\n\n{human}"
    if agent_name:
        print(
            f"  ⏳ [{agent_name}] thinking... (claude, timeout={AGENT_TIMEOUT}s, Ctrl+C to skip)",
            flush=True,
        )
    cmd = [_CLAUDE_BIN, "-p", prompt, "--no-session-persistence"]
    if allow_tools:
        cmd.append("--dangerously-skip-permissions")
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


def call_copilot(
    system: str,
    human: str,
    agent_name: str = "",
    model: str = _COPILOT_FAST_MODEL,
    cwd: str | None = None,
    allow_tools: bool = False,
) -> str:
    """Call GitHub Copilot via CLI (copilot -p --model ...).

    Args:
        model: Copilot model ID (e.g. claude-sonnet-4.6, gpt-5.4-mini).
        cwd: Working directory for the copilot process.
        allow_tools: When True, adds --allow-all-tools so Copilot can create/edit
                     files (use only for Developer). Defaults to False to prevent
                     premature file creation by design/review agents.
    """
    if agent_name:
        print(
            f"  ⏳ [{agent_name}] thinking... (copilot, timeout={AGENT_TIMEOUT}s, Ctrl+C to skip)", flush=True)
    prompt = f"{system}\n\n{human}"
    cmd = [_COPILOT_BIN, "-p", prompt, "--silent", "--model", model]
    if allow_tools:
        cmd.append("--allow-all-tools")
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
        raise RuntimeError(f"Copilot CLI error:\n{result.stderr.strip()}")
    return result.stdout.strip()
