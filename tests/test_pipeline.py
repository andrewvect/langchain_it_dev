"""
End-to-end pipeline tests — all LLM calls replaced with hard-coded "ping-pong"
responses so the graph runs fully without any real model / CLI calls.

Happy path:
  product_manager -> teamlead -> architect -> qa_test_design -> developer
  -> reviewer(APPROVED) -> qa_validation(PASS) -> ci_validator(PASS)
  -> jira(skip) -> devops -> teamlead_summarize

Rework loop:
  … -> reviewer(REWORK) -> developer(round 2) -> reviewer(APPROVED) -> …
"""

import sqlite3
from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

import database
from database import create_task, init_db
from graph import build_graph, route_after_ci, route_after_qa_validation, route_after_review
from state import TeamState

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """Point every database call at a fresh in-memory SQLite file."""
    db_file = str(tmp_path / "test_pipeline.db")
    monkeypatch.setattr(database, "DB_PATH", db_file)
    with patch("database.DB_PATH", db_file):
        init_db()
        yield db_file


@pytest.fixture()
def mem_graph(tmp_db):
    """Build the graph with an in-memory checkpointer (no real SQLite saver)."""
    with patch("graph.team_checkpointer", MemorySaver()):
        g = build_graph()
    return g


@pytest.fixture()
def base_state(tmp_path, tmp_db) -> TeamState:
    task_id = create_task("Build a REST API")
    return TeamState(
        task_id=task_id,
        user_request="Build a REST API",
        review_iteration=0,
        project_dir=str(tmp_path),
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _auto_approve(*args, **kwargs):
    """human_checkpoint stub: always approve (return content as-is)."""
    # signature: (agent_name, field, content, extra_hint="")
    return args[2]


# ── Happy-path test ───────────────────────────────────────────────────────────


def test_full_pipeline_happy_path(mem_graph, base_state):
    """
    Ping-pong: every agent receives a hand-crafted canned response.
    The whole graph must reach END with all expected fields populated.
    """
    config = {"configurable": {"thread_id": "test-happy-1"}}

    with (
        patch("agents.product_manager.call", return_value="Product PRD"),
        # TeamLead uses `call` for both decompose and summarize
        patch("agents.teamlead.call", side_effect=[
            "REST API task brief",    # teamlead_decompose
            "Final project summary",  # teamlead_summarize
        ]),
        # Architect also uses `call`
        patch("agents.architect.call",
              return_value="FastAPI + PostgreSQL architecture"),
        # QA, Developer, Reviewer, QA Validation, CI, DevOps use `_call_copilot`
        patch("agents.qa._call_copilot",
              return_value="def test_health(): assert True"),
        patch(
            "agents.developer._call_copilot",
            side_effect=[
                "def app(): pass  # implementation",  # code
                "Implemented a simple REST API",       # developer notes
            ],
        ),
        patch("agents.reviewer._call_copilot",
              return_value="APPROVED\nLooks great"),
        patch("agents.qa_validation._call_copilot",
              return_value="PASS\nAll tests pass"),
        patch("agents.ci_validator._call_copilot",
              return_value="PASS\nAll checks green"),
        patch("agents.devops._call_copilot",
              return_value="FROM python:3.12\nCMD uvicorn app:app"),
        # Jira: no api_token → skips automatically (patch get_jira_config)
        patch("agents.jira.get_jira_config", return_value={
              "api_token": "", "email": "", "base_url": ""}),
        # Human checkpoints: auto-approve everywhere
        patch("agents.product_manager.human_checkpoint",
              side_effect=_auto_approve),
        patch("agents.teamlead.human_checkpoint", side_effect=_auto_approve),
        patch("agents.architect.human_checkpoint", side_effect=_auto_approve),
        patch("agents.qa.human_checkpoint", side_effect=_auto_approve),
        patch("agents.developer.human_checkpoint", side_effect=_auto_approve),
        patch("agents.reviewer.human_checkpoint", side_effect=_auto_approve),
        patch("agents.qa_validation.human_checkpoint",
              side_effect=_auto_approve),
        patch("agents.ci_validator.human_checkpoint", side_effect=_auto_approve),
        patch("agents.devops.human_checkpoint", side_effect=_auto_approve),
    ):
        final = mem_graph.invoke(base_state, config=config)

    assert final["user_request"] == "REST API task brief"
    assert "FastAPI" in final["architecture"]
    assert "test_health" in final["test_cases"]
    assert "app" in final["code"]
    assert final["developer_notes"] == "Implemented a simple REST API"
    assert final["review_result"] == "approved"
    assert final["qa_validation_result"] == "pass"
    assert final["ci_result"] == "pass"
    assert "python" in final["devops_config"].lower()
    assert final["jira_result"] == "skipped (no Jira credentials)"


# ── Rework loop test ──────────────────────────────────────────────────────────


def test_pipeline_rework_then_approved(mem_graph, base_state):
    """
    Reviewer first returns REWORK, developer is called again, then APPROVED.
    Verifies the conditional edge loops correctly back to developer.
    """
    config = {"configurable": {"thread_id": "test-rework-1"}}

    with (
        patch("agents.product_manager.call", return_value="Product PRD"),
        patch("agents.teamlead.call", side_effect=[
            "REST API task brief",          # teamlead_decompose
            "Final summary after rework",   # teamlead_summarize
        ]),
        patch("agents.architect.call", return_value="FastAPI architecture"),
        patch("agents.qa._call_copilot", return_value="def test_api(): pass"),
        patch(
            "agents.developer._call_copilot",
            side_effect=[
                "def app_v1(): pass",        # code — round 1
                "First implementation",       # notes — round 1
                "def app_v2(): pass",         # code — round 2 (after rework)
                "Fixed implementation",       # notes — round 2
            ],
        ),
        patch(
            "agents.reviewer._call_copilot",
            side_effect=[
                "REWORK\nAdd error handling",  # round 1
                "APPROVED\nGood now",           # round 2
            ],
        ),
        patch("agents.qa_validation._call_copilot",
              return_value="PASS\nAll tests pass"),
        patch("agents.ci_validator._call_copilot",
              return_value="PASS\nAll checks green"),
        patch("agents.devops._call_copilot", return_value="FROM python:3.12"),
        patch("agents.jira.get_jira_config", return_value={
              "api_token": "", "email": "", "base_url": ""}),
        patch("agents.product_manager.human_checkpoint",
              side_effect=_auto_approve),
        patch("agents.teamlead.human_checkpoint", side_effect=_auto_approve),
        patch("agents.architect.human_checkpoint", side_effect=_auto_approve),
        patch("agents.qa.human_checkpoint", side_effect=_auto_approve),
        patch("agents.developer.human_checkpoint", side_effect=_auto_approve),
        patch("agents.reviewer.human_checkpoint", side_effect=_auto_approve),
        patch("agents.qa_validation.human_checkpoint",
              side_effect=_auto_approve),
        patch("agents.ci_validator.human_checkpoint", side_effect=_auto_approve),
        patch("agents.devops.human_checkpoint", side_effect=_auto_approve),
    ):
        final = mem_graph.invoke(base_state, config=config)

    assert final["review_result"] == "approved"
    assert "v2" in final["code"]            # developer produced v2 code
    assert "Fixed" in final["developer_notes"]


# ── route_after_review unit tests ─────────────────────────────────────────────


def test_route_after_review_sends_to_developer_on_rework():
    state = TeamState(review_result="rework", review_iteration=1)
    with patch("graph.MAX_REVIEW_ITERATIONS", 5):
        assert route_after_review(state) == "developer"


def test_route_after_review_sends_to_qa_validation_when_approved():
    state = TeamState(review_result="approved", review_iteration=1)
    assert route_after_review(state) == "qa_validation"


def test_route_after_review_sends_to_qa_validation_at_max_iterations():
    state = TeamState(review_result="rework", review_iteration=5)
    with patch("graph.MAX_REVIEW_ITERATIONS", 5):
        assert route_after_review(state) == "qa_validation"


# ── route_after_qa_validation unit tests ──────────────────────────────────────


def test_route_after_qa_validation_sends_to_developer_on_fail():
    state = TeamState(qa_validation_result="fail", review_iteration=1)
    with patch("graph.MAX_REVIEW_ITERATIONS", 5):
        assert route_after_qa_validation(state) == "developer"


def test_route_after_qa_validation_sends_to_ci_on_pass():
    state = TeamState(qa_validation_result="pass", review_iteration=1)
    assert route_after_qa_validation(state) == "ci_validator"


# ── route_after_ci unit tests ─────────────────────────────────────────────────


def test_route_after_ci_sends_to_developer_on_fail():
    state = TeamState(ci_result="fail", review_iteration=1)
    with patch("graph.MAX_REVIEW_ITERATIONS", 5):
        assert route_after_ci(state) == "developer"


def test_route_after_ci_sends_to_jira_on_pass():
    state = TeamState(ci_result="pass", review_iteration=1)
    assert route_after_ci(state) == "jira_setup"
