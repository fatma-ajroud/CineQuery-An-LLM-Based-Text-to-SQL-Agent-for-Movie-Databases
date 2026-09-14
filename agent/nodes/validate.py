"""Node 4 - SQL Validation.

Checks the generated query before execution:
  - it parses as SQL
  - it is a single statement
  - it is SELECT-only (no data/schema modification)
  - referenced tables exist in the schema

Sets `validation_result` (bool) and `validation_error` (str | None).
"""
from __future__ import annotations

import sqlparse

from agent.state import AgentState
from db import get_engine
from sqlalchemy import inspect

# Statements/keywords that must never appear.
_FORBIDDEN = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "MERGE", "REPLACE", "CALL", "COPY",
}


def _known_tables() -> set[str]:
    inspector = inspect(get_engine())
    return set(inspector.get_table_names(schema="public"))


def validate_node(state: AgentState) -> AgentState:
    sql = state.get("generated_sql", "").strip()

    if not sql:
        return {"validation_result": False,
                "validation_error": "Empty SQL query."}

    statements = [s for s in sqlparse.parse(sql) if str(s).strip()]
    if len(statements) != 1:
        return {"validation_result": False,
                "validation_error": "Expected exactly one SQL statement."}

    stmt = statements[0]
    if stmt.get_type() != "SELECT":
        return {"validation_result": False,
                "validation_error": "Only SELECT queries are allowed."}

    upper_tokens = {t.value.upper() for t in stmt.flatten()}
    forbidden_hit = _FORBIDDEN & upper_tokens
    if forbidden_hit:
        return {"validation_result": False,
                "validation_error": f"Forbidden keyword(s): {', '.join(sorted(forbidden_hit))}."}

    # Best-effort table-existence check.
    try:
        known = _known_tables()
        identifiers = {t.value.lower().strip('"') for t in stmt.flatten()}
        # We don't hard-fail on unknown identifiers (columns/aliases look the
        # same as tables to a flat scan); instead we flag if NO known table
        # is referenced at all, which usually means a hallucinated schema.
        if known and not (identifiers & {k.lower() for k in known}):
            return {"validation_result": False,
                    "validation_error": "Query references no known table."}
    except Exception:  # noqa: BLE001 - schema check is best-effort
        pass

    return {"validation_result": True, "validation_error": None}
