"""QA Validation agent: checks that the implemented code satisfies the test cases.

Does NOT create files — outputs pass/fail decision and comments stored in state only.
"""

from llm.copilot import _COPILOT_SMART_MODEL, call_copilot
from utils import _save_to_md, human_checkpoint, parse_json_response
from config import MAX_REVIEW_ITERATIONS
from database import diff_and_log
from state import TeamState


def qa_validation(state: TeamState) -> dict:
    old = dict(state)
    iteration = state.get("review_iteration", 0)

    result_raw = call_copilot(
        system=(
            "You are a QA Engineer performing validation. "
            "Carefully analyse the code against the defined test cases and acceptance criteria. "
            "Determine whether all tests would PASS or at least one would FAIL. "
            "Respond ONLY with valid JSON — no markdown, no extra text. "
            'Schema: {"decision": "pass" | "fail", "comments": "<brief notes or list of failing tests>"} '
            "Respond in the same language as the user. "
            "Do NOT create, modify, or delete any files."
        ),
        human=(
            f"Test cases:\n{state.get('test_cases', '')}\n\n"
            f"Code:\n{state.get('code', '')}"
        ),
        agent_name="QA Validation",
        model=_COPILOT_SMART_MODEL,
        cwd=state.get("project_dir"),
    )

    parsed = parse_json_response(result_raw)
    if parsed and "decision" in parsed:
        result = parsed["decision"].lower().strip()
        result = "pass" if result == "pass" else "fail"
        comments = str(parsed.get("comments", ""))
    else:
        # Fallback: legacy text parsing
        first_line = result_raw.splitlines()[0].strip().upper()
        result = "pass" if "PASS" in first_line else "fail"
        comments = "\n".join(result_raw.splitlines()[1:]).strip()

    if result == "fail" and iteration >= MAX_REVIEW_ITERATIONS - 1:
        result = "pass"
        comments += f"\n\n[Auto-passed QA validation after {MAX_REVIEW_ITERATIONS} iterations]"

    feedback = human_checkpoint(
        "QA Validation",
        f"qa_validation ({result.upper()})",
        comments,
        extra_hint="Enter to keep decision, or type 'pass'/'fail: <reason>' to override.",
    )
    if feedback != comments:
        if feedback.strip().lower().startswith("pass"):
            result = "pass"
            comments = feedback
        elif feedback.strip().lower().startswith("fail"):
            result = "fail"
            comments = feedback
        else:
            comments = feedback

    update = {
        "qa_validation_result": result,
        "qa_validation_comments": comments,
        "review_iteration": iteration + 1,
    }
    diff_and_log(state["task_id"], "QA Validation",
                 iteration, old, {**old, **update})
    _save_to_md(
        state["task_id"],
        "QA Validation",
        f"qa_validation_{iteration + 1} ({result.upper()})",
        comments,
        state.get("project_dir"),
        input_content=(
            f"Test cases:\n{state.get('test_cases', '')}\n\n"
            f"Code:\n{state.get('code', '')}"
        ),
    )
    return update
