"""Reviewer agent: code review with APPROVED/REWORK decision.

Does NOT create files — outputs review decision and comments stored in state only.
"""

from llm.copilot import _COPILOT_SMART_MODEL, call_copilot
from utils import _save_to_md, human_checkpoint, parse_json_response
from config import MAX_REVIEW_ITERATIONS
from database import diff_and_log
from state import TeamState


def reviewer(state: TeamState) -> dict:
    old = dict(state)
    iteration = state.get("review_iteration", 0)

    review_raw = call_copilot(
        system=(
            "You are a strict Senior Code Reviewer. "
            "Check the code for: correctness, security (OWASP), code style, performance, "
            "adherence to the architecture. "
            "Respond ONLY with valid JSON — no markdown, no extra text. "
            'Schema: {"decision": "approved" | "rework", "comments": "<your feedback>"} '
            "Respond in the same language as the user. "
            "Do NOT create, modify, or delete any files."
        ),
        human=(
            f"Architecture:\n{state.get('architecture', '')}\n\nCode:\n{state.get('code', '')}"),
        agent_name="Reviewer",
        model=_COPILOT_SMART_MODEL,
        cwd=state.get("project_dir"),
    )

    parsed = parse_json_response(review_raw)
    if parsed and "decision" in parsed:
        result = parsed["decision"].lower().strip()
        result = "approved" if result == "approved" else "rework"
        comments = str(parsed.get("comments", ""))
    else:
        # Fallback: legacy text parsing
        first_line = review_raw.splitlines()[0].strip().upper()
        result = "approved" if "APPROVED" in first_line else "rework"
        comments = "\n".join(review_raw.splitlines()[1:]).strip()

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
        input_content=(
            f"Architecture:\n{state.get('architecture', '')}\n\n"
            f"Code:\n{state.get('code', '')}"
        ),
    )
    return update
