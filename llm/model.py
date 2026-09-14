"""OpenRouter LLM client (via the OpenAI-compatible endpoint).

Member 2 (LLM & LangChain) owns this file. OpenRouter exposes an
OpenAI-compatible API, so we use `ChatOpenAI` from langchain-openai and point
its base_url at OpenRouter.
"""
from __future__ import annotations

from langchain_openai import ChatOpenAI

from config import settings


def get_llm(temperature: float = 0.0, model: str | None = None) -> ChatOpenAI:
    """Return a configured chat model.

    Temperature defaults to 0 for deterministic SQL generation.
    Pass `model` to override the default (useful for the model-comparison
    experiment in section 13 of the project doc).
    """
    return ChatOpenAI(
        model=model or settings.LLM_MODEL,
        temperature=temperature,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        # OpenRouter uses these headers for attribution / rankings.
        default_headers={
            "HTTP-Referer": settings.OPENROUTER_SITE_URL,
            "X-Title": settings.OPENROUTER_APP_NAME,
        },
    )
