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

        # Loose containment check; refine per question type as needed.
        execution_correct = bool(
            sql_valid and expected and expected.lower() in result_text.lower()
        )

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
    print(f"Results written to : {RESULTS_PATH}")
    return df


if __name__ == "__main__":
    evaluate()
