# Database

PostgreSQL database for the Movie Text-to-SQL agent. Small but relationally
rich: ~50 movies distributed across normalized tables so the LLM has real
relationships to reason over.

## Schema

| Table             | Purpose                                            |
|-------------------|----------------------------------------------------|
| `movies`          | Core movie entity (title, release_year, runtime, language) |
| `directors`       | Director entity                                    |
| `actors`          | Actor entity                                       |
| `genres`          | Genre entity                                       |
| `ratings`         | One or more rating rows per movie                  |
| `movie_directors` | Junction: movies ↔ directors                       |
| `movie_actors`    | Junction: movies ↔ actors (with `role`)            |
| `movie_genres`    | Junction: movies ↔ genres                          |

### ER overview

```
directors ──< movie_directors >── movies ──< ratings
                                    │
actors    ──< movie_actors    >─────┤
                                    │
genres    ──< movie_genres    >─────┘
```

(`──<` = one-to-many toward the junction table.)

## Files

- `schema.sql` — table definitions, keys, and indexes. Idempotent.
- `seed.sql` — **starter** sample data (7 movies) so the pipeline runs
  end-to-end. Replace/extend with the curated ~50-movie dataset.
- These two run automatically, in order, when the Postgres container boots
  for the first time (mounted into `/docker-entrypoint-initdb.d/`).

## Running locally

From the repo root:

```bash
docker compose up -d db          # boots Postgres, runs schema.sql then seed.sql
```

Re-apply the SQL manually (e.g. after editing the seed) without recreating
the volume:

```bash
docker compose exec -T db psql -U movies -d moviesdb < database/schema.sql
docker compose exec -T db psql -U movies -d moviesdb < database/seed.sql
```

Wipe and start clean:

```bash
docker compose down -v && docker compose up -d db
```

## Target dataset size (from project doc)

~50 movies · 20–30 directors · 80–120 actors · 10–15 genres ·
50 rating records · plus junction rows. Exact numbers can be adjusted
during data preparation.
