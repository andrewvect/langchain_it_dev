"""DevOps agent: produces Dockerfile, docker-compose, and CI/CD pipeline."""

from llm.copilot import _COPILOT_FAST_MODEL, _call_copilot
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
        "Respond in the same language as the user."
    )
    config = _call_copilot(
        system=devops_system,
        human=(
            f"Architecture:\n{state.get('architecture', '')}\n\n"
            f"Code structure and notes:\n{state.get('developer_notes', '')}"
        ),
        agent_name="DevOps",
        model=_COPILOT_FAST_MODEL,
    )

    feedback = human_checkpoint("DevOps", "devops_config", config)
    if feedback != config:
        config = _call_copilot(
            system=devops_system,
            human=(
                f"Architecture:\n{state.get('architecture', '')}\n\n"
                f"Code structure and notes:\n{state.get('developer_notes', '')}\n\n"
                f"Previous config was rejected. Human corrections:\n{feedback}"
            ),
            agent_name="DevOps",
            model=_COPILOT_FAST_MODEL,
        )

    update = {"devops_config": config}
    diff_and_log(
        state["task_id"], "DevOps", state.get("review_iteration", 0), old, {**old, **update}
    )
    _save_to_md(state["task_id"], "DevOps", "devops_config", config, state.get("project_dir"))
    return update
