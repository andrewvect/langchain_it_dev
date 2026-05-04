"""
Entry point.

Usage:
    python main.py "Create a REST API for user authentication with JWT"
    python main.py --new          # ignore incomplete run, ask for new prompt
    python main.py --new "task"   # same but with inline task
    python main.py --project-dir /path/to/project "task"

If there is an incomplete (in_progress / failed / interrupted) task in the DB,
the script will offer to resume it from the last completed step.
"""

import os
import sys
from typing import Any

from database import (
    cancel_all_incomplete,
    create_task,
    finish_task,
    get_last_incomplete_task,
    get_task_history,
    init_db,
    restore_state_from_log,
)
from graph import team_checkpointer, team_graph


def _ask_project_dir() -> str:
    """Interactively ask the user to enter or confirm a project folder."""
    print("\n📁 Project folder selection")
    print("   All generated code and logs will be saved there.")
    while True:
        raw = input(
            "   Enter project folder path (or press Enter for ./generated/new): ").strip()
        if not raw:
            path = os.path.join(os.path.dirname(__file__), "generated", "new")
        else:
            path = os.path.expanduser(raw)
        path = os.path.abspath(path)
        try:
            os.makedirs(path, exist_ok=True)
            print(f"   ✅ Using: {path}\n")
            return path
        except OSError as e:
            print(f"   ❌ Cannot create folder: {e}. Try again.")


def _print_history(task_id: int) -> None:
    print(f"\n{'─' * 60}")
    print("CONTEXT CHANGE LOG:")
    history = get_task_history(task_id)
    for entry in history:
        new_preview = (entry["new_value"] or "—")[:120].replace("\n", " ")
        print(
            f"  [{entry['timestamp']}] "
            f"iter={entry['iteration']} "
            f"{entry['agent']:12s} "
            f"field={entry['field']:20s} "
            f"→ {new_preview}..."
        )


def _last_completed_node(task_id: int) -> str | None:
    config = {"configurable": {"thread_id": str(task_id)}}
    chk = team_checkpointer.get(config)  # type: ignore[arg-type]
    if not chk:
        return None
    raw_meta: Any = (
        chk.get("metadata", {}) if isinstance(
            chk, dict) else getattr(chk, "metadata", {})
    )
    metadata: dict = raw_meta or {}
    writes = (metadata or {}).get("writes") or {}
    return next(iter(writes), None)


def run_team(
    user_request: str, resume_task_id: int | None = None, project_dir: str | None = None
) -> str:
    init_db()

    if resume_task_id:
        task_id = resume_task_id
        last_node = _last_completed_node(task_id)
        if last_node:
            print(
                f"\n[Task #{task_id}] Resuming after '{last_node}'...\n{'─' * 60}")
        else:
            print(
                f"\n[Task #{task_id}] No checkpoint — restarting from beginning...\n{'─' * 60}")
        finish_task(task_id, status="in_progress")
        initial_state = restore_state_from_log(task_id)
        initial_state.setdefault("review_iteration", 0)
        if project_dir:
            initial_state["project_dir"] = project_dir
        print("Restored state fields:", list(initial_state.keys()))
    else:
        task_id = create_task(user_request)
        initial_state = {
            "task_id": task_id,
            "user_request": user_request,
            "review_iteration": 0,
        }
        if project_dir:
            initial_state["project_dir"] = project_dir
        print(f"\n[Task #{task_id}] Starting IT team pipeline...\n{'─' * 60}")

    config = {"configurable": {"thread_id": str(task_id)}}

    try:
        final_state: dict = team_graph.invoke(
            initial_state, config=config)  # type: ignore[call-overload]
    except KeyboardInterrupt:
        finish_task(task_id, status="interrupted")
        print(
            f"\n[Task #{task_id}] Interrupted — run again to resume from last step.")
        return ""
    except Exception:
        finish_task(task_id, status="failed")
        last_node = _last_completed_node(task_id)
        print(
            f"\n[Task #{task_id}] Failed after '{last_node}' — run again to resume from that step."
        )
        raise

    finish_task(task_id, status="done")
    _print_history(task_id)

    print(f"\n{'═' * 60}")
    print("FINAL DELIVERABLE:\n")
    print(final_state.get("final_summary", "No summary generated."))
    print(f"{'═' * 60}\n")

    return str(final_state.get("final_summary", ""))


if __name__ == "__main__":
    args = sys.argv[1:]
    force_new = "--new" in args
    if force_new:
        args = [a for a in args if a != "--new"]

    # Parse --project-dir /path
    cli_project_dir: str | None = None
    if "--project-dir" in args:
        idx = args.index("--project-dir")
        if idx + 1 < len(args):
            cli_project_dir = os.path.abspath(
                os.path.expanduser(args[idx + 1]))
            args = args[:idx] + args[idx + 2:]
        else:
            print("Error: --project-dir requires a path argument.")
            sys.exit(1)

    init_db()

    if force_new:
        cancel_all_incomplete()

    resume_id = None
    if not force_new:
        incomplete = get_last_incomplete_task()
        if incomplete:
            last_node = _last_completed_node(incomplete["id"])
            resume_point = f"after '{last_node}'" if last_node else "from beginning"
            print(
                f"\n⚠️  Found resumable task #{incomplete['id']} [{incomplete['status']}]:")
            print(f"   Created : {incomplete['created_at']}")
            print(f"   Request : {incomplete['user_input'][:100]}")
            print(f"   Resume  : {resume_point}")
            choice = input("   Resume it? [Y/n]: ").strip().lower()
            if choice in ("", "y", "yes"):
                resume_id = incomplete["id"]

    # Resolve project folder (CLI flag overrides interactive prompt)
    project_dir = cli_project_dir or _ask_project_dir()

    if resume_id:
        run_team(user_request="", resume_task_id=resume_id,
                 project_dir=project_dir)
    else:
        request = " ".join(args) if args else input(
            "Enter your backend task: ").strip()
        if not request:
            print("No task provided.")
            sys.exit(1)
        run_team(request, project_dir=project_dir)
