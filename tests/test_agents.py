"""Integration-style tests for agent node functions (all LLM calls mocked)."""

from unittest.mock import patch

import pytest

import database
from database import create_task, init_db
from state import TeamState


@pytest.fixture(autouse=True)
def in_memory_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(database, "DB_PATH", db_file)
    # Patch the string imported in database module itself
    with patch("database.DB_PATH", db_file):
        init_db()
        yield db_file


def _base_state(tmp_path) -> TeamState:
    task_id = create_task("Build REST API")
    return TeamState(
        task_id=task_id,
        user_request="Build REST API",
        review_iteration=0,
        project_dir=str(tmp_path),
    )


# ─── teamlead_decompose ───────────────────────────────────────────────────────


def test_teamlead_decompose_returns_user_request(tmp_path):
    from agents.teamlead import teamlead_decompose

    state = _base_state(tmp_path)
    with patch("agents.teamlead._call", return_value="structured brief"):
        with patch("agents.teamlead.human_checkpoint", side_effect=lambda *a, **kw: a[2]):
            result = teamlead_decompose(state)

    assert result["user_request"] == "structured brief"
    assert result["review_iteration"] == 0


def test_teamlead_decompose_reruns_on_human_feedback(tmp_path):
    from agents.teamlead import teamlead_decompose

    state = _base_state(tmp_path)
    call_returns = iter(["first brief", "revised brief"])
    with patch("agents.teamlead._call", side_effect=call_returns):
        with patch("agents.teamlead.human_checkpoint", return_value="please revise"):
            result = teamlead_decompose(state)

    assert result["user_request"] == "revised brief"


# ─── architect ────────────────────────────────────────────────────────────────


def test_architect_returns_architecture(tmp_path):
    from agents.architect import architect

    state = _base_state(tmp_path)
    with patch("agents.architect._call", return_value="design doc"):
        with patch("agents.architect.human_checkpoint", side_effect=lambda *a, **kw: a[2]):
            result = architect(state)

    assert result["architecture"] == "design doc"


# ─── qa_engineer ──────────────────────────────────────────────────────────────


def test_qa_engineer_returns_test_cases(tmp_path):
    from agents.qa import qa_engineer

    state = _base_state(tmp_path)
    state["architecture"] = "REST API design"
    with patch("agents.qa._call_copilot", return_value="def test_login(): ..."):
        with patch("agents.qa.human_checkpoint", side_effect=lambda *a, **kw: a[2]):
            result = qa_engineer(state)

    assert "test_login" in result["test_cases"]


# ─── developer ────────────────────────────────────────────────────────────────


def test_developer_returns_code_and_notes(tmp_path):
    from agents.developer import developer

    state = _base_state(tmp_path)
    state["architecture"] = "design"
    state["test_cases"] = "def test_x(): ..."

    with patch("agents.developer._call_copilot", side_effect=["def app(): ...", "notes"]):
        with patch("agents.developer.human_checkpoint", side_effect=lambda *a, **kw: a[2]):
            result = developer(state)

    assert "app" in result["code"]
    assert result["developer_notes"] == "notes"


# ─── reviewer ─────────────────────────────────────────────────────────────────


def test_reviewer_approved(tmp_path):
    from agents.reviewer import reviewer

    state = _base_state(tmp_path)
    state["code"] = "clean code"
    state["architecture"] = "design"
    state["review_iteration"] = 0

    with patch("agents.reviewer._call_copilot", return_value="APPROVED\nLooks good"):
        with patch("agents.reviewer.human_checkpoint", side_effect=lambda *a, **kw: a[2]):
            result = reviewer(state)

    assert result["review_result"] == "approved"
    assert result["review_iteration"] == 1


def test_reviewer_rework(tmp_path):
    from agents.reviewer import reviewer

    state = _base_state(tmp_path)
    state["code"] = "messy code"
    state["architecture"] = "design"
    state["review_iteration"] = 0

    with patch("agents.reviewer._call_copilot", return_value="REWORK\nFix the imports"):
        with patch("agents.reviewer.human_checkpoint", side_effect=lambda *a, **kw: a[2]):
            result = reviewer(state)

    assert result["review_result"] == "rework"
    assert "Fix the imports" in result["review_comments"]


def test_reviewer_auto_approves_at_max_iterations(tmp_path):
    from agents.reviewer import reviewer

    state = _base_state(tmp_path)
    state["code"] = "code"
    state["architecture"] = "design"
    state["review_iteration"] = 4  # MAX_REVIEW_ITERATIONS - 1

    with patch("agents.reviewer.MAX_REVIEW_ITERATIONS", 5):
        with patch("agents.reviewer._call_copilot", return_value="REWORK\nstill bad"):
            with patch("agents.reviewer.human_checkpoint", side_effect=lambda *a, **kw: a[2]):
                result = reviewer(state)

    assert result["review_result"] == "approved"
    assert "Auto-approved" in result["review_comments"]


# ─── devops ───────────────────────────────────────────────────────────────────


def test_devops_returns_config(tmp_path):
    from agents.devops import devops

    state = _base_state(tmp_path)
    state["architecture"] = "design"
    state["developer_notes"] = "notes"

    with patch("agents.devops._call_copilot", return_value="FROM python:3.12"):
        with patch("agents.devops.human_checkpoint", side_effect=lambda *a, **kw: a[2]):
            result = devops(state)

    assert "python" in result["devops_config"].lower()


# ─── teamlead_summarize ───────────────────────────────────────────────────────


def test_teamlead_summarize_returns_summary(tmp_path):
    from agents.teamlead import teamlead_summarize

    state = _base_state(tmp_path)
    state["architecture"] = "design"
    state["code"] = "code"
    state["test_cases"] = "tests"
    state["devops_config"] = "docker"

    with patch("agents.teamlead._call_copilot", return_value="Final report"):
        result = teamlead_summarize(state)

    assert result["final_summary"] == "Final report"
