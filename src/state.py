"""
Shared state that flows through the LangGraph graph.
Every agent receives the full state and returns a partial update.
"""

from typing_extensions import TypedDict


class TeamState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────────────────
    task_id: int  # SQLite task id
    user_request: str  # original user task
    # target project folder (selected at startup)
    project_dir: str

    # ── Product Manager ────────────────────────────────────────────────────
    product_brief: str  # PRD produced by product manager

    # ── Architect ──────────────────────────────────────────────────────────
    architecture: str  # system design doc

    # ── Developer ──────────────────────────────────────────────────────────
    code: str  # implemented code
    developer_notes: str  # dev comments / explanations

    # ── Reviewer ───────────────────────────────────────────────────────────
    review_result: str  # "approved" | "rework"
    review_comments: str  # reviewer feedback
    review_iteration: int  # current iteration counter (0-based)

    # ── QA Test Design ─────────────────────────────────────────────────────
    test_cases: str  # test cases / unit tests

    # ── QA Validation ──────────────────────────────────────────────────────
    qa_validation_result: str    # "pass" | "fail"
    qa_validation_comments: str  # QA validation feedback

    # ── CI Validator ───────────────────────────────────────────────────────
    ci_result: str      # "pass" | "fail"
    ci_fail_type: str   # "tests" | "lint_build" | ""
    ci_comments: str    # CI pipeline feedback

    # ── DevOps ─────────────────────────────────────────────────────────────
    devops_config: str  # Dockerfile, CI/CD config

    # ── Jira ───────────────────────────────────────────────────────────────
    jira_project_key: str  # created/reused Jira project key
    jira_result: str  # summary of created tickets

    # ── Final ──────────────────────────────────────────────────────────────
    final_summary: str  # TeamLead's final answer to user
