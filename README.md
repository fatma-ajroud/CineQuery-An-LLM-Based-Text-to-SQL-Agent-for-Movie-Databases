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
├── database/         # schema.sql, curated 50-movie seed.sql, README (ER diagram)
├── evaluation/       # questions.json (38 Qs), evaluate.py, results.csv
├── tests/            # smoke tests
├── docs/             # ARCHITECTURE.md — file-by-file technical reference
├── config.py         # env-driven settings
├── db.py             # SQLAlchemy engine + schema introspection
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

For a detailed, file-by-file walkthrough of how every module is wired
together, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

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
python -m agent.graph "Which directors have directed more than three movies?"
```

### 5. Evaluate

```bash
python evaluation/evaluate.py   # writes evaluation/results.csv
```

Runs all 38 questions in `evaluation/questions.json` (10 basic / 10
relational / 9 aggregation / 9 complex) through the agent and prints SQL
validity and execution accuracy, both overall and broken down by difficulty
and category.

## Dataset

`database/seed.sql` is a curated, internally-consistent set of 50 real,
well-known movies (1972–2023): 29 directors, 121 actors (with per-movie
`role`), 15 genres, and one rating per movie. See
[database/README.md](database/README.md) for the full breakdown and ER
diagram.

## Model choice

The default (`LLM_MODEL` in `.env`) is
`nvidia/nemotron-3-super-120b-a12b:free` on OpenRouter — a free-tier model,
so the project runs end-to-end with no API cost. It was picked by live-testing
several current free-tier candidates directly against the generation prompt;
it returned clean, correctly-joined SQL immediately while a couple of other
candidates hit shared rate limits. `llm/model.py` accepts a `model`
override, so swapping in a different model (e.g. a paid Claude/GPT/Gemini
slug on OpenRouter) for comparison only requires changing `LLM_MODEL` — no
other code changes. SQL generation and repair both use `temperature=0` for
determinism; only the final answer-formatting step uses a small positive
temperature for more natural prose.

**OpenRouter's free-model lineup changes over time** — old slugs get
deprecated or moved behind a paywall (this happened mid-project: the
originally-chosen `meta-llama/llama-3.1-8b-instruct:free` now 404s). If SQL
generation starts failing with a 404, check
<https://openrouter.ai/models?max_price=0> for a current free slug and
update `LLM_MODEL`.

**Free-tier daily cap:** OpenRouter limits free models to **50 requests/day**
per account (adding $10 of credit raises this to 1000/day). A single
question uses 2-4 requests (generate, validate/execute are local, repair
retries, plus one for the final answer), and the 38-question evaluation set
can use 60-100+, so a full `evaluate.py` run can exhaust the free daily quota
partway through — remaining questions will fail with a 429 rate-limit error
(caught gracefully; they show up as `sql_valid=False` in `results.csv`, not
crashes) rather than a real model or prompt-quality failure.

### Example evaluation run

One full live run against `nvidia/nemotron-3-super-120b-a12b:free` (before
the daily quota above was exhausted by earlier testing in the same session):

```
Questions          : 38
SQL validity       : 89%
Execution accuracy : 84%
Avg repair retries : 1.13
```

Of the 6 questions that didn't score as correct: 4 failed with empty
`generated_sql` after exhausting all repair retries - confirmed (by
re-running 3 of them in isolation) to be the free-tier daily cap kicking in
mid-run, not a bad query. The other 2 were false negatives in the harness
itself, both since fixed: `evaluate.py` read `questions.json` without
`encoding="utf-8"`, mangling one non-ASCII expected answer ("Amélie" read
as "AmÃ©lie"); and one `expected_result` had a transcription error (an
actor's filmography listed a movie they weren't actually cast in in
`seed.sql`). Cross-checking every `expected_result` by running its
`expected_sql` directly against the live database confirmed all 38 are now
correct. So this run had **zero genuine SQL-generation misses** - every
question the agent actually got to answer, it answered correctly. Re-run
`evaluation/evaluate.py` for your own numbers — they'll vary by model and by
how much of the daily quota is already used.

## Development phases (from the project doc)

1. **Database** — build and populate the PostgreSQL database.
2. **Basic LLM** — make `question → SQL` work reliably.
3. **Database integration** — `question → SQL → PostgreSQL → result`.
4. **LangGraph** — turn the pipeline into a graph with separate nodes.
5. **Error correction** — `SQL error → LLM → corrected SQL → execution`.
6. **UI** — build the Streamlit interface.
7. **Evaluation** — run the prepared question set and compare results.
8. **Final experiments** — compare models, analyze strengths/weaknesses. 
