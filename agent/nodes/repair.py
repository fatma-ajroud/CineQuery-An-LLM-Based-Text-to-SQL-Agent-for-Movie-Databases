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
    try:
        fixed = repair_sql(
            question=state["question"],
            schema=state["schema"],
            generated_sql=state.get("generated_sql", ""),
            error=error,
        )
    except Exception as exc:  # noqa: BLE001 - LLM call failure still counts as a retry
        return {
            "generated_sql": "",
            "retry_count": state.get("retry_count", 0) + 1,
            "validation_error": f"LLM call failed: {exc}",
            "database_error": None,
        }
    return {
        "generated_sql": fixed,
        "retry_count": state.get("retry_count", 0) + 1,
        "validation_error": None,
        "database_error": None,
    }
