"""Developer agent: implements code following TDD."""

from llm.copilot import _COPILOT_CODE_MODEL, _COPILOT_FAST_MODEL, _call_copilot
from utils import _save_code_to_project, _save_to_md, human_checkpoint
from database import diff_and_log
from state import TeamState


def developer(state: TeamState) -> dict:
    old = dict(state)

    rework_hint = ""
    if state.get("review_comments") and state.get("review_result") == "rework":
        rework_hint = (
            f"\n\nPREVIOUS REVIEW FEEDBACK (fix these issues):\n{state['review_comments']}"
        )

    dev_system = (
        "You are a Senior Backend Developer practicing TDD. "
        "Implement clean, production-ready code that makes the provided tests pass. "
        "Follow the architecture strictly. Include docstrings and inline comments. "
        "Respond in the same language as the user."
    )
    code = _call_copilot(
        system=dev_system,
        human=(
            f"Architecture:\n{state.get('architecture', '')}\n\n"
            f"Tests to pass (TDD):\n{state.get('test_cases', '')}"
            f"{rework_hint}"
        ),
        agent_name="Developer",
        model=_COPILOT_CODE_MODEL,
    )

    feedback = human_checkpoint(
        "Developer",
        "code",
        code,
        extra_hint="Reviewer will check next. You can request specific fixes.",
    )
    if feedback != code:
        code = _call_copilot(
            system=dev_system,
            human=(
                f"Architecture:\n{state.get('architecture', '')}\n\n"
                f"Tests to pass (TDD):\n{state.get('test_cases', '')}"
                f"{rework_hint}\n\n"
                f"Previous code was rejected. Human corrections:\n{feedback}"
            ),
            agent_name="Developer",
            model=_COPILOT_CODE_MODEL,
        )

    notes = _call_copilot(
        system="You are a Senior Backend Developer. Summarize what you implemented and any important decisions.",
        human=f"Code you wrote:\n{code}",
        agent_name="Developer (notes)",
        model=_COPILOT_FAST_MODEL,
    )

    update = {"code": code, "developer_notes": notes}
    _save_code_to_project(state["task_id"], code, state.get("project_dir"))
    _save_to_md(state["task_id"], "Developer", "code", code, state.get("project_dir"))
    _save_to_md(state["task_id"], "Developer", "developer_notes", notes, state.get("project_dir"))
    diff_and_log(
        state["task_id"], "Developer", state.get("review_iteration", 0), old, {**old, **update}
    )
    return update
