# Architecture

Technical reference for how this repository is put together: what each
folder/file does, how modules depend on each other, and how a question flows
from the UI to an answer. For setup/run instructions see the root
[README.md](../README.md).

## 1. System overview

The project is a **Natural Language → SQL** agent over a small PostgreSQL
movie database. A user asks a question in English; a LangGraph state machine
turns it into SQL, runs it, repairs it on failure, and turns the rows back
into an English answer.

```
User
  │
  ▼
Streamlit UI (app/streamlit_app.py)
  │  calls
  ▼
LangGraph workflow (agent/graph.py)
  │  analyze → schema → generate_sql → validate → execute → interpret
  │                                        ▲           │
  │                                        └── repair ◄┘  (on failure, ≤ N retries)
  │
  ├── llm/  → OpenRouter (OpenAI-compatible Chat API) for SQL generation,
  │           repair, and answer formatting
  └── db.py → SQLAlchemy engine → PostgreSQL (schema introspection,
              query execution)
```

Everything is wired through two shared singletons:
- `config.settings` ([config.py](../config.py)) — all environment-driven configuration.
- `db.get_engine()` ([db.py](../db.py)) — one cached SQLAlchemy `Engine`.

## 2. Repository layout

```
.
├── app/                # Streamlit UI (presentation layer)
├── agent/               # LangGraph workflow — the orchestration layer
│   └── nodes/           # one module per graph node
├── llm/                 # LLM client, prompts, and generation/repair chains
├── database/             # SQL DDL + seed data, loaded by Postgres on boot
├── evaluation/           # offline accuracy harness + fixed question set
├── tests/                 # pytest smoke tests (no live DB/LLM required)
├── config.py              # env-driven settings singleton
├── db.py                  # SQLAlchemy engine, schema introspection, query execution
├── docker-compose.yml     # single-service Postgres for local dev
├── requirements.txt       # Python dependencies
├── .env.example           # documents every environment variable
└── README.md
```

## 3. Configuration — [config.py](../config.py)

Loads `.env` via `python-dotenv` and exposes a single `settings` object used
everywhere else (`from config import settings`). Fields:

| Setting | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | Auth for OpenRouter's OpenAI-compatible API |
| `OPENROUTER_BASE_URL` | Defaults to `https://openrouter.ai/api/v1` |
| `LLM_MODEL` | Model slug, e.g. `meta-llama/llama-3.1-8b-instruct:free` |
| `OPENROUTER_APP_NAME` / `OPENROUTER_SITE_URL` | Sent as OpenRouter attribution headers |
| `DATABASE_URL` | SQLAlchemy connection string (`postgresql+psycopg2://...`) |
| `MAX_SQL_REPAIR_RETRIES` | Cap on the graph's repair loop (default `3`) |

`.env.example` documents each variable and its default; `.env` itself is
git-ignored.

## 4. Database layer

### 4.1 Schema — [database/schema.sql](../database/schema.sql)

8 tables, idempotent (drops in dependency order, then recreates):

- **Entities:** `movies`, `directors`, `actors`, `genres`, `ratings`
  (`ratings.movie_id → movies`, one-to-many so a movie can have several
  rating rows)
- **Junctions (many-to-many):** `movie_directors`, `movie_actors` (carries a
  `role` column), `movie_genres`
- Indexes on every junction/foreign-key column used by the evaluation
  question set's JOIN/GROUP BY-heavy queries.

```
directors ──< movie_directors >── movies ──< ratings
                                    │
actors    ──< movie_actors    >─────┤
                                    │
genres    ──< movie_genres    >─────┘
```

### 4.2 Seed data — [database/seed.sql](../database/seed.sql)

A curated, internally-consistent dataset of 50 real, well-known movies
(1972–2023): 29 directors, 121 actors (with per-movie `role`), 15 genres,
and one rating per movie (52 director-links, 146 cast-links, 136
genre-links). The junction-table inserts (`movie_directors`, `movie_actors`,
`movie_genres`, `ratings`) use name-based `SELECT ... JOIN` against
`movies`/`directors`/`actors`/`genres` rather than hardcoded `SERIAL` ids,
so the data can be edited or reordered without silently breaking a foreign
key. See [database/README.md](../database/README.md) for the full
breakdown.

