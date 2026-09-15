"""Node 3 - SQL Generation.

Calls the LLM (via the llm package) to produce a PostgreSQL query from the
schema + question. Used both for the first attempt and, indirectly, after a
repair resets the SQL.
"""
from __future__ import annotations

from agent.state import AgentState
from llm.sql_generator import generate_sql


def generate_sql_node(state: AgentState) -> AgentState:
    try:
        sql = generate_sql(question=state["question"], schema=state["schema"])
    except Exception as exc:  # noqa: BLE001 - LLM call failure feeds the repair loop
        return {
            "generated_sql": "",
            "validation_error": f"LLM call failed: {exc}",
            "database_error": None,
        }
    # Clear any stale errors from a previous attempt.
    return {
        "generated_sql": sql,
        "validation_error": None,
        "database_error": None,
    }
