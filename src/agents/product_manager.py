"""Product Manager agent: translates user request into a structured PRD.

Does NOT create files — outputs text (PRD) stored in state only.
"""

from llm.copilot import call_claude
from utils import _save_to_md, human_checkpoint
from database import diff_and_log
from state import TeamState


def product_manager(state: TeamState) -> dict:
    old = dict(state)

    system = (
        "You are an experienced Product Manager. "
        "Transform the raw user request into a clear Product Requirements Document (PRD): "
        "business goals, user stories, acceptance criteria, out-of-scope items, and priorities. "
        "Be precise so the engineering team has no ambiguity. "
        "Respond in the same language as the user. "
        "Your role is ONLY to produce a PRD — do NOT write code, tests, or implementation details, "
        "and do NOT offer to implement anything. "
        "Do NOT create, modify, or delete any files."
    )

    project_dir = state.get("project_dir")
    prd = call_claude(
        system=system,
        human=f"User request:\n{state['user_request']}",
        agent_name="ProductManager",
        cwd=project_dir,
        # PM doesn't need file access, and this prevents premature file creation by design-phase agents
        allow_tools=False,
    )

    feedback = human_checkpoint("ProductManager", "product_brief", prd)
    if feedback != prd:
        prd = call_claude(
            system=system,
            human=(
                f"User request:\n{state['user_request']}\n\n"
                f"Previous PRD was rejected. Human corrections:\n{feedback}"
            ),
            agent_name="ProductManager",
            cwd=project_dir,
            allow_tools=False,
        )

    update = {"product_brief": prd}
    diff_and_log(state["task_id"], "ProductManager", 0, old, {**old, **update})
    _save_to_md(
        state["task_id"], "ProductManager", "product_brief", prd,
        state.get("project_dir"),
        input_content=f"User request:\n{state['user_request']}",
    )
    return update