### 4.3 Loading — [docker-compose.yml](../docker-compose.yml)

Single `db` service (`postgres:16`). `schema.sql` and `seed.sql` are bind-mounted
into `/docker-entrypoint-initdb.d/` as `01_schema.sql` / `02_seed.sql` —
Postgres's official image runs everything in that directory **alphabetically,
and only on first container boot** (i.e., only when the `pgdata` volume is
empty). To reload after editing the SQL you must `docker compose down -v`
(drops the volume) or run the files manually via `psql`.

### 4.4 Access — [db.py](../db.py)

- `get_engine()` — lazily creates and caches one SQLAlchemy `Engine`
  (`pool_pre_ping=True` so stale connections are detected and recycled).
- `get_schema_text()` — introspects the **live** database (via
  `sqlalchemy.inspect`) and renders `table(col type, col type, ...)` lines.
  This is what gets embedded into the LLM prompt, so the prompt always
  reflects the actual schema rather than a hand-maintained copy.
- `run_query(sql)` — executes a raw SQL string inside a connection context
  and returns rows as `list[dict]`. Any exception propagates to the caller
  (the `execute` node), which is how execution failures feed the repair loop.

## 5. Agent layer — [agent/](../agent)

### 5.1 State — [agent/state.py](../agent/state.py)

`AgentState` is a `TypedDict` (not a class with methods) — the entire
contract between graph nodes. Each node receives the full state and returns
a partial dict that LangGraph merges in. Fields:

| Field | Set by | Meaning |
|---|---|---|
| `question` | input / `analyze` | user's question (trimmed) |
| `schema` | `schema` | textual schema for the prompt |
| `generated_sql` | `generate_sql` / `repair` | current SQL candidate |
| `validation_result`, `validation_error` | `validate` | did static validation pass |
| `query_result`, `database_error` | `execute` | rows or the DB error string |
| `retry_count` | `repair` | repair attempts so far |
| `final_answer` | `interpret` | the natural-language response |

`new_state(question)` builds the initial state for a run.

### 5.2 Graph wiring — [agent/graph.py](../agent/graph.py)

Builds a `langgraph.graph.StateGraph(AgentState)` with 7 nodes:

```
START → analyze → schema → generate_sql → validate ─┬─ (valid) ──────────────► execute ─┬─ (success) ─► interpret → END
                                                      │                                   │
                                                      └─ (invalid, retries left) ─► repair│─ (error, retries left) ─┘
                                                                                     ▲     │
                                                                                     └─────┘ (repair always loops back to validate)
```

Concretely:
- `analyze → schema → generate_sql → validate` is a straight line.
- `_after_validate(state)`: `execute` if `validation_result` is true;
  otherwise `repair` if `retry_count < MAX_SQL_REPAIR_RETRIES`, else
  `interpret` (give up gracefully).
- `_after_execute(state)`: `interpret` if `database_error is None`;
  otherwise same retry-or-give-up logic as above.
- `repair` always routes back to `validate` (so a repaired query is
  re-validated before being executed again).
- `interpret_node` (defined inline in `graph.py`, not under `nodes/`) turns
  `query_result` into an answer via `llm.sql_generator.format_answer`, or —
  if the state has no result — builds an apology message that reports the
  last error and how many repairs were attempted.

`graph_app = build_graph()` is compiled **once at import time** and reused.
`answer_question(question)` is the core public entry point:
`graph_app.invoke(new_state(question))`, returning the full final `AgentState`.
Running `python -m agent.graph "<question>"` invokes this directly from the
CLI for manual testing; [evaluation/evaluate.py](../evaluation/evaluate.py)
also calls it directly.

Two more functions wrap `answer_question` for the UI without changing its
contract:
- `run_agent(question)` — shapes the final state into the flat
  `{sql, columns, rows, answer, attempts, error}` dict
  [app/streamlit_app.py](../app/streamlit_app.py) renders per turn, and
  never raises (any exception, e.g. a missing API key or unreachable
  database, is captured into `error` instead of propagating).
