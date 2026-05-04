"""Human checkpoint and file-save helpers."""

import os
import re
import sys
import textwrap
from datetime import datetime

from config import HUMAN_IN_THE_LOOP

_DIVIDER = "─" * 60
_MD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "outputs")


def _save_to_md(
    task_id: int, agent_name: str, field: str, content: str, project_dir: str | None = None
) -> None:
    """Append agent output to <project_dir>/task_<task_id>.md (or outputs/ fallback)."""
    out_dir = project_dir if project_dir else _MD_DIR
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"task_{task_id}.md")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n\n## [{timestamp}] {agent_name} → {field}\n\n")
        f.write(content)
        f.write("\n")


def _save_code_to_project(task_id: int, code: str, project_dir: str | None = None) -> str:
    """Save generated code into the project folder. Returns the folder path."""
    if project_dir:
        target_dir = project_dir
    else:
        target_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "generated", f"task_{task_id}"
        )
    os.makedirs(target_dir, exist_ok=True)

    # Try to extract individual files from fenced code blocks (```filename\n...\n```)
    pattern = re.compile(r"```(?:\w+\s+)?([^\s`]+\.\w+)\n(.*?)```", re.DOTALL)
    matches = pattern.findall(code)

    if matches:
        for filename, file_content in matches:
            safe_name = os.path.basename(filename)
            file_path = os.path.join(target_dir, safe_name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_content.strip())
    else:
        with open(os.path.join(target_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write(code)

    print(f"  💾 Code saved to: {target_dir}", flush=True)
    return target_dir


def human_checkpoint(agent_name: str, field: str, content: str, extra_hint: str = "") -> str:
    """
    Show agent output to the human, ask for approval or corrections.
    Returns the (possibly edited) content to use going forward.

    Responses:
      <Enter>  — approve as-is
      any text — treat as additional instructions, re-run agent with them appended
    """
    if not HUMAN_IN_THE_LOOP:
        return content

    print(f"\n{_DIVIDER}")
    print(f"  [{agent_name}] → {field}")
    print(_DIVIDER)
    for line in content.splitlines():
        print(textwrap.fill(line, width=100) if len(line) > 100 else line)
    print(_DIVIDER)
    if extra_hint:
        print(f"  Hint: {extra_hint}")
    sys.stdout.flush()
    sys.stderr.flush()
    feedback = input(
        f"  [Human] Press Enter to approve, or type corrections for {agent_name}: "
    ).strip()

    return feedback if feedback else content
