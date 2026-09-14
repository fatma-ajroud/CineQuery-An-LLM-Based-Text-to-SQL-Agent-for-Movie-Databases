"""Prompt templates for SQL generation, repair, and answer formatting.

Member 2 (LLM & LangChain) owns and iterates on these. Keep prompts here so
the model-comparison experiment uses identical prompts across models.
"""
from __future__ import annotations

# System prompt: rules the model must always follow.
SQL_SYSTEM_PROMPT = """\
You are an expert PostgreSQL analyst for a movie database.
Translate the user's natural-language question into a single valid
PostgreSQL query.

Rules:
- Use ONLY the tables and columns given in the schema. Never invent names.
- Generate a SELECT query only. Never write INSERT, UPDATE, DELETE, DROP,
  ALTER, TRUNCATE, or any statement that modifies data or schema.
- Return ONLY the SQL query. No explanation, no markdown fences, no commentary.
- Prefer explicit JOINs using the foreign keys described in the relationships.
- When the question implies aggregation, use GROUP BY / HAVING / ORDER BY
  appropriately.
"""

# Human prompt for the initial generation. Filled with schema + question.
SQL_GENERATION_PROMPT = """\
Database schema:
{schema}

Relationships:
{relationships}

User question:
{question}

Return only the PostgreSQL SELECT query.
"""

# Repair prompt: given the failing SQL and the DB/validation error, fix it.
SQL_REPAIR_PROMPT = """\
The following PostgreSQL query failed.

Database schema:
{schema}

Original question:
{question}

Query that failed:
{generated_sql}

Error:
{error}

Return a corrected PostgreSQL SELECT query that fixes the error.
Return only the SQL query, no explanation.
"""

# Answer-formatting prompt: turn raw rows into a natural-language answer.
ANSWER_PROMPT = """\
The user asked:
{question}

The SQL query returned these rows:
{rows}

Write a short, clear natural-language answer to the user's question based on
these rows. Do not mention SQL or databases. If there are no rows, say that
no matching results were found.
"""

# Static description of the relationships, injected into generation prompts.
RELATIONSHIPS = """\
- movies (movie_id PK)
- directors (director_id PK), actors (actor_id PK), genres (genre_id PK)
- ratings.movie_id -> movies.movie_id  (a movie can have several ratings)
- movie_directors(movie_id -> movies, director_id -> directors)
- movie_actors(movie_id -> movies, actor_id -> actors, role)
- movie_genres(movie_id -> movies, genre_id -> genres)
"""
