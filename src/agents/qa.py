"""QA Engineer agent: writes tests before implementation (TDD)."""

from llm.copilot import _COPILOT_FAST_MODEL, _call_copilot
from utils import _save_to_md, human_checkpoint
from database import diff_and_log
from state import TeamState


def qa_engineer(state: TeamState) -> dict:
    old = dict(state)

    qa_system = (
        "You are a QA Engineer practicing TDD. "
        "Based on the architecture spec, write comprehensive unit and integration tests "
        "BEFORE the implementation exists. Define the expected behavior, contracts, "
        "edge cases and error handling. Tests will guide the developer. "
        "Respond in the same language as the user."
    )
    project_dir = state.get("project_dir")
    tests = _call_copilot(
        system=qa_system,
        human=f"Architecture:\n{state.get('architecture', '')}",
        agent_name="QA",
        model=_COPILOT_FAST_MODEL,
        cwd=project_dir,
    )

    feedback = human_checkpoint("QA", "test_cases", tests)
    if feedback != tests:
        tests = _call_copilot(
            system=qa_system,
            human=(
                f"Architecture:\n{state.get('architecture', '')}\n\n"
                f"Previous tests were rejected. Human corrections:\n{feedback}"
            ),
            agent_name="QA",
            model=_COPILOT_FAST_MODEL,
            cwd=project_dir,
        )

    update = {"test_cases": tests}
    diff_and_log(state["task_id"], "QA", state.get(
        "review_iteration", 0), old, {**old, **update})
    _save_to_md(state["task_id"], "QA", "test_cases",
                tests, state.get("project_dir"))
    return update
