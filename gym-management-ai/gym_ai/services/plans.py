"""Membership plans (Monthly, Quarterly, Yearly ...)."""
import sqlite3

from gym_ai.database import get_connection
from gym_ai.utils import GymError


def add_plan(name: str, duration_days: int, fee: float) -> dict:
    if duration_days <= 0 or fee <= 0:
        raise GymError("Duration and fee must both be greater than zero.")
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO plans (name, duration_days, fee) VALUES (?, ?, ?)",
                (name.strip(), duration_days, fee),
            )
            return get_plan(cur.lastrowid, conn)
    except sqlite3.IntegrityError:
        raise GymError(f"A plan named '{name}' already exists.")


def get_plan(plan_id: int, conn=None) -> dict:
    def _fetch(c):
        row = c.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if row is None:
            raise GymError(f"Plan {plan_id} not found.")
        return dict(row)

    if conn is not None:
        return _fetch(conn)
    with get_connection() as c:
        return _fetch(c)


def list_plans() -> list[dict]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM plans ORDER BY duration_days")]
