"""Central configuration loaded from environment (.env).

Import `settings` anywhere:

    from config import settings
    print(settings.DATABASE_URL)
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()  # reads .env from the repo root if present


class Settings:
    # --- OpenRouter / LLM ---
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    LLM_MODEL: str = os.getenv("LLM_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
    OPENROUTER_APP_NAME: str = os.getenv("OPENROUTER_APP_NAME", "movie-text-to-sql")
    OPENROUTER_SITE_URL: str = os.getenv("OPENROUTER_SITE_URL", "http://localhost:8501")

    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://movies:movies@localhost:5432/moviesdb",
    )

    # --- Agent behaviour ---
    MAX_SQL_REPAIR_RETRIES: int = int(os.getenv("MAX_SQL_REPAIR_RETRIES", "3"))


settings = Settings()
