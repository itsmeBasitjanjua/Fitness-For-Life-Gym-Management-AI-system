"""Member registration, profiles and search."""
from gym_ai.database import get_connection
from gym_ai.utils import GymError, today_str

# Only these columns may be changed through update_member (safety whitelist).
UPDATABLE_FIELDS = {
    "name", "phone", "email", "gender", "age", "height_cm",
    "weight_kg", "goal", "fitness_level", "plan_id",
}


def membership_state(row: dict) -> str:
    """
    Describe a member's membership in one word:
      inactive         - member was deactivated
      no_payment_yet   - registered but never paid
      active           - paid up, expiry is today or later
      expired          - expiry date has passed
    """
    if row["status"] != "active":
        return "inactive"
    if not row["membership_expiry"]:
        return "no_payment_yet"
    return "active" if row["membership_expiry"] >= today_str() else "expired"


def _decorate(row) -> dict:
    data = dict(row)
    data["membership_state"] = membership_state(data)
    return data


def add_member(name, phone, plan_id=None, email=None, gender=None, age=None,
               height_cm=None, weight_kg=None, goal=None, fitness_level=None) -> dict:
    if not name or not name.strip():
        raise GymError("Member name is required.")
    if not phone or not phone.strip():
        raise GymError("Member phone number is required.")

    with get_connection() as conn:
        duplicate = conn.execute("SELECT id FROM members WHERE phone = ?", (phone.strip(),)).fetchone()
        if duplicate:
            raise GymError(f"A member with phone {phone} already exists (ID {duplicate['id']}).")
        if plan_id is not None and not conn.execute("SELECT 1 FROM plans WHERE id = ?", (plan_id,)).fetchone():
            raise GymError(f"Plan {plan_id} not found.")

        cur = conn.execute(
            """INSERT INTO members (name, phone, email, gender, age, height_cm, weight_kg,
                                    goal, fitness_level, plan_id, join_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name.strip(), phone.strip(), email, gender, age, height_cm, weight_kg,
             goal, fitness_level, plan_id, today_str()),
        )
        return _fetch_member(conn, cur.lastrowid)


def _fetch_member(conn, member_id: int) -> dict:
    row = conn.execute(
        """SELECT m.*, p.name AS plan_name, p.fee AS plan_fee, p.duration_days
           FROM members m LEFT JOIN plans p ON p.id = m.plan_id WHERE m.id = ?""",
        (member_id,),
    ).fetchone()
    if row is None:
        raise GymError(f"Member {member_id} not found.")
    return _decorate(row)


def get_member(member_id: int) -> dict:
    with get_connection() as conn:
        return _fetch_member(conn, member_id)


def search_members(query: str) -> list[dict]:
    """Find members by part of their name or phone number."""
    like = f"%{query.strip()}%"
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT m.*, p.name AS plan_name, p.fee AS plan_fee
               FROM members m LEFT JOIN plans p ON p.id = m.plan_id
               WHERE m.name LIKE ? OR m.phone LIKE ? ORDER BY m.name LIMIT 25""",
            (like, like),
        ).fetchall()
    return [_decorate(r) for r in rows]


def list_members(status: str | None = None) -> list[dict]:
    """All members, optionally filtered by status ('active' or 'inactive')."""
    sql = """SELECT m.*, p.name AS plan_name, p.fee AS plan_fee
             FROM members m LEFT JOIN plans p ON p.id = m.plan_id"""
    params: tuple = ()
    if status:
        sql += " WHERE m.status = ?"
        params = (status,)
    with get_connection() as conn:
        return [_decorate(r) for r in conn.execute(sql + " ORDER BY m.id", params)]


def update_member(member_id: int, **fields) -> dict:
    changes = {k: v for k, v in fields.items() if v is not None}
    unknown = set(changes) - UPDATABLE_FIELDS
    if unknown:
        raise GymError(f"Cannot update: {', '.join(sorted(unknown))}.")
    if not changes:
        raise GymError("Nothing to update - give at least one field.")
    with get_connection() as conn:
        _fetch_member(conn, member_id)  # makes sure the member exists
        assignments = ", ".join(f"{col} = ?" for col in changes)
        conn.execute(f"UPDATE members SET {assignments} WHERE id = ?", (*changes.values(), member_id))
        return _fetch_member(conn, member_id)


def set_member_status(member_id: int, status: str) -> dict:
    if status not in ("active", "inactive"):
        raise GymError("Status must be 'active' or 'inactive'.")
    with get_connection() as conn:
        _fetch_member(conn, member_id)
        conn.execute("UPDATE members SET status = ? WHERE id = ?", (status, member_id))
        return _fetch_member(conn, member_id)
