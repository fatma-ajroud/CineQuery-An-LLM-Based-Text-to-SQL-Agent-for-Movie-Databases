"""
Streamlit front-end for the Text-to-SQL Movie Database agent.

Run with:
    streamlit run app/streamlit_app.py

Framed as a film archive's request desk rather than a generic chatbot: you
submit a request (a question), the archivist (the agent) pulls the record,
checks it against the catalog (schema/SQL), and hands back a ticket with
the query, the result, and the verdict (the final answer).

For each question the UI shows, in order:
    1. the user's natural-language question
    2. the SQL generated (and executed) by the agent
    3. the raw execution result (as a table)
    4. the final natural-language answer

The UI is decoupled from the agent implementation via `agent.graph.run_agent`.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make the project root importable when Streamlit runs this file directly.
sys.path.append(str(Path(__file__).resolve().parent.parent))

from agent.graph import _credentials_available, run_agent  # noqa: E402

st.set_page_config(
    page_title="Movie Archive Desk",
    page_icon="🎟️",
    layout="centered",
)

EXAMPLE_QUESTIONS = [
    "How many movies are in the database?",
    "Which directors have directed more than three movies?",
    "Which actors appeared in Inception?",
    "Which genres have an average rating above 8?",
]

if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: question/sql/columns/rows/answer/attempts/latency_s/error


# --- Styling -------------------------------------------------------------
# CSS is scoped to Streamlit's data-testid hooks (more stable across
# versions than its internal, auto-generated class names) plus a few
# custom classes we own outright. If a hook has shifted in your installed
# Streamlit version, the selector simply matches nothing - the app still
# works, just without that one cosmetic touch.
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    html, body, [class^="st-"], .stMarkdown, .stButton button,
    .stTextInput input, textarea {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    code, pre, [data-testid="stCodeBlock"], [data-testid="stCode"] {
        font-family: 'IBM Plex Mono', monospace !important;
    }

    .archive-hero {
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 2.3rem;
        letter-spacing: -0.01em;
        color: #16231F;
        margin-bottom: 0.15rem;
    }
    .archive-subhead {
        color: #4B5A52;
        font-size: 1rem;
        margin-bottom: 1.6rem;
        max-width: 46em;
    }
    .ticket-number {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        color: #4B5A52;
        letter-spacing: 0.02em;
    }
    .ticket-question {
        font-size: 1.05rem;
        font-weight: 600;
        color: #16231F;
        margin: 0.1rem 0 0.5rem 0;
    }
    .section-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        color: #4B5A52;
        margin: 0.85rem 0 0.3rem 0;
    }
    .verdict {
        border-left: 3px solid #B8912E;
        padding: 0.35rem 0 0.35rem 0.8rem;
        margin-top: 0.7rem;
        font-size: 1.02rem;
        color: #16231F;
    }
    .verdict-meta {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.74rem;
        color: #4B5A52;
        margin-top: 0.3rem;
    }
    .not-found {
        border-left: 3px solid #8C3B2E;
        padding: 0.35rem 0 0.35rem 0.8rem;
        margin-top: 0.7rem;
        color: #16231F;
    }

    section[data-testid="stSidebar"] .stButton button {
        text-align: left;
        justify-content: flex-start;
        border: none;
        border-left: 3px solid #C9C2AC;
        border-radius: 0;
        background: transparent;
        padding-left: 0.7rem;
        font-size: 0.87rem;
        color: #16231F;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        border-left-color: #B8912E;
        background: rgba(184, 145, 46, 0.10);
        color: #16231F;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_turn(turn: dict, number: int) -> None:
    with st.container(border=True):
        st.markdown(f'<div class="ticket-number">TICKET No. {number:03d}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ticket-question">{turn["question"]}</div>', unsafe_allow_html=True)

        if turn.get("error"):
            st.markdown(
                f'<div class="not-found">Request could not be filled after '
                f'{turn["attempts"]} attempt(s): {turn["error"]}</div>',
                unsafe_allow_html=True,
            )
            return

        st.markdown('<div class="section-label">query</div>', unsafe_allow_html=True)
        st.code(turn["sql"], language="sql")

        if turn["rows"]:
            st.markdown('<div class="section-label">result</div>', unsafe_allow_html=True)
            df = pd.DataFrame(turn["rows"], columns=turn["columns"])
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-label">verdict</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="verdict">{turn["answer"]}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="verdict-meta">{turn["attempts"]} repair attempt(s) '
            f'&middot; {turn["latency_s"]:.1f}s</div>',
            unsafe_allow_html=True,
        )


def ask(question: str) -> None:
    with st.spinner("Pulling the file..."):
        result = run_agent(question)

    st.session_state.history.append(
        {
            "question": question,
            "sql": result["sql"],
            "columns": result["columns"],
            "rows": result["rows"],
            "answer": result["answer"],
            "attempts": result["attempts"],
            "latency_s": result["latency_s"],
            "error": result["error"],
        }
    )


# --- Sidebar: the desk -----------------------------------------------------
with st.sidebar:
    st.markdown("### The Archive Desk")
    st.caption(
        "Submit a request in plain English. The archivist writes the "
        "catalog query, checks it, and hands back a ticket with the "
        "result."
    )

    st.markdown("**Try a request**")
    for example in EXAMPLE_QUESTIONS:
        if st.button(example, use_container_width=True, key=f"ex_{example}"):
            ask(example)

    st.divider()
    if st.button("Clear the desk", use_container_width=True):
        st.session_state.history = []
        st.rerun()

    st.divider()
    if _credentials_available():
        st.success("Desk configured — API key and database URL are set.", icon="🗂️")
    else:
        st.warning(
            "Desk not fully configured — add OPENROUTER_API_KEY and "
            "DATABASE_URL in .env. See docs/RUNBOOK.md.",
            icon="🗃️",
        )

# --- Main: the reading room ------------------------------------------------
st.markdown('<div class="archive-hero">The Movie Archive</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="archive-subhead">Ask a question in plain English. '
    "The archive turns it into a query, checks the catalog, and returns "
    "a ticket with the result.</div>",
    unsafe_allow_html=True,
)

for i, turn in enumerate(st.session_state.history, start=1):
    render_turn(turn, i)

question = st.chat_input("Submit a request, e.g. Which director has directed more than three movies?")
if question:
    ask(question)
    st.rerun()
