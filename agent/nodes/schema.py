"""Node 2 - Schema Retrieval.

Provides the LLM with the relevant database schema. Because the database is
small, the complete schema is supplied. A later improvement could retrieve
only the tables relevant to the question.
"""
from __future__ import annotations

from agent.state import AgentState
from db import get_schema_text


def schema_node(state: AgentState) -> AgentState:
    schema = get_schema_text()
    return {"schema": schema}
