"""Gym running costs: rent, electricity, equipment, repairs, supplements ..."""
from gym_ai.database import get_connection
from gym_ai.utils import now_str, positive_amount, GymError, validate_month


def add_expense(category: str, amount: float, description: str | None = None,
                spent_at: str | None = None) -> dict:
    if not category or not category.strip():
        raise GymError("Expense category is required (e.g. Rent, Electricity, Equipment).")
    amount = positive_amount(amount)
    spent_at = spent_at or now_str()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (category, description, amount, spent_at) VALUES (?, ?, ?, ?)",
            (category.strip().title(), description, amount, spent_at),
        )
    return {"id": cur.lastrowid, "category": category.strip().title(), "description": description,
            "amount": amount, "spent_at": spent_at}


def list_expenses(month: str | None = None) -> list[dict]:
    month = validate_month(month)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, category, description, amount, spent_at FROM expenses "
            "WHERE substr(spent_at, 1, 7) = ? ORDER BY spent_at",
            (month,),
        ).fetchall()
    return [dict(r) for r in rows]


def expense_summary(month: str | None = None) -> dict:
    month = validate_month(month)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE substr(spent_at, 1, 7) = ? GROUP BY category ORDER BY total DESC",
            (month,),
        ).fetchall()
    by_category = [dict(r) for r in rows]
    return {"month": month, "total": sum(r["total"] for r in by_category), "by_category": by_category}
