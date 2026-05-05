"""TeamLead agent: decompose user request and summarize final output.

Does NOT create files — outputs text stored in state only.
"""

from llm.copilot import call_claude, call_copilot
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
        "Be concise and unambiguous. Respond in the same language as the user. "
        "Do NOT create, modify, or delete any files."
    )

    project_dir = state.get("project_dir")
    brief = call_claude(
        system=system,
        human=(
            f"Product requirements:\n{state.get('product_brief', '')}\n\n"
            f"User task:\n{state['user_request']}"
        ),
        agent_name="TeamLead", cwd=project_dir,
        allow_tools=False,  # TeamLead doesn't need file access, and this prevents premature file creation by design-phase agents
    )

    feedback = human_checkpoint("TeamLead", "task_brief", brief)
    if feedback != brief:
        brief = call_claude(
            system=system,
            human=(
                f"Product requirements:\n{state.get('product_brief', '')}\n\n"
                f"User task:\n{state['user_request']}\n\n"
                f"Previous brief was rejected. Human corrections:\n{feedback}"
            ),
            agent_name="TeamLead",
            cwd=project_dir,
            allow_tools=False,  # TeamLead doesn't need file access, and this prevents premature file creation by design-phase agents
        )

    update = {"user_request": brief, "review_iteration": 0}
    diff_and_log(state["task_id"], "TeamLead", 0, old, {**old, **update})
    _save_to_md(
        state["task_id"], "TeamLead", "task_brief", brief,
        state.get("project_dir"),
        input_content=(
            f"Product requirements:\n{state.get('product_brief', '')}\n\n"
            f"User task:\n{state['user_request']}"
        ),
    )
    return update


def teamlead_summarize(state: TeamState) -> dict:
    """Exit point: assembles final answer for the user."""
    old = dict(state)

    summary = call_copilot(
        system=(
            "You are a Senior Engineering TeamLead. "
            "Compile the final deliverable report for the user based on "
            "architecture, code, tests and devops config produced by your team. "
            "Be structured and clear. Respond in the same language as the user. "
            "Do NOT create, modify, or delete any files."
        ),
        human=(
            f"Original request:\n{state['user_request']}\n\n"
            f"Architecture:\n{state.get('architecture', '—')}\n\n"
            f"Code:\n{state.get('code', '—')}\n\n"
            f"Review comments:\n{state.get('review_comments', '—')}\n\n"
            f"QA validation:\n{state.get('qa_validation_comments', '—')}\n\n"
            f"CI result:\n{state.get('ci_comments', '—')}\n\n"
            f"Tests:\n{state.get('test_cases', '—')}\n\n"
            f"DevOps config:\n{state.get('devops_config', '—')}\n\n"
            f"Jira project: {state.get('jira_project_key', '—')}\n"
            f"Jira tickets:\n{state.get('jira_result', '—')}"
        ),
        agent_name="TeamLead (summary)",
        cwd=state.get("project_dir"),
    )

    update = {"final_summary": summary}
    diff_and_log(
        state["task_id"], "TeamLead", state.get(
            "review_iteration", 0), old, {**old, **update}
    )
    _save_to_md(
        state["task_id"], "TeamLead", "final_summary", summary,
        state.get("project_dir"),
        input_content=(
            f"Original request:\n{state['user_request']}\n\n"
            f"Architecture:\n{state.get('architecture', '—')}\n\n"
            f"Review comments:\n{state.get('review_comments', '—')}\n\n"
            f"QA validation:\n{state.get('qa_validation_comments', '—')}\n\n"
            f"CI result:\n{state.get('ci_comments', '—')}"
        ),
    )
    return update