- `_credentials_available()` — a cheap presence check on
  `settings.OPENROUTER_API_KEY` / `settings.DATABASE_URL`, purely
  informational (drives the sidebar's "real agent active" vs. "not
  configured" badge). It does not gate `run_agent`.

### 5.3 Nodes — [agent/nodes/](../agent/nodes)

| File | Node | Responsibility |
|---|---|---|
| [analyze.py](../agent/nodes/analyze.py) | `analyze_node` | Trims the question. Currently a pass-through placeholder — a hook for future intent/entity classification. |
| [schema.py](../agent/nodes/schema.py) | `schema_node` | Calls `db.get_schema_text()` and stores it in state. |
| [generate_sql.py](../agent/nodes/generate_sql.py) | `generate_sql_node` | Calls `llm.sql_generator.generate_sql`; clears stale `validation_error`/`database_error` from any prior attempt. |
| [validate.py](../agent/nodes/validate.py) | `validate_node` | Static, no-DB-execution safety check (see §5.4). |
| [execute.py](../agent/nodes/execute.py) | `execute_node` | Runs the SQL via `db.run_query`; catches any exception into `database_error` rather than raising. |
| [repair.py](../agent/nodes/repair.py) | `repair_node` | Calls `llm.sql_generator.repair_sql` with the failing SQL + error, increments `retry_count`. |

### 5.4 Validation rules ([validate.py](../agent/nodes/validate.py))

Uses `sqlparse` (not a live DB call) to check, in order:
1. Non-empty SQL.
2. Exactly one statement (blocks multi-statement/SQL-injection-style payloads).
3. Statement type is `SELECT` (never INSERT/UPDATE/DELETE/DDL).
4. No forbidden keyword appears anywhere in the token stream — a second,
   belt-and-suspenders check against `INSERT, UPDATE, DELETE, DROP, ALTER,
   TRUNCATE, CREATE, GRANT, REVOKE, MERGE, REPLACE, CALL, COPY`.
5. Best-effort table-existence check: introspects known table names and
   flags the query only if **none** of its tokens match a real table (a
   strong signal the model hallucinated the schema). This is deliberately
   loose — flat token scanning can't distinguish a column/alias from a
   table name, so it only rejects the "references nothing real" case.

This is the only safety gate before SQL reaches the database — there's no
separate DB-level read-only role or statement timeout enforced at the
SQLAlchemy layer.

## 6. LLM layer — [llm/](../llm)

### 6.1 Client — [llm/model.py](../llm/model.py)

`get_llm(temperature=0.0, model=None)` returns a `langchain_openai.ChatOpenAI`
pointed at OpenRouter's OpenAI-compatible endpoint (`base_url` +
`api_key` from `settings`), with OpenRouter's attribution headers
(`HTTP-Referer`, `X-Title`) attached. Temperature defaults to `0` for
deterministic SQL generation; `format_answer` (below) overrides it to `0.2`
for more natural prose. The `model` override exists so different runs/experiments
can swap models without touching call sites.

### 6.2 Prompts — [llm/prompts.py](../llm/prompts.py)

Four templates, kept centralized so every model comparison uses identical
wording:
- `SQL_SYSTEM_PROMPT` — standing rules (SELECT-only, use only given
  columns, no markdown fences, prefer explicit JOINs).
- `SQL_GENERATION_PROMPT` — fills `{schema}`, `{relationships}`, `{question}`.
- `SQL_REPAIR_PROMPT` — fills schema/question plus the failing
  `{generated_sql}` and `{error}`.
- `ANSWER_PROMPT` — fills `{question}` and `{rows}` to produce the final
  prose answer.
- `RELATIONSHIPS` — a hand-written static description of the FK graph
  (movies/directors/actors/genres/ratings + junction tables), injected
  alongside the introspected schema so the model has explicit join hints
  that raw column types don't convey.

### 6.3 Chains — [llm/sql_generator.py](../llm/sql_generator.py)

Thin wrappers around `get_llm().invoke([...])`:
- `generate_sql(question, schema)` — system + generation prompt → `_clean_sql`.
- `repair_sql(question, schema, generated_sql, error)` — system + repair
  prompt → `_clean_sql`.
- `format_answer(question, rows)` — answer prompt only (no system prompt),
  temperature `0.2`.
