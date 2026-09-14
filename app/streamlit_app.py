"""Streamlit UI for the Movie Text-to-SQL agent.

Chat-style input; shows the user question, generated SQL, execution result,
and the final natural-language answer (section 10, Member 4).

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `streamlit run app/streamlit_app.py` to import project packages.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from agent.graph import answer_question

st.set_page_config(page_title="Movie Text-to-SQL", page_icon="🎬")
st.title("🎬 Movie Text-to-SQL Agent")
st.caption("Ask a question about the movie database in plain language.")

question = st.text_input(
    "Your question",
    placeholder="e.g. Which directors have the highest average movie rating?",
)

if st.button("Ask", type="primary") and question.strip():
    with st.spinner("Thinking..."):
        state = answer_question(question.strip())

    st.subheader("Answer")
    st.write(state.get("final_answer", ""))

    with st.expander("Generated SQL"):
        st.code(state.get("generated_sql", ""), language="sql")

    rows = state.get("query_result")
    if rows:
        st.subheader("Result")
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    if state.get("retry_count"):
        st.info(f"SQL was repaired {state['retry_count']} time(s) before success.")
