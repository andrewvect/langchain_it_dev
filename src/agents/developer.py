"""Developer agent: implements code following TDD.

CREATES FILES — runs with allow_tools=True so it can write source code and
test files directly to disk in project_dir.
"""

from llm.copilot import _COPILOT_CODE_MODEL, _COPILOT_FAST_MODEL, call_copilot
from utils import _save_to_md, human_checkpoint
from database import diff_and_log
from state import TeamState


def developer(state: TeamState) -> dict:
    old = dict(state)

    rework_hint = ""
    if state.get("review_comments") and state.get("review_result") == "rework":
        rework_hint = (
            f"\n\nPREVIOUS REVIEW FEEDBACK (fix these issues):\n{state['review_comments']}"
        )
    if state.get("qa_validation_comments") and state.get("qa_validation_result") == "fail":
        rework_hint += (
            f"\n\nQA VALIDATION FAILURES (fix these):\n{state['qa_validation_comments']}"
        )
    if state.get("ci_comments") and state.get("ci_result") == "fail":
        rework_hint += (
            f"\n\nCI PIPELINE FAILURES (fix these):\n{state['ci_comments']}"
        )

    dev_system = (
        "You are a Senior Backend Developer practicing TDD. "
        "Implement clean, production-ready code that makes the provided tests pass. "
        "Follow the architecture strictly. Include docstrings and inline comments. "
        "Respond in the same language as the user. "
        "You MUST create and write all necessary source and test files to disk in the project directory."
    )
    project_dir = state.get("project_dir")
    code = call_copilot(
        system=dev_system,
        human=(
            f"Architecture:\n{state.get('architecture', '')}\n\n"
            f"Tests to pass (TDD):\n{state.get('test_cases', '')}"
            f"{rework_hint}"
        ),
        agent_name="Developer",
        model=_COPILOT_CODE_MODEL,
        cwd=project_dir,
        allow_tools=True,
    )

    feedback = human_checkpoint(
        "Developer",
        "code",
        code,
        extra_hint="Reviewer will check next. You can request specific fixes.",
    )
    if feedback != code:
        code = call_copilot(
            system=dev_system,
            human=(
                f"Architecture:\n{state.get('architecture', '')}\n\n"
                f"Tests to pass (TDD):\n{state.get('test_cases', '')}"
                f"{rework_hint}\n\n"
                f"Previous code was rejected. Human corrections:\n{feedback}"
            ),
            agent_name="Developer",
            model=_COPILOT_CODE_MODEL,
            cwd=project_dir,
            allow_tools=True,
        )

    notes = call_copilot(
        system="You are a Senior Backend Developer. Summarize what you implemented and any important decisions.",
        human=f"Code you wrote:\n{code}",
        agent_name="Developer (notes)",
        model=_COPILOT_FAST_MODEL,
        cwd=project_dir,
    )

    iteration = state.get("review_iteration", 0)
    update = {"code": code, "developer_notes": notes}
    _save_to_md(
        state["task_id"], "Developer", f"code (iteration {iteration + 1})", code,
        state.get("project_dir"),
        input_content=(
            f"Architecture:\n{state.get('architecture', '')}\n\n"
            f"Tests to pass (TDD):\n{state.get('test_cases', '')}"
            f"{rework_hint}"
        ),
    )
    _save_to_md(
        state["task_id"], "Developer", f"developer_notes (iteration {iteration + 1})", notes,
        state.get("project_dir"),
        input_content=f"Code:\n{code}",
    )
    diff_and_log(
        state["task_id"], "Developer", state.get(
            "review_iteration", 0), old, {**old, **update}
    )
    return update
