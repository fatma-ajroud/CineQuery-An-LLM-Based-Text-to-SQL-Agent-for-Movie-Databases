"""Node 1 - Question Analysis.

Receives the user's natural-language question and determines what information
is being requested. For the first implementation this is a light pass-through
(the whole schema is given to the generator anyway). It's a place to add
intent detection or question classification later.
"""
from __future__ import annotations

from agent.state import AgentState


def analyze_node(state: AgentState) -> AgentState:
    question = state["question"].strip()
    # TODO(Member 3): optionally classify difficulty/intent, extract entities.
    return {"question": question}
