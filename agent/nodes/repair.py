"""Node 6 - Error Handling / SQL Repair.

Invoked when validation or execution failed. Sends the original question, the
failing SQL, the error, and the schema back to the LLM for a corrected query,
and increments the retry counter. The graph enforces the max-retry cap.
"""
from __future__ import annotations

from agent.state import AgentState
from llm.sql_generator import repair_sql


def repair_node(state: AgentState) -> AgentState:
    error = state.get("database_error") or state.get("validation_error") or "unknown error"
    fixed = repair_sql(
        question=state["question"],
        schema=state["schema"],
        generated_sql=state.get("generated_sql", ""),
        error=error,
    )
    return {
        "generated_sql": fixed,
        "retry_count": state.get("retry_count", 0) + 1,
        "validation_error": None,
        "database_error": None,
    }
