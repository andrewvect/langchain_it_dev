"""
LangGraph definition for the IT Backend Team.

Flow:
  product_manager
        |
        v
  teamlead_decompose
        |
        v
    architect
        |
        v
  qa_test_design   <- writes tests first (TDD)
        |
        v
   developer <------------------------------------------------------+
        |                                                           |
        v                                                           |
    reviewer ---- "rework" -----------------------------------------+
        |                                                           |
        +-- "approved"                                              |
              |                                                     |
        qa_validation ---- "fail" ----------------------------------+
              |                                                     |
              +-- "pass"                                            |
                    |                                               |
              ci_validator ---- "fail" (tests or lint/build) ------+
                    |
                    +-- "pass"
                          |
                      jira_setup
                          |
                        devops
                          |
                  teamlead_summarize
"""

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents import (
    architect,
    ci_validator,
    developer,
    devops,
    jira_setup,
    product_manager,
    qa_test_design,
    qa_validation,
    reviewer,
    teamlead_decompose,
    teamlead_summarize,
)
from config import DB_PATH, MAX_REVIEW_ITERATIONS
from state import TeamState

_chk_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
team_checkpointer = SqliteSaver(_chk_conn)


def route_after_review(state: TeamState) -> str:
    """Conditional edge: send back for rework or proceed to QA validation."""
    if (
        state.get("review_result") == "rework"
        and state.get("review_iteration", 0) < MAX_REVIEW_ITERATIONS
    ):
        return "developer"
    return "qa_validation"


def route_after_qa_validation(state: TeamState) -> str:
    """Conditional edge: send back for rework or proceed to CI."""
    if (
        state.get("qa_validation_result") == "fail"
        and state.get("review_iteration", 0) < MAX_REVIEW_ITERATIONS
    ):
        return "developer"
    return "ci_validator"


def route_after_ci(state: TeamState) -> str:
    """Conditional edge: send back for rework or proceed to Jira."""
    if (
        state.get("ci_result") == "fail"
        and state.get("review_iteration", 0) < MAX_REVIEW_ITERATIONS
    ):
        return "developer"
    return "jira_setup"


def build_graph() -> CompiledStateGraph:
    g = StateGraph(TeamState)

    # -- Nodes ----------------------------------------------------------------
    g.add_node("product_manager", product_manager)
    g.add_node("teamlead_decompose", teamlead_decompose)
    g.add_node("architect", architect)
    g.add_node("qa_test_design", qa_test_design)
    g.add_node("developer", developer)
    g.add_node("reviewer", reviewer)
    g.add_node("qa_validation", qa_validation)
    g.add_node("ci_validator", ci_validator)
    g.add_node("jira_setup", jira_setup)
    g.add_node("devops", devops)
    g.add_node("teamlead_summarize", teamlead_summarize)

    # -- Edges ----------------------------------------------------------------
    g.set_entry_point("product_manager")
    g.add_edge("product_manager", "teamlead_decompose")
    g.add_edge("teamlead_decompose", "architect")
    g.add_edge("architect", "qa_test_design")  # TDD: tests before code
    g.add_edge("qa_test_design", "developer")
    g.add_edge("developer", "reviewer")

    g.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "developer": "developer",
            "qa_validation": "qa_validation",
        },
    )
    g.add_conditional_edges(
        "qa_validation",
        route_after_qa_validation,
        {
            "developer": "developer",
            "ci_validator": "ci_validator",
        },
    )
    g.add_conditional_edges(
        "ci_validator",
        route_after_ci,
        {
            "developer": "developer",
            "jira_setup": "jira_setup",
        },
    )
    g.add_edge("jira_setup", "devops")
    g.add_edge("devops", "teamlead_summarize")
    g.add_edge("teamlead_summarize", END)

    return g.compile(checkpointer=team_checkpointer)


team_graph = build_graph()
