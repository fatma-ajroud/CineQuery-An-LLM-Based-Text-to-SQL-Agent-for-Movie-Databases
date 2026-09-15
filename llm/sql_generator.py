"""SQL generation and repair chains built on the OpenRouter LLM.

Member 2 (LLM & LangChain) owns this file. These functions are called by the
LangGraph nodes (Member 3).
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from llm.model import get_llm
from llm.prompts import (
    ANSWER_PROMPT,
    FEW_SHOT_EXAMPLES,
    RELATIONSHIPS,
    SQL_GENERATION_PROMPT,
    SQL_REPAIR_PROMPT,
    SQL_SYSTEM_PROMPT,
)


def _clean_sql(text: str) -> str:
    """Strip markdown fences / stray prose so we hand the DB pure SQL."""
    text = text.strip()
    if text.startswith("```"):
        # remove ```sql ... ``` fences
        text = text.strip("`")
        if text.lower().startswith("sql"):
            text = text[3:]
    return text.strip().rstrip(";").strip()


def generate_sql(question: str, schema: str) -> str:
    """Generate an initial SQL query from a question + schema."""
    llm = get_llm()
    messages = [
        SystemMessage(content=SQL_SYSTEM_PROMPT),
        HumanMessage(
            content=SQL_GENERATION_PROMPT.format(
                schema=schema,
                relationships=RELATIONSHIPS,
                examples=FEW_SHOT_EXAMPLES,
                question=question,
            )
        ),
    ]
    response = llm.invoke(messages)
    return _clean_sql(response.content)


def repair_sql(question: str, schema: str, generated_sql: str, error: str) -> str:
    """Ask the LLM to fix a query that failed validation or execution."""
    llm = get_llm()
    messages = [
        SystemMessage(content=SQL_SYSTEM_PROMPT),
        HumanMessage(
            content=SQL_REPAIR_PROMPT.format(
                schema=schema,
                question=question,
                generated_sql=generated_sql,
                error=error,
            )
        ),
    ]
    response = llm.invoke(messages)
    return _clean_sql(response.content)


def format_answer(question: str, rows: list[dict]) -> str:
    """Turn result rows into a natural-language answer (Node 7)."""
    llm = get_llm(temperature=0.2)
    messages = [
        HumanMessage(
            content=ANSWER_PROMPT.format(question=question, rows=rows)
        ),
    ]
    response = llm.invoke(messages)
    return response.content.strip()
