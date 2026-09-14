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
        answer = format_answer(state["question"], state["query_result"])
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


if __name__ == "__main__":  # quick manual smoke test
    import sys

    q = " ".join(sys.argv[1:]) or "How many movies are in the database?"
    result = answer_question(q)
    print("SQL:   ", result.get("generated_sql"))
    print("Rows:  ", result.get("query_result"))
    print("Answer:", result.get("final_answer"))
