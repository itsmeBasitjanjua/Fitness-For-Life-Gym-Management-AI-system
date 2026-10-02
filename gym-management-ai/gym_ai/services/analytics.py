"""
Read-only SQL for the analytics agent ("how many members joined in September?").

Two safety layers stop the AI from changing data:
  1. only a single SELECT statement is accepted
  2. the connection itself is opened read-only
"""
import re

from gym_ai.database import SCHEMA, get_readonly_connection
from gym_ai.utils import GymError

MAX_ROWS = 100
_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum)\b", re.I)


def run_read_only_query(sql: str) -> dict:
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned.lower().startswith(("select", "with")):
        raise GymError("Only SELECT queries are allowed.")
    if ";" in cleaned:
        raise GymError("Run one statement at a time.")
    if _FORBIDDEN.search(cleaned):
        raise GymError("That query contains a keyword that is not allowed.")

    conn = get_readonly_connection()
    try:
        rows = conn.execute(cleaned).fetchmany(MAX_ROWS + 1)
    except Exception as exc:  # bad SQL -> tell the AI so it can fix the query
        raise GymError(f"SQL error: {exc}")
    finally:
        conn.close()

    truncated = len(rows) > MAX_ROWS
    return {"rows": [dict(r) for r in rows[:MAX_ROWS]], "truncated": truncated}


def database_schema() -> str:
    """The CREATE TABLE statements, so the AI knows table and column names."""
    return SCHEMA
