"""Member progress tracking: weight, body fat and notes over time."""
from gym_ai.database import get_connection
from gym_ai.services.members import _fetch_member
from gym_ai.utils import GymError, now_str


def log_progress(member_id: int, weight_kg: float | None = None,
                 body_fat_pct: float | None = None, note: str | None = None) -> dict:
    if weight_kg is None and body_fat_pct is None and not note:
        raise GymError("Give at least a weight, body-fat % or a note.")
    with get_connection() as conn:
        member = _fetch_member(conn, member_id)
        conn.execute(
            "INSERT INTO progress (member_id, logged_at, weight_kg, body_fat_pct, note) VALUES (?, ?, ?, ?, ?)",
            (member_id, now_str(), weight_kg, body_fat_pct, note),
        )
        if weight_kg is not None:  # keep the member profile up to date
            conn.execute("UPDATE members SET weight_kg = ? WHERE id = ?", (weight_kg, member_id))
    return {"member_name": member["name"], "logged": True}


def get_progress(member_id: int, limit: int = 12) -> dict:
    with get_connection() as conn:
        member = _fetch_member(conn, member_id)
        rows = conn.execute(
            "SELECT logged_at, weight_kg, body_fat_pct, note FROM progress "
            "WHERE member_id = ? ORDER BY logged_at DESC LIMIT ?",
            (member_id, limit),
        ).fetchall()
    entries = [dict(r) for r in rows]
    weights = [e["weight_kg"] for e in reversed(entries) if e["weight_kg"] is not None]
    change = round(weights[-1] - weights[0], 1) if len(weights) >= 2 else None
    return {"member_name": member["name"], "entries": entries, "weight_change_kg": change}
