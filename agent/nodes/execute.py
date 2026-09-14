"""Node 5 - SQL Execution.

Runs the validated SELECT against PostgreSQL via SQLAlchemy. On success sets
`query_result`; on failure sets `database_error` so the graph routes to the
repair node.
"""
from __future__ import annotations

from agent.state import AgentState
from db import run_query


def execute_node(state: AgentState) -> AgentState:
    sql = state["generated_sql"]
    try:
        rows = run_query(sql)
        return {"query_result": rows, "database_error": None}
    except Exception as exc:  # noqa: BLE001 - any DB error feeds the repair loop
        return {"query_result": None, "database_error": str(exc)}
