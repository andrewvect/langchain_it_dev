"""Reviewer agent: code review with APPROVED/REWORK decision."""

from llm.copilot import _COPILOT_CODE_MODEL, _call_copilot
from utils import _save_to_md, human_checkpoint
from config import MAX_REVIEW_ITERATIONS
from database import diff_and_log
from state import TeamState


def reviewer(state: TeamState) -> dict:
    old = dict(state)
    iteration = state.get("review_iteration", 0)

    review = _call_copilot(
        system=(
            "You are a strict Senior Code Reviewer. "
            "Check the code for: correctness, security (OWASP), code style, performance, "
            "adherence to the architecture. "
            "If the code is acceptable respond with exactly: APPROVED\n<your comments>\n"
            "If it needs fixes respond with exactly: REWORK\n<list of required changes>\n"
            "Respond in the same language as the user."
        ),
        human=(
            f"Architecture:\n{state.get('architecture', '')}\n\nCode:\n{state.get('code', '')}"),
        agent_name="Reviewer",
        model=_COPILOT_CODE_MODEL,
        cwd=state.get("project_dir"),
    )

    first_line = review.splitlines()[0].strip().upper()
    result = "approved" if "APPROVED" in first_line else "rework"
    comments = "\n".join(review.splitlines()[1:]).strip()

    if result == "rework" and iteration >= MAX_REVIEW_ITERATIONS - 1:
        result = "approved"
        comments += f"\n\n[Auto-approved after {MAX_REVIEW_ITERATIONS} iterations]"

    feedback = human_checkpoint(
        "Reviewer",
        f"review ({result.upper()})",
        comments,
        extra_hint="Enter to keep decision, or type 'approve'/'rework: <reason>' to override.",
    )
    if feedback != comments:
        if feedback.strip().lower().startswith("approve"):
            result = "approved"
            comments = feedback
        elif feedback.strip().lower().startswith("rework"):
            result = "rework"
            comments = feedback
        else:
            comments = feedback

    update = {
        "review_result": result,
        "review_comments": comments,
        "review_iteration": iteration + 1,
    }
    diff_and_log(state["task_id"], "Reviewer",
                 iteration, old, {**old, **update})
    _save_to_md(
        state["task_id"],
        "Reviewer",
        f"review_{iteration + 1} ({result.upper()})",
        comments,
        state.get("project_dir"),
    )
    return update
