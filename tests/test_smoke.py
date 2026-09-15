"""Smoke tests that don't require a live LLM or database.

These verify the scaffold imports cleanly and the validation logic behaves.
Run:  pytest -q
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_state_factory():
    from agent.state import new_state

    s = new_state("How many movies?")
    assert s["question"] == "How many movies?"
    assert s["retry_count"] == 0


def test_clean_sql_strips_fences():
    from llm.sql_generator import _clean_sql

    assert _clean_sql("```sql\nSELECT 1;\n```") == "SELECT 1"
    assert _clean_sql("SELECT 1;") == "SELECT 1"


def test_validate_rejects_empty_sql():
    from agent.nodes.validate import validate_node

    result = validate_node({"generated_sql": ""})
    assert result["validation_result"] is False


def test_validate_rejects_non_select():
    from agent.nodes.validate import validate_node

    result = validate_node({"generated_sql": "DELETE FROM movies;"})
    assert result["validation_result"] is False


def test_validate_rejects_multiple_statements():
    from agent.nodes.validate import validate_node

    result = validate_node({"generated_sql": "SELECT 1; SELECT 2;"})
    assert result["validation_result"] is False
    assert "one SQL statement" in result["validation_error"]


def test_validate_accepts_plain_select():
    from agent.nodes.validate import validate_node

    result = validate_node(
        {"generated_sql": "SELECT * FROM movies WHERE release_year > 2015;"}
    )
    assert result["validation_result"] is True
