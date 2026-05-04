"""
SQLite storage: logs every context change (who spoke, what changed, iteration).
"""

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at  TEXT NOT NULL,
            user_input  TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'in_progress'
        );

        CREATE TABLE IF NOT EXISTS context_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id      INTEGER NOT NULL REFERENCES tasks(id),
            timestamp    TEXT NOT NULL,
            agent        TEXT NOT NULL,          -- who made the change
            iteration    INTEGER NOT NULL,        -- review iteration #
            field        TEXT NOT NULL,           -- which field changed
            old_value    TEXT,
            new_value    TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );
        """)


def create_task(user_input: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (created_at, user_input, status) VALUES (?, ?, 'in_progress')",
            (datetime.now(UTC).isoformat(), user_input),
        )
        return cur.lastrowid or 0


def log_context_change(
    task_id: int,
    agent: str,
    iteration: int,
    field: str,
    old_value: Any,
    new_value: Any,
) -> None:
    """Record a single field change in the context."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO context_log
               (task_id, timestamp, agent, iteration, field, old_value, new_value)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                datetime.now(UTC).isoformat(),
                agent,
                iteration,
                field,
                json.dumps(old_value, ensure_ascii=False) if old_value is not None else None,
                json.dumps(new_value, ensure_ascii=False) if new_value is not None else None,
            ),
        )


def diff_and_log(
    task_id: int, agent: str, iteration: int, old_state: dict[str, Any], new_state: dict[str, Any]
) -> None:
    """Compare two state snapshots and log every changed field."""
    all_keys = set(old_state) | set(new_state)
    for key in all_keys:
        old_val = old_state.get(key)
        new_val = new_state.get(key)
        if old_val != new_val:
            log_context_change(task_id, agent, iteration, key, old_val, new_val)


def finish_task(task_id: int, status: str = "done") -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id),
        )


def get_task_history(task_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM context_log WHERE task_id = ? ORDER BY id",
            (task_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def cancel_all_incomplete() -> None:
    """Mark all in_progress tasks as cancelled (used when --new is passed)."""
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET status = 'cancelled' WHERE status = 'in_progress'")


def get_last_incomplete_task() -> dict | None:
    """Return the most recent resumable task (in_progress, failed, or interrupted)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE status IN ('in_progress', 'failed', 'interrupted') "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def restore_state_from_log(task_id: int) -> dict:
    """
    Replay context_log to reconstruct the last known TeamState for a task.
    The latest value per field wins.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT field, new_value FROM context_log WHERE task_id = ? ORDER BY id",
            (task_id,),
        ).fetchall()

    state: dict = {"task_id": task_id}
    for row in rows:
        field = row["field"]
        raw = row["new_value"]
        try:
            state[field] = json.loads(raw) if raw is not None else None
        except (json.JSONDecodeError, TypeError):
            state[field] = raw
    return state
