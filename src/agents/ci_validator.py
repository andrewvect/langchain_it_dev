"""CI Validator agent: simulates CI pipeline — lint, build, and test run.

Does NOT create files — outputs pass/fail result and comments stored in state only.
"""

from llm.copilot import _COPILOT_SMART_MODEL, call_copilot
from utils import _save_to_md, human_checkpoint, parse_json_response
from config import MAX_REVIEW_ITERATIONS
from database import diff_and_log
from state import TeamState


def ci_validator(state: TeamState) -> dict:
    old = dict(state)
    iteration = state.get("review_iteration", 0)

    result_raw = call_copilot(
        system=(
            "You are a CI/CD pipeline validator. "
            "Simulate running the full CI pipeline on the provided code: "
            "1. Linting (code style, static analysis) "
            "2. Build (compilation or import checks) "
            "3. Test suite execution "
            "Respond ONLY with valid JSON — no markdown, no extra text. "
            'Schema: {"result": "pass" | "fail", "fail_type": "" | "lint_build" | "tests", "comments": "<notes or list of issues>"} '
            'Use fail_type="" when result is "pass". '
            "Respond in the same language as the user. "
            "Do NOT create, modify, or delete any files."
        ),
        human=(
            f"Architecture:\n{state.get('architecture', '')}\n\n"
            f"Test cases:\n{state.get('test_cases', '')}\n\n"
            f"Code:\n{state.get('code', '')}\n\n"
            f"DevOps config:\n{state.get('devops_config', '')}"
        ),
        agent_name="CI Validator",
        model=_COPILOT_SMART_MODEL,
        cwd=state.get("project_dir"),
    )

    parsed = parse_json_response(result_raw)
    if parsed and "result" in parsed:
        result = parsed["result"].lower().strip()
        result = "pass" if result == "pass" else "fail"
        fail_type = str(parsed.get("fail_type", "")).lower().strip()
        if fail_type not in ("lint_build", "tests"):
            fail_type = "" if result == "pass" else "tests"
        comments = str(parsed.get("comments", ""))
    else:
        # Fallback: legacy text parsing
        first_line = result_raw.splitlines()[0].strip().upper()
        if "PASS" in first_line and "FAIL" not in first_line:
            result = "pass"
            fail_type = ""
        elif "FAIL_LINT_BUILD" in first_line:
            result = "fail"
            fail_type = "lint_build"
        else:
            result = "fail"
            fail_type = "tests"
        comments = "\n".join(result_raw.splitlines()[1:]).strip()

    if result == "fail" and iteration >= MAX_REVIEW_ITERATIONS - 1:
        result = "pass"
        fail_type = ""
        comments += f"\n\n[Auto-passed CI after {MAX_REVIEW_ITERATIONS} iterations]"

    feedback = human_checkpoint(
        "CI Validator",
        f"ci_validation ({result.upper()})",
        comments,
        extra_hint="Enter to keep decision, or type 'pass'/'fail: <reason>' to override.",
    )
    if feedback != comments:
        if feedback.strip().lower().startswith("pass"):
            result = "pass"
            fail_type = ""
            comments = feedback
        elif feedback.strip().lower().startswith("fail"):
            result = "fail"
            fail_type = "tests"
            comments = feedback
        else:
            comments = feedback

    update = {
        "ci_result": result,
        "ci_fail_type": fail_type,
        "ci_comments": comments,
        "review_iteration": iteration + 1,
    }
    diff_and_log(state["task_id"], "CI Validator",
                 iteration, old, {**old, **update})
    _save_to_md(
        state["task_id"],
        "CI Validator",
        f"ci_validation_{iteration + 1} ({result.upper()})",
        comments,
        state.get("project_dir"),
        input_content=(
            f"Architecture:\n{state.get('architecture', '')}\n\n"
            f"Test cases:\n{state.get('test_cases', '')}\n\n"
            f"Code:\n{state.get('code', '')}\n\n"
            f"DevOps config:\n{state.get('devops_config', '')}"
        ),
    )
    return update
