"""TeamLead agent: decompose user request and summarize final output."""

from llm.copilot import _COPILOT_FAST_MODEL, _call, _call_copilot
from utils import _save_to_md, human_checkpoint
from database import diff_and_log
from state import TeamState


def teamlead_decompose(state: TeamState) -> dict:
    """Entry point: receives user request, writes a brief task brief."""
    old = dict(state)
    system = (
        "You are a Senior Engineering TeamLead. "
        "Your job is to read the user's task and produce a clear, structured technical brief "
        "for your team (architect, developer, QA, devops). "
        "Be concise and unambiguous. Respond in the same language as the user."
    )

    brief = _call(
        system=system, human=f"User task:\n{state['user_request']}", agent_name="TeamLead"
    )

    feedback = human_checkpoint("TeamLead", "task_brief", brief)
    if feedback != brief:
        brief = _call(
            system=system,
            human=(
                f"User task:\n{state['user_request']}\n\n"
                f"Previous brief was rejected. Human corrections:\n{feedback}"
            ),
            agent_name="TeamLead",
        )

    update = {"user_request": brief, "review_iteration": 0}
    diff_and_log(state["task_id"], "TeamLead", 0, old, {**old, **update})
    _save_to_md(state["task_id"], "TeamLead", "task_brief", brief, state.get("project_dir"))
    return update


def teamlead_summarize(state: TeamState) -> dict:
    """Exit point: assembles final answer for the user."""
    old = dict(state)

    summary = _call_copilot(
        system=(
            "You are a Senior Engineering TeamLead. "
            "Compile the final deliverable report for the user based on "
            "architecture, code, tests and devops config produced by your team. "
            "Be structured and clear. Respond in the same language as the user."
        ),
        human=(
            f"Original request:\n{state['user_request']}\n\n"
            f"Architecture:\n{state.get('architecture', '—')}\n\n"
            f"Code:\n{state.get('code', '—')}\n\n"
            f"Review comments:\n{state.get('review_comments', '—')}\n\n"
            f"Tests:\n{state.get('test_cases', '—')}\n\n"
            f"DevOps config:\n{state.get('devops_config', '—')}\n\n"
            f"Jira project: {state.get('jira_project_key', '—')}\n"
            f"Jira tickets:\n{state.get('jira_result', '—')}"
        ),
        agent_name="TeamLead (summary)",
        model=_COPILOT_FAST_MODEL,
    )

    update = {"final_summary": summary}
    diff_and_log(
        state["task_id"], "TeamLead", state.get("review_iteration", 0), old, {**old, **update}
    )
    _save_to_md(state["task_id"], "TeamLead", "final_summary", summary, state.get("project_dir"))
    return update
