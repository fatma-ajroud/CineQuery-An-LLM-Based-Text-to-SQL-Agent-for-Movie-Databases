"""
Streamlit front-end for the Text-to-SQL Movie Database agent.

Run with:
    streamlit run app/streamlit_app.py

For each question the UI shows, in order:
    1. the user's natural-language question
    2. the SQL generated (and executed) by the agent
    3. the raw execution result (as a table)
    4. the final natural-language answer

The UI is decoupled from the agent implementation via `agent.graph.run_agent`,
so it works today against the placeholder mock agent and will work unchanged
once Member 2/3 wire in the real LangChain + LangGraph pipeline.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make the project root importable when Streamlit runs this file directly.
sys.path.append(str(Path(__file__).resolve().parent.parent))

from agent.graph import _credentials_available, run_agent  # noqa: E402

st.set_page_config(
    page_title="Movie DB — Ask in Plain English",
    page_icon="🎬",
    layout="centered",
)

EXAMPLE_QUESTIONS = [
    "How many movies are in the database?",
    "Which directors have the highest average movie rating?",
    "Which actors appeared in Inception?",
    "Which genres have an average rating above 8?",
]

if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: question/sql/columns/rows/answer/error


def render_turn(turn: dict) -> None:
    with st.chat_message("user"):
        st.markdown(turn["question"])

    with st.chat_message("assistant"):
        if turn.get("error"):
            st.error(f"The query failed after {turn['attempts']} attempt(s): {turn['error']}")
            return

        st.markdown(turn["answer"])

        with st.expander(f"Generated SQL ({turn['attempts']} attempt(s))", expanded=False):
            st.code(turn["sql"], language="sql")

        if turn["rows"]:
            df = pd.DataFrame(turn["rows"], columns=turn["columns"])
            st.dataframe(df, use_container_width=True, hide_index=True)


def ask(question: str) -> None:
    with st.spinner("Thinking through the schema and generating SQL..."):
        result = run_agent(question)

    st.session_state.history.append(
        {
            "question": question,
            "sql": result["sql"],
            "columns": result["columns"],
            "rows": result["rows"],
            "answer": result["answer"],
            "attempts": result["attempts"],
            "error": result["error"],
        }
    )


# --- Sidebar -----------------------------------------------------------
with st.sidebar:
    st.header("🎬 Movie Text-to-SQL")
    st.caption(
        "Ask questions in plain English. The agent generates SQL, "
        "runs it against PostgreSQL, and explains the result."
    )

    st.subheader("Try an example")
    for example in EXAMPLE_QUESTIONS:
        if st.button(example, use_container_width=True, key=f"ex_{example}"):
            ask(example)

    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.history = []
        st.rerun()

    st.divider()
    if _credentials_available():
        st.success("Real agent active — LangGraph + Postgres", icon="✅")
    else:
        st.warning(
            "Running on the mock agent (no OPENROUTER_API_KEY / "
            "DATABASE_URL detected). See README.md to switch on "
            "the real LangGraph pipeline.",
            icon="⚠️",
        )

# --- Main chat area ------------------------------------------------------
st.title("Ask your movie database anything")

for turn in st.session_state.history:
    render_turn(turn)

question = st.chat_input("e.g. Which director has directed more than three movies?")
if question:
    ask(question)
    st.rerun()
