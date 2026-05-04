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

    # ── Architect ──────────────────────────────────────────────────────────
    architecture: str  # system design doc

    # ── Developer ──────────────────────────────────────────────────────────
    code: str  # implemented code
    developer_notes: str  # dev comments / explanations

    # ── Reviewer ───────────────────────────────────────────────────────────
    review_result: str  # "approved" | "rework"
    review_comments: str  # reviewer feedback
    review_iteration: int  # current iteration counter (0-based)

    # ── QA ─────────────────────────────────────────────────────────────────
    test_cases: str  # test cases / unit tests

    # ── DevOps ─────────────────────────────────────────────────────────────
    devops_config: str  # Dockerfile, CI/CD config

    # ── Jira ───────────────────────────────────────────────────────────────
    jira_project_key: str  # created/reused Jira project key
    jira_result: str  # summary of created tickets

    # ── Final ──────────────────────────────────────────────────────────────
    final_summary: str  # TeamLead's final answer to user
