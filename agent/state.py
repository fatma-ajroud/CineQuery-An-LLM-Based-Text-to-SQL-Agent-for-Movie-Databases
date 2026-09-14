"""LangGraph shared state for the Text-to-SQL agent.

The state is a plain TypedDict passed between graph nodes. Each node reads
some keys and writes others. Fields mirror section 8 of the project doc.
"""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # --- input ---
    question: str                     # the user's natural-language question

    # --- schema retrieval ---
    schema: str                       # textual schema (DDL / description) for the prompt

    # --- generation ---
    generated_sql: str                # SQL produced by the LLM

    # --- validation ---
    validation_result: bool           # True if the SQL passed validation
    validation_error: Optional[str]   # why validation failed (if it did)

    # --- execution ---
    query_result: Optional[list[dict[str, Any]]]  # rows returned by PostgreSQL
    database_error: Optional[str]     # error string returned by PostgreSQL

    # --- repair loop bookkeeping ---
    retry_count: int                  # how many repair attempts so far

    # --- output ---
    final_answer: str                 # natural-language answer for the user


def new_state(question: str) -> AgentState:
    """Create a fresh state for a run."""
    return AgentState(
        question=question,
        schema="",
        generated_sql="",
        validation_result=False,
        validation_error=None,
        query_result=None,
        database_error=None,
        retry_count=0,
        final_answer="",
    )
