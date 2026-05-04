"""
LangGraph definition for the IT Backend Team.

Flow (TDD):
  teamlead_decompose
        │
        ▼
    architect
        │
        ▼
   qa_engineer   ← writes tests first (TDD)
        │
        ▼
    developer ◄──────────────────────────────────┐
        │                                         │
        ▼                                         │
    reviewer ──── "rework" (< MAX_ITERATIONS) ───┘
        │
        └── "approved"
              │
          jira_setup
              │
             devops
              │
     teamlead_summarize
"""

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents import (
    architect,
    developer,
    devops,
    jira_setup,
    qa_engineer,
    reviewer,
    teamlead_decompose,
    teamlead_summarize,
)
from config import DB_PATH, MAX_REVIEW_ITERATIONS
from state import TeamState

_chk_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
team_checkpointer = SqliteSaver(_chk_conn)


def route_after_review(state: TeamState) -> str:
    """Conditional edge: send to rework or proceed to DevOps."""
    if (
        state.get("review_result") == "rework"
        and state.get("review_iteration", 0) < MAX_REVIEW_ITERATIONS
    ):
        return "developer"
    return "jira_setup"


def build_graph() -> CompiledStateGraph:
    g = StateGraph(TeamState)

    # ── Nodes ────────────────────────────────────────────────────────────────
    g.add_node("teamlead_decompose", teamlead_decompose)
    g.add_node("architect", architect)
    g.add_node("qa_engineer", qa_engineer)
    g.add_node("developer", developer)
    g.add_node("reviewer", reviewer)
    g.add_node("jira_setup", jira_setup)
    g.add_node("devops", devops)
    g.add_node("teamlead_summarize", teamlead_summarize)

    # ── Edges ────────────────────────────────────────────────────────────────
    g.set_entry_point("teamlead_decompose")
    g.add_edge("teamlead_decompose", "architect")
    g.add_edge("architect", "qa_engineer")  # TDD: tests before code
    g.add_edge("qa_engineer", "developer")
    g.add_edge("developer", "reviewer")

    g.add_conditional_edges(
        "reviewer",
        route_after_review,
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
