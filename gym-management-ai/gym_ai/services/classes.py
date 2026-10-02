"""Group classes (yoga, spinning ...), bookings, waitlists and cancellations."""
from gym_ai.database import get_connection
from gym_ai.services.members import _fetch_member
from gym_ai.utils import GymError, now_str


def add_class(name: str, weekday: str, start_time: str, capacity: int,
              trainer_id: int | None = None) -> dict:
    if capacity <= 0:
        raise GymError("Capacity must be at least 1.")
    with get_connection() as conn:
        if trainer_id is not None and not conn.execute("SELECT 1 FROM staff WHERE id = ?", (trainer_id,)).fetchone():
            raise GymError(f"Trainer (staff) {trainer_id} not found.")
        cur = conn.execute(
            "INSERT INTO classes (name, trainer_id, weekday, start_time, capacity) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), trainer_id, weekday.strip().title(), start_time, capacity),
        )
        return _get_class(conn, cur.lastrowid)


def _get_class(conn, class_id: int) -> dict:
    row = conn.execute(
        """SELECT c.*, s.name AS trainer_name FROM classes c
           LEFT JOIN staff s ON s.id = c.trainer_id WHERE c.id = ?""",
        (class_id,),
    ).fetchone()
    if row is None:
        raise GymError(f"Class {class_id} not found.")
    return dict(row)


def list_classes() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT c.*, s.name AS trainer_name FROM classes c
               LEFT JOIN staff s ON s.id = c.trainer_id ORDER BY c.weekday, c.start_time"""
        ).fetchall()
    return [dict(r) for r in rows]


def book_class(class_id: int, member_id: int, class_date: str) -> dict:
    """Book a seat. If the class is full the member goes on the waitlist."""
    with get_connection() as conn:
        gym_class = _get_class(conn, class_id)
        member = _fetch_member(conn, member_id)
        if member["membership_state"] != "active":
            raise GymError(f"{member['name']} needs an active membership to book classes.")

        taken = conn.execute(
            "SELECT COUNT(*) AS n FROM bookings WHERE class_id = ? AND class_date = ? AND status = 'confirmed'",
            (class_id, class_date),
        ).fetchone()["n"]
        status = "confirmed" if taken < gym_class["capacity"] else "waitlist"

        existing = conn.execute(
            "SELECT id, status FROM bookings WHERE class_id = ? AND member_id = ? AND class_date = ?",
            (class_id, member_id, class_date),
        ).fetchone()
        if existing and existing["status"] != "cancelled":
            raise GymError(f"{member['name']} is already {existing['status']} for this class on {class_date}.")
        if existing:  # re-booking after a cancellation
            conn.execute("UPDATE bookings SET status = ?, booked_at = ? WHERE id = ?",
                         (status, now_str(), existing["id"]))
        else:
            conn.execute(
                "INSERT INTO bookings (class_id, member_id, class_date, status, booked_at) VALUES (?, ?, ?, ?, ?)",
                (class_id, member_id, class_date, status, now_str()),
            )
    return {"class": gym_class["name"], "class_date": class_date, "member_name": member["name"],
            "status": status,
            "message": "Seat confirmed." if status == "confirmed" else "Class is full - added to the waitlist."}


def cancel_booking(class_id: int, member_id: int, class_date: str) -> dict:
    """Cancel a booking. The first person on the waitlist (if any) gets the seat."""
    with get_connection() as conn:
        booking = conn.execute(
            "SELECT id, status FROM bookings WHERE class_id = ? AND member_id = ? AND class_date = ?",
            (class_id, member_id, class_date),
        ).fetchone()
        if booking is None or booking["status"] == "cancelled":
            raise GymError("No active booking found for that member, class and date.")
        conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking["id"],))

        promoted = None
        if booking["status"] == "confirmed":
            nxt = conn.execute(
                """SELECT b.id, b.member_id, m.name FROM bookings b JOIN members m ON m.id = b.member_id
                   WHERE b.class_id = ? AND b.class_date = ? AND b.status = 'waitlist'
                   ORDER BY b.booked_at, b.id LIMIT 1""",
                (class_id, class_date),
            ).fetchone()
            if nxt:
                conn.execute("UPDATE bookings SET status = 'confirmed' WHERE id = ?", (nxt["id"],))
                promoted = {"member_id": nxt["member_id"], "member_name": nxt["name"]}
    return {"cancelled": True, "promoted_from_waitlist": promoted}


def class_roster(class_id: int, class_date: str) -> dict:
    with get_connection() as conn:
        gym_class = _get_class(conn, class_id)
        rows = conn.execute(
            """SELECT m.id AS member_id, m.name, b.status FROM bookings b
               JOIN members m ON m.id = b.member_id
               WHERE b.class_id = ? AND b.class_date = ? AND b.status != 'cancelled'
               ORDER BY b.status, b.booked_at""",
            (class_id, class_date),
        ).fetchall()
    return {"class": gym_class["name"], "date": class_date, "capacity": gym_class["capacity"],
            "bookings": [dict(r) for r in rows]}
