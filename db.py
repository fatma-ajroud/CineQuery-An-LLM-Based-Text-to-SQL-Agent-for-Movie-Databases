"""SQLAlchemy database access + schema introspection.

Shared by the schema-retrieval node (reads the schema for the prompt) and the
execution node (runs the validated SELECT).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from config import settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """Lazily create and cache the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_schema_text() -> str:
    """Return a compact textual schema (tables + columns + types) for prompts.

    Introspects the live database so the prompt always matches reality.
    """
    inspector = inspect(get_engine())
    lines: list[str] = []
    for table in inspector.get_table_names(schema="public"):
        cols = inspector.get_columns(table, schema="public")
        col_desc = ", ".join(f"{c['name']} {c['type']}" for c in cols)
        lines.append(f"{table}({col_desc})")
    return "\n".join(lines)


def run_query(sql: str) -> list[dict[str, Any]]:
    """Execute a read-only SQL query and return rows as dicts.

    Raises whatever SQLAlchemy/psycopg2 raises on error; the execute node
    catches it and routes to the repair node.
    """
    with get_engine().connect() as conn:
        result = conn.execute(text(sql))
        return [dict(row) for row in result.mappings().all()]