- `_clean_sql(text)` — strips markdown code fences (```sql ... ```) and a
  trailing semicolon, since `validate_node` expects a single bare statement.

These functions are the seam between the `agent/nodes/` (orchestration) and
the actual model calls — nodes never call `ChatOpenAI` directly.

## 7. App layer — [app/streamlit_app.py](../app/streamlit_app.py)

Chat-style Streamlit UI. Per turn it renders: the question, the final
answer, the generated SQL (inside a collapsed expander, labeled with attempt
count), and a `pandas.DataFrame` of the result rows. A sidebar offers
example questions as one-click buttons and a "clear conversation" reset;
it also reports whether the "real" agent or a mock is active via
`_credentials_available()`.

The app imports `run_agent` and `_credentials_available` from `agent.graph`
(§5.2) rather than calling `answer_question` directly — `run_agent` wraps
`answer_question`, shapes the state into this flat dict, and never raises
(exceptions, e.g. a missing API key or unreachable database, are captured
into the `error` field instead of crashing the app). `_credentials_available`
is purely informational, driving the sidebar's real-agent/not-configured
badge; it does not change `run_agent`'s behavior.

## 8. Evaluation — [evaluation/](../evaluation)

- [questions.json](../evaluation/questions.json) — 38 fixed
  question/difficulty/category/expected-SQL/expected-result records (10
  basic, 10 relational, 9 aggregation, 9 complex), with every
  `expected_result` computed directly from the real seed data (§4.2) rather
  than estimated.
- [evaluate.py](../evaluation/evaluate.py) — runs `answer_question` over
  every question, then scores two independent metrics:
  - **`sql_valid`** — did execution complete without a `database_error` and
    produce rows.
  - **`execution_correct`** — a *loose, order-independent containment*
    check (`_is_execution_correct`): a single-value `expected_result` (a
    count, one name) must appear as a substring of the flattened,
    comma-joined result values; a comma-separated multi-item
    `expected_result` (e.g. a list of movie titles) is split into tokens and
    each token is checked independently, so a generated query that returns
    the right rows in a different order still scores correct. This
    intentionally tolerates SQL that's phrased differently from
    `expected_sql` but returns an equivalent answer — exact SQL match is
    not required or checked here.
  - Writes per-question rows plus a printed summary — overall, and broken
    down by `difficulty` and `category` — to `evaluation/results.csv`
    (git-ignored/generated, not checked in).

## 9. Tests — [tests/test_smoke.py](../tests/test_smoke.py)

Deliberately dependency-free (no live DB, no API key needed):
- `test_state_factory` — `new_state()` produces the expected defaults.
- `test_clean_sql_strips_fences` — `_clean_sql` correctly strips ` ```sql `
  fences and trailing semicolons.
- `test_validate_rejects_empty_sql` / `_non_select` / `_multiple_statements`
  and `test_validate_accepts_plain_select` — exercise the SELECT-only hard
  constraint (§5.4) directly. `validate_node`'s best-effort known-table
  check safely no-ops when Postgres is unreachable, so these run without a
  live database.

Run with `pytest -q`. There is currently no integration test that exercises
the full graph against a real Postgres instance or a live LLM.

## 10. End-to-end request flow

1. User submits a question in the Streamlit chat input.
2. UI calls into the agent entry point (`answer_question`, per the
   committed graph — see the known-issue note in §7 for the current
   uncommitted mismatch).
3. `analyze` trims the question.
4. `schema` introspects Postgres live and attaches the schema text.
5. `generate_sql` calls the LLM with system + generation prompts →
   candidate SQL.
6. `validate` statically checks the SQL (single SELECT statement, no
   forbidden keywords, references a real table).
   - Invalid + retries remain → `repair` → back to `validate`.
   - Invalid + retries exhausted → `interpret` (failure path).
7. `execute` runs the validated SQL against Postgres.
   - DB error + retries remain → `repair` → back to `validate`.
   - DB error + retries exhausted → `interpret` (failure path).
   - Success → `interpret`.
8. `interpret` either calls `format_answer` (LLM turns rows into prose) or
   builds an apology string citing the last error and retry count.
9. UI renders the answer, the SQL used, and the result table.
