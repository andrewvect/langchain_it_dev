"""Tests for database.py — SQLite task and context-log helpers."""

import json
from unittest.mock import patch

import pytest

import database
from database import (
    cancel_all_incomplete,
    create_task,
    diff_and_log,
    finish_task,
    get_last_incomplete_task,
    get_task_history,
    init_db,
    log_context_change,
    restore_state_from_log,
)


@pytest.fixture(autouse=True)
def in_memory_db(tmp_path):
    """Redirect all DB operations to a fresh in-memory file per test."""
    db_file = str(tmp_path / "test.db")
    with patch.object(database, "DB_PATH", db_file):
        # Also patch the import inside database module
        with patch("database.DB_PATH", db_file):
            init_db()
            yield db_file


def test_create_task_returns_int():
    task_id = create_task("Build API")
    assert isinstance(task_id, int)
    assert task_id > 0


def test_create_task_stores_input():
    task_id = create_task("My task")
    conn = database.get_conn()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    assert row["user_input"] == "My task"
    assert row["status"] == "in_progress"


def test_finish_task_updates_status():
    task_id = create_task("task")
    finish_task(task_id, status="done")
    conn = database.get_conn()
    row = conn.execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
    assert row["status"] == "done"


def test_log_context_change_and_get_history():
    task_id = create_task("task")
    log_context_change(task_id, "Architect", 0, "architecture", None, "Service design doc")
    history = get_task_history(task_id)
    assert len(history) == 1
    assert history[0]["agent"] == "Architect"
    assert history[0]["field"] == "architecture"
    assert json.loads(history[0]["new_value"]) == "Service design doc"


def test_diff_and_log_records_only_changed_fields():
    task_id = create_task("task")
    old = {"task_id": task_id, "user_request": "old request", "architecture": "v1"}
    new = {**old, "architecture": "v2"}
    diff_and_log(task_id, "Architect", 0, old, new)
    history = get_task_history(task_id)
    fields = [h["field"] for h in history]
    assert "architecture" in fields
    assert "user_request" not in fields  # unchanged


def test_diff_and_log_ignores_identical_state():
    task_id = create_task("task")
    state = {"task_id": task_id, "code": "print('hi')"}
    diff_and_log(task_id, "Developer", 0, state, state)
    assert get_task_history(task_id) == []


def test_cancel_all_incomplete():
    t1 = create_task("t1")
    t2 = create_task("t2")
    finish_task(t1, "done")
    cancel_all_incomplete()
    conn = database.get_conn()
    row = conn.execute("SELECT status FROM tasks WHERE id = ?", (t2,)).fetchone()
    assert row["status"] == "cancelled"
    row_done = conn.execute("SELECT status FROM tasks WHERE id = ?", (t1,)).fetchone()
    assert row_done["status"] == "done"  # not touched


def test_get_last_incomplete_task_returns_none_when_empty():
    assert get_last_incomplete_task() is None


def test_get_last_incomplete_task_returns_most_recent():
    t1 = create_task("first")
    t2 = create_task("second")
    finish_task(t1, "done")
    result = get_last_incomplete_task()
    assert result is not None
    assert result["id"] == t2


def test_restore_state_from_log():
    task_id = create_task("task")
    log_context_change(task_id, "TeamLead", 0, "user_request", None, "brief v1")
    log_context_change(task_id, "TeamLead", 0, "user_request", "brief v1", "brief v2")
    log_context_change(task_id, "Architect", 0, "architecture", None, "design doc")

    state = restore_state_from_log(task_id)
    assert state["task_id"] == task_id
    assert state["user_request"] == "brief v2"  # latest value wins
    assert state["architecture"] == "design doc"
