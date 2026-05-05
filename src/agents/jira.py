"""Jira integration: create project, epics, and story tickets.

Does NOT create local files — creates tickets via Jira REST API only.
"""

import json
import re
from typing import Any

import requests

from llm.copilot import _COPILOT_FAST_MODEL, call_copilot
from utils import _save_to_md
from config import get_jira_config
from database import diff_and_log
from state import TeamState


def _jira_request(method: str, url: str, cfg: dict[str, str], **kwargs: Any) -> requests.Response:
    """Authenticated Jira REST API request."""
    resp = requests.request(
        method,
        url,
        auth=(cfg["email"], cfg["api_token"]),
        headers={"Accept": "application/json",
                 "Content-Type": "application/json"},
        timeout=30,
        **kwargs,
    )
    resp.raise_for_status()
    return resp


def _get_or_create_project(cfg: dict, project_key: str, project_name: str) -> str:
    """Return project key, creating the project if it doesn't exist."""
    base = cfg["base_url"]
    try:
        _jira_request("GET", f"{base}/rest/api/3/project/{project_key}", cfg)
        print(f"  ✅ [Jira] Project {project_key} already exists", flush=True)
        return project_key
    except requests.HTTPError as e:
        if e.response.status_code != 404:
            raise

    me = _jira_request("GET", f"{base}/rest/api/3/myself", cfg).json()
    account_id = me["accountId"]

    payload = {
        "key": project_key,
        "name": project_name,
        "projectTypeKey": "software",
        "projectTemplateKey": "com.pyxis.greenhopper.jira:gh-scrum-template",
        "leadAccountId": account_id,
    }
    resp = _jira_request(
        "POST", f"{base}/rest/api/3/project", cfg, json=payload).json()
    key: str = resp.get("key", project_key)
    print(f"  ✅ [Jira] Created project: {key}", flush=True)
    return key


def _create_issue(
    cfg: dict,
    project_key: str,
    summary: str,
    issue_type: str,
    description: str = "",
    parent_key: str = "",
) -> str:
    """Create a Jira issue and return its key."""
    base = cfg["base_url"]
    fields: dict = {
        "project": {"key": project_key},
        "summary": summary[:255],
        "issuetype": {"name": issue_type},
    }
    if description:
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [
                    {"type": "text", "text": description[:10000]}]}
            ],
        }
    if parent_key:
        fields["parent"] = {"key": parent_key}

    resp = _jira_request(
        "POST", f"{base}/rest/api/3/issue", cfg, json={"fields": fields}).json()
    key: str = resp.get("key", "")
    print(f"    ✅ [Jira] {issue_type}: {key} — {summary[:60]}", flush=True)
    return key


def jira_setup(state: TeamState) -> dict:
    """
    Runs once after the first reviewer APPROVAL.
    1. Uses LLM to decompose architecture into structured epics + tasks.
    2. Creates (or reuses) a Jira project.
    3. Creates Epic tickets and Story/Task sub-tickets.
    """
    old = dict(state)
    cfg = get_jira_config()

    if not cfg["api_token"]:
        print("  ⚠️  [Jira] No API token configured — skipping", flush=True)
        return {"jira_result": "skipped (no Jira credentials)", "jira_project_key": ""}

    # ── Step 1: LLM decomposes the work into structured tickets ────────────
    tickets_raw = call_copilot(
        system=(
            "You are a Senior Engineering TeamLead. "
            "Based on the architecture document, produce a JSON list of Jira tickets. "
            "Output ONLY valid JSON — no markdown, no extra text. "
            'Schema: [{"epic": "Epic title", "tasks": [{"title": "Task title", "description": "..."}]}]. '
            "Create 2-5 epics, each with 2-6 tasks. Respond in English."
        ),
        human=(
            f"Project: {state.get('user_request', '')[:500]}\n\n"
            f"Architecture:\n{state.get('architecture', '')[:3000]}"
        ),
        agent_name="Jira decomposer",
        model=_COPILOT_FAST_MODEL,
        cwd=state.get("project_dir"),
    )

    tickets_raw = re.sub(r"^```(?:json)?\s*", "", tickets_raw.strip())
    tickets_raw = re.sub(r"\s*```$", "", tickets_raw.strip())

    try:
        epics_data = json.loads(tickets_raw)
    except json.JSONDecodeError:
        epics_data = [
            {
                "epic": "Implementation",
                "tasks": [
                    {
                        "title": "Backend implementation",
                        "description": state.get("architecture", "")[:500],
                    },
                    {"title": "Testing", "description": "Write and run tests"},
                    {"title": "Deployment", "description": "Set up CI/CD and deploy"},
                ],
            }
        ]
        print(
            "  ⚠️  [Jira] LLM returned invalid JSON — using fallback tickets", flush=True)

    # ── Step 2: Derive a short project key from the task ──────────────────
    raw_request = state.get("user_request", "TASK")
    words = re.findall(r"[A-Za-z]+", raw_request)
    project_key = ("".join(w[0].upper() for w in words[:5]) or "TASK")[:10]
    if len(project_key) < 2:
        project_key = "TASK"
    project_name = " ".join(words[:6]) or "AI Generated Project"

    # ── Step 3: Ensure project exists ─────────────────────────────────────
    try:
        project_key = _get_or_create_project(cfg, project_key, project_name)
    except Exception as e:
        msg = f"[Jira] Failed to create/find project: {e}"
        print(f"  ❌ {msg}", flush=True)
        return {"jira_result": msg, "jira_project_key": ""}

    # ── Step 4: Create Epics + Tasks ──────────────────────────────────────
    created_lines: list = [f"Project: {project_key}"]
    for epic_def in epics_data:
        epic_summary = str(epic_def.get("epic", "Epic"))
        try:
            epic_key = _create_issue(cfg, project_key, epic_summary, "Epic")
            created_lines.append(f"Epic {epic_key}: {epic_summary}")
        except Exception as e:
            print(f"  ❌ [Jira] Epic creation failed: {e}", flush=True)
            epic_key = ""

        for task_def in epic_def.get("tasks", []):
            task_title = str(task_def.get("title", "Task"))
            task_desc = str(task_def.get("description", ""))
            try:
                task_key = _create_issue(
                    cfg,
                    project_key,
                    task_title,
                    "Story",
                    description=task_desc,
                    parent_key=epic_key,
                )
                created_lines.append(f"  Story {task_key}: {task_title}")
            except Exception:
                try:
                    task_key = _create_issue(
                        cfg, project_key, task_title, "Task", description=task_desc
                    )
                    created_lines.append(f"  Task {task_key}: {task_title}")
                except Exception as e2:
                    print(f"  ❌ [Jira] Task creation failed: {e2}", flush=True)

    jira_result = "\n".join(created_lines)
    _save_to_md(
        state["task_id"], "Jira", "setup", jira_result,
        state.get("project_dir"),
        input_content=f"Project key: {project_key}",
    )
    diff_and_log(
        state["task_id"],
        "Jira",
        state.get("review_iteration", 0),
        old,
        {**old, "jira_project_key": project_key, "jira_result": jira_result},
    )
    print(
        f"\n  🎫 [Jira] Setup complete — {len(created_lines) - 1} items in {project_key}",
        flush=True,
    )
    return {"jira_project_key": project_key, "jira_result": jira_result}
