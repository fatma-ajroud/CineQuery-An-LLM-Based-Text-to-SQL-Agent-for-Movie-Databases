"""Evaluation harness (Member 4).

Runs the agent over evaluation/questions.json and measures:
  - SQL validity      : did the agent produce executable SQL?
  - execution accuracy : did the result match the expected result?

Writes evaluation/results.csv. Execution accuracy is treated as more
important than exact SQL match (many queries produce the same result).

Run:  python evaluation/evaluate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as a script from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from agent.graph import answer_question

HERE = Path(__file__).resolve().parent
QUESTIONS_PATH = HERE / "questions.json"
RESULTS_PATH = HERE / "results.csv"


def _result_to_text(rows) -> str:
    if not rows:
        return ""
    # Flatten every value in every row into a single comparable string.
    vals = [str(v) for row in rows for v in row.values()]
    return ", ".join(vals)


def _is_execution_correct(expected: str, result_text: str) -> bool:
    """Loose, order-independent containment check.

    A single-value expectation (e.g. a count or one name) just needs to
    appear as a substring. A comma-separated multi-item expectation (e.g.
    a list of movie titles) is split into tokens and each token is checked
    independently, since the SQL the LLM writes is free to return matching
    rows in a different order than `expected_result` was written in.
    """
    if not expected or not result_text:
        return False
    tokens = [t.strip() for t in expected.split(",") if t.strip()]
    if len(tokens) <= 1:
        return expected.lower() in result_text.lower()
    result_lower = result_text.lower()
    return all(tok.lower() in result_lower for tok in tokens)


def evaluate() -> pd.DataFrame:
    questions = json.loads(QUESTIONS_PATH.read_text())
    records = []

    for item in questions:
        q = item["question"]
        state = answer_question(q)

        generated_sql = state.get("generated_sql", "")
        rows = state.get("query_result")
        db_error = state.get("database_error")

        sql_valid = rows is not None and db_error is None
        result_text = _result_to_text(rows)
        expected = str(item.get("expected_result", "")).strip()

        execution_correct = bool(sql_valid and _is_execution_correct(expected, result_text))

        records.append({
            "question": q,
            "difficulty": item.get("difficulty"),
            "category": item.get("category"),
            "generated_sql": generated_sql,
            "sql_valid": sql_valid,
            "execution_correct": execution_correct,
            "retry_count": state.get("retry_count", 0),
            "result": result_text,
            "expected_result": expected,
        })

    df = pd.DataFrame(records)
    df.to_csv(RESULTS_PATH, index=False)

    total = len(df)
    print(f"Questions          : {total}")
    if total:
        print(f"SQL validity       : {df['sql_valid'].mean():.0%}")
        print(f"Execution accuracy : {df['execution_correct'].mean():.0%}")
        print(f"Avg repair retries : {df['retry_count'].mean():.2f}")

        print("\nBy difficulty:")
        by_difficulty = df.groupby("difficulty").agg(
            n=("question", "count"),
            sql_valid=("sql_valid", "mean"),
            execution_correct=("execution_correct", "mean"),
        )
        print(by_difficulty.to_string(float_format=lambda v: f"{v:.0%}"))

        print("\nBy category:")
        by_category = df.groupby("category").agg(
            n=("question", "count"),
            sql_valid=("sql_valid", "mean"),
            execution_correct=("execution_correct", "mean"),
        )
        print(by_category.to_string(float_format=lambda v: f"{v:.0%}"))
    print(f"\nResults written to : {RESULTS_PATH}")
    return df


if __name__ == "__main__":
    evaluate()
