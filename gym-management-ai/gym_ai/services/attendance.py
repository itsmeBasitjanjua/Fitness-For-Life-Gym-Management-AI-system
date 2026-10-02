"""Member check-ins. Entry is only allowed with a valid (paid) membership."""
from gym_ai.database import get_connection
from gym_ai.services.members import _fetch_member
from gym_ai.utils import now_str, today_str


def check_in(member_id: int) -> dict:
    with get_connection() as conn:
        member = _fetch_member(conn, member_id)
        state = member["membership_state"]
        if state != "active":
            reasons = {
                "inactive": "member is inactive",
                "no_payment_yet": "no payment has been made yet",
                "expired": f"membership expired on {member['membership_expiry']}",
            }
            return {"allowed": False, "member_name": member["name"],
                    "message": f"Entry denied: {reasons[state]}."}

        today = today_str()
        existing = conn.execute(
            "SELECT check_in FROM attendance WHERE member_id = ? AND substr(check_in, 1, 10) = ?",
            (member_id, today),
        ).fetchone()
        if existing:
            return {"allowed": True, "member_name": member["name"],
                    "message": f"Already checked in today at {existing['check_in'][11:16]}."}

        stamp = now_str()
        conn.execute("INSERT INTO attendance (member_id, check_in) VALUES (?, ?)", (member_id, stamp))
        return {"allowed": True, "member_name": member["name"], "check_in": stamp,
                "message": f"Welcome {member['name']}! Membership valid until {member['membership_expiry']}."}


def attendance_on(date: str | None = None) -> list[dict]:
    """Who visited on a given date (default: today)."""
    date = date or today_str()
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT m.id AS member_id, m.name, a.check_in FROM attendance a
               JOIN members m ON m.id = a.member_id
               WHERE substr(a.check_in, 1, 10) = ? ORDER BY a.check_in""",
            (date,),
        ).fetchall()
    return [dict(r) for r in rows]


def member_attendance(member_id: int, limit: int = 30) -> dict:
    with get_connection() as conn:
        member = _fetch_member(conn, member_id)
        rows = conn.execute(
            "SELECT check_in FROM attendance WHERE member_id = ? ORDER BY check_in DESC LIMIT ?",
            (member_id, limit),
        ).fetchall()
        month_visits = conn.execute(
            "SELECT COUNT(*) AS n FROM attendance WHERE member_id = ? AND substr(check_in, 1, 7) = ?",
            (member_id, today_str()[:7]),
        ).fetchone()["n"]
    return {"member_name": member["name"], "visits_this_month": month_visits,
            "recent_check_ins": [r["check_in"] for r in rows]}
