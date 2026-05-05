"""Architect agent: produces a technical design document.

Does NOT create files — outputs text (architecture doc) stored in state only.
"""

from llm.copilot import call_claude
from utils import _save_to_md, human_checkpoint
from database import diff_and_log
from state import TeamState


def architect(state: TeamState) -> dict:
    old = dict(state)
    system = (
        "You are a Senior Backend Software Architect. "
        "Design the system: choose stack, describe DB schema, API contract, "
        "service boundaries and key design patterns. "
        "Output a clear technical design document."
        "Respond in the same language as the user."
        "Create a design for developers. "
        "Do NOT create, modify, or delete any files."
    )

    project_dir = state.get("project_dir")
    design = call_claude(
        system=system, human=f"Task brief:\n{state['user_request']}",
        agent_name="Architect", cwd=project_dir,
    )

    feedback = human_checkpoint("Architect", "architecture", design)
    if feedback != design:
        design = call_claude(
            system=system,
            human=(
                f"Task brief:\n{state['user_request']}\n\n"
                f"Previous design was rejected. Human corrections:\n{feedback}"
            ),
            agent_name="Architect",
            cwd=project_dir,
        )

    update = {"architecture": design}
    diff_and_log(
        state["task_id"], "Architect", state.get(
            "review_iteration", 0), old, {**old, **update}
    )
    _save_to_md(
        state["task_id"], "Architect", "architecture", design,
        state.get("project_dir"),
        input_content=f"Task brief:\n{state['user_request']}",
    )
    return update
