"""QA Test Design agent: writes tests before implementation (TDD).

Does NOT create files — outputs test code as text stored in state only.
Files are physically written to disk by the Developer agent (allow_tools=True).
"""

from llm.copilot import _COPILOT_FAST_MODEL, call_copilot
from utils import _save_to_md, human_checkpoint
from database import diff_and_log
from state import TeamState


def qa_test_design(state: TeamState) -> dict:
    old = dict(state)

    qa_system = (
        "You are a QA Engineer practicing TDD. "
        "Based on the architecture spec and product requirements, write comprehensive unit and integration tests "
        "BEFORE the implementation exists. Define the expected behavior, contracts, "
        "edge cases and error handling. Tests will guide the developer. "
        "Respond in the same language as the user. "
        "Do NOT create, modify, or delete any files — output test code as text only."
    )
    project_dir = state.get("project_dir")
    tests = call_copilot(
        system=qa_system,
        human=(
            f"Product requirements:\n{state.get('product_brief', '')}\n\n"
            f"Architecture:\n{state.get('architecture', '')}"
        ),
        agent_name="QA Test Design",
        model=_COPILOT_FAST_MODEL,
        cwd=project_dir,
    )

    feedback = human_checkpoint("QA Test Design", "test_cases", tests)
    if feedback != tests:
        tests = call_copilot(
            system=qa_system,
            human=(
                f"Product requirements:\n{state.get('product_brief', '')}\n\n"
                f"Architecture:\n{state.get('architecture', '')}\n\n"
                f"Previous tests were rejected. Human corrections:\n{feedback}"
            ),
            agent_name="QA Test Design",
            model=_COPILOT_FAST_MODEL,
            cwd=project_dir,
        )

    update = {"test_cases": tests}
    diff_and_log(state["task_id"], "QA Test Design", state.get(
        "review_iteration", 0), old, {**old, **update})
    _save_to_md(
        state["task_id"], "QA Test Design", "test_cases", tests,
        state.get("project_dir"),
        input_content=(
            f"Product requirements:\n{state.get('product_brief', '')}\n\n"
            f"Architecture:\n{state.get('architecture', '')}"
        ),
    )
    return update
