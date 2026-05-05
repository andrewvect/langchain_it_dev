"""DevOps agent: produces Dockerfile, docker-compose, and CI/CD pipeline.

Does NOT create files — outputs config text stored in state only.
"""

from llm.copilot import _COPILOT_FAST_MODEL, call_copilot
from utils import _save_to_md, human_checkpoint
from database import diff_and_log
from state import TeamState


def devops(state: TeamState) -> dict:
    old = dict(state)

    devops_system = (
        "You are a DevOps Engineer specializing in backend systems. "
        "Produce: Dockerfile, docker-compose.yml (if applicable), "
        "GitHub Actions CI/CD pipeline (.github/workflows/ci.yml). "
        "Add health checks and best practices. "
        "Respond in the same language as the user. "
        "Do NOT create, modify, or delete any files — output configuration as text only."
    )
    project_dir = state.get("project_dir")
    config = call_copilot(
        system=devops_system,
        human=(
            f"Architecture:\n{state.get('architecture', '')}\n\n"
            f"Code structure and notes:\n{state.get('developer_notes', '')}"
        ),
        agent_name="DevOps",
        model=_COPILOT_FAST_MODEL,
        cwd=project_dir,
    )

    feedback = human_checkpoint("DevOps", "devops_config", config)
    if feedback != config:
        config = call_copilot(
            system=devops_system,
            human=(
                f"Architecture:\n{state.get('architecture', '')}\n\n"
                f"Code structure and notes:\n{state.get('developer_notes', '')}\n\n"
                f"Previous config was rejected. Human corrections:\n{feedback}"
            ),
            agent_name="DevOps",
            model=_COPILOT_FAST_MODEL,
            cwd=project_dir,
        )

    update = {"devops_config": config}
    diff_and_log(
        state["task_id"], "DevOps", state.get(
            "review_iteration", 0), old, {**old, **update}
    )
    _save_to_md(
        state["task_id"], "DevOps", "devops_config", config,
        state.get("project_dir"),
        input_content=(
            f"Architecture:\n{state.get('architecture', '')}\n\n"
            f"Code structure and notes:\n{state.get('developer_notes', '')}"
        ),
    )
    return update
