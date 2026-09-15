"""LangGraph workflow wiring the Text-to-SQL agent together.

Flow (see section 7 of the project doc):

    analyze -> schema -> generate_sql -> validate
        validate  --valid-->    execute
        validate  --invalid-->  repair (if retries left, else interpret)
        execute   --success-->  interpret
        execute   --error-->    repair (if retries left, else interpret)
        repair    ------------>  validate
        interpret ------------>  END

Member 3 (LangGraph & SQL Agent) owns this file.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.nodes.analyze import analyze_node
from agent.nodes.execute import execute_node
from agent.nodes.generate_sql import generate_sql_node
from agent.nodes.repair import repair_node
from agent.nodes.schema import schema_node
from agent.nodes.validate import validate_node
from agent.state import AgentState, new_state
from config import settings
from llm.sql_generator import format_answer


# ----------------------------------------------------------------- Node 7
def interpret_node(state: AgentState) -> AgentState:
    """Turn result rows (or a final error) into a natural-language answer."""
    if state.get("query_result") is not None:
        try:
            answer = format_answer(state["question"], state["query_result"])
        except Exception as exc:  # noqa: BLE001 - the query succeeded; don't crash on formatting
            n = len(state["query_result"])
            answer = (
                f"The query succeeded ({n} row(s)) but the answer could not be "
                f"summarized: {exc}"
            )
    else:
        err = state.get("database_error") or state.get("validation_error")
        answer = (
            "Sorry, I couldn't produce a valid query for that question "
            f"after {state.get('retry_count', 0)} repair attempt(s). "
            f"(Last error: {err})"
        )
    return {"final_answer": answer}


# ---------------------------------------------------- conditional routers
def _after_validate(state: AgentState) -> str:
    if state.get("validation_result"):
        return "execute"
    if state.get("retry_count", 0) < settings.MAX_SQL_REPAIR_RETRIES:
        return "repair"
    return "interpret"


def _after_execute(state: AgentState) -> str:
    if state.get("database_error") is None:
        return "interpret"
    if state.get("retry_count", 0) < settings.MAX_SQL_REPAIR_RETRIES:
        return "repair"
    return "interpret"


def build_graph():
    """Compile and return the LangGraph app."""
    g = StateGraph(AgentState)

    g.add_node("analyze", analyze_node)
    g.add_node("schema", schema_node)
    g.add_node("generate_sql", generate_sql_node)
    g.add_node("validate", validate_node)
    g.add_node("execute", execute_node)
    g.add_node("repair", repair_node)
    g.add_node("interpret", interpret_node)

    g.add_edge(START, "analyze")
    g.add_edge("analyze", "schema")
    g.add_edge("schema", "generate_sql")
    g.add_edge("generate_sql", "validate")

    g.add_conditional_edges("validate", _after_validate,
                            {"execute": "execute",
                             "repair": "repair",
                             "interpret": "interpret"})
    g.add_conditional_edges("execute", _after_execute,
                            {"interpret": "interpret",
                             "repair": "repair"})
    g.add_edge("repair", "validate")
    g.add_edge("interpret", END)

    return g.compile()


# Compiled once at import time for reuse by the app / evaluation.
graph_app = build_graph()


def answer_question(question: str) -> AgentState:
    """Convenience entry point: run the full graph on one question.

    Returns the final state (contains generated_sql, query_result,
    final_answer, retry_count, etc.).
    """
    return graph_app.invoke(new_state(question))


def _credentials_available() -> bool:
    """Whether OpenRouter + Postgres config look present.

    Informational only (drives the Streamlit sidebar badge) - it does not
    gate `run_agent`, which always calls the real graph.
    """
    return bool(settings.OPENROUTER_API_KEY) and bool(settings.DATABASE_URL)


def run_agent(question: str) -> dict:
    """UI-facing wrapper around `answer_question`.

    Shapes the final state into the flat dict app/streamlit_app.py renders
    per turn, and never raises - any exception (e.g. a missing API key or an
    unreachable database) is captured into `error` instead of crashing the
    app.
    """
    try:
        state = answer_question(question)
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI, not raised
        return {
            "sql": "",
            "columns": [],
            "rows": [],
            "answer": "",
            "attempts": 0,
            "error": str(exc),
        }

    rows = state.get("query_result") or []
    error = None
    if state.get("query_result") is None:
        error = state.get("database_error") or state.get("validation_error")

    return {
        "sql": state.get("generated_sql", ""),
        "columns": list(rows[0].keys()) if rows else [],
        "rows": rows,
        "answer": state.get("final_answer", ""),
        "attempts": state.get("retry_count", 0),
        "error": error,
    }


if __name__ == "__main__":  # quick manual smoke test
    import sys

    q = " ".join(sys.argv[1:]) or "How many movies are in the database?"
    result = answer_question(q)
    print("SQL:   ", result.get("generated_sql"))
    print("Rows:  ", result.get("query_result"))
    print("Answer:", result.get("final_answer"))
