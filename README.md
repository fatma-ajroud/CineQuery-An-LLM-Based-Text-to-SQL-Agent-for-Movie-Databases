# Movie Text-to-SQL AI Agent

An AI-powered **Natural Language → SQL** system for a movie database. Ask a
question in plain language and the agent generates, validates, executes, and
(if needed) repairs a PostgreSQL query, then returns a natural-language answer.

> Central question: *How effectively can an LLM, orchestrated through
> LangGraph, translate natural-language questions into correct SQL over a
> relational movie database, and recover from SQL-generation errors?*

## How it works

```
User → Streamlit UI → LangGraph workflow → OpenRouter LLM
     → SQL validation → PostgreSQL → result interpreter → answer
```

The LangGraph agent runs these nodes: **analyze → schema → generate_sql →
validate → execute**, with a **repair** loop (≤ 3 retries) whenever validation
or execution fails, and a final **interpret** step that turns rows into a
sentence.

## Tech stack

- **LLM / orchestration:** Python, LangChain, LangGraph, OpenRouter (a free /
  low-cost hosted model — no large local model required)
- **Database:** PostgreSQL, SQLAlchemy
- **App:** Streamlit (optional FastAPI layer)
- **Dev:** Git + GitHub, Docker Compose

## Repository layout

```
movie-text-to-sql/
├── app/              # Streamlit UI
│   └── streamlit_app.py
├── agent/            # LangGraph workflow (core agent architecture)
│   ├── state.py      # shared graph state
│   ├── graph.py      # nodes wired together + repair routing
│   └── nodes/        # analyze, schema, generate_sql, validate, execute, repair
├── llm/              # OpenRouter model, prompts, SQL generation/repair chains
│   ├── model.py
│   ├── prompts.py
│   └── sql_generator.py
├── database/         # schema.sql, seed.sql, README (ER diagram)
├── evaluation/       # questions.json, evaluate.py, results.csv
├── tests/            # smoke tests
├── config.py         # env-driven settings
├── db.py             # SQLAlchemy engine + schema introspection
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Quick start

### 1. Clone and install

```bash
git clone <your-repo-url>
cd movie-text-to-sql
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# edit .env: add your OPENROUTER_API_KEY and (optionally) pick LLM_MODEL
```

Get a key at <https://openrouter.ai/keys>.

### 3. Start PostgreSQL (loads schema + seed automatically)

```bash
docker compose up -d db
```

### 4. Run the app

```bash
streamlit run app/streamlit_app.py
```

Or run one question from the command line:

```bash
python -m agent.graph "Which directors have the highest average movie rating?"
```

### 5. Evaluate

```bash
python evaluation/evaluate.py   # writes evaluation/results.csv
```

## Development phases (from the project doc)

1. **Database** — build and populate the PostgreSQL database.
2. **Basic LLM** — make `question → SQL` work reliably.
3. **Database integration** — `question → SQL → PostgreSQL → result`.
4. **LangGraph** — turn the pipeline into a graph with separate nodes.
5. **Error correction** — `SQL error → LLM → corrected SQL → execution`.
6. **UI** — build the Streamlit interface.
7. **Evaluation** — run the prepared question set and compare results.
8. **Final experiments** — compare models, analyze strengths/weaknesses.

## Team division

| Member | Area | Owns |
|--------|------|------|
| 1 | Database & Data Engineering | `database/` (schema, seed, ER diagram) |
| 2 | LLM & LangChain | `llm/` (model, prompts, sql_generator) |
| 3 | LangGraph & SQL Agent | `agent/` (state, graph, nodes) |
| 4 | Application, Evaluation & Testing | `app/`, `evaluation/`, `tests/` |

Shared: repo organization, architecture decisions, dataset/question design,
integration, final report & presentation. Define interfaces early — don't
develop components fully independently until the last week.

## Notes

- The initial system is restricted to **SELECT** queries only (validated in
  `agent/nodes/validate.py`).
- `database/seed.sql` currently holds a small illustrative sample so the
  pipeline runs end-to-end; Member 1 replaces it with the curated ~50-movie
  dataset.
- Secrets live in `.env` (git-ignored). Never commit real API keys.
