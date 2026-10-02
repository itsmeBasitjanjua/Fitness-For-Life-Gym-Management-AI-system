"""Sales leads: people who asked about joining but are not members yet."""
from gym_ai.database import get_connection
from gym_ai.utils import GymError, now_str

VALID_STATUS = ("new", "contacted", "trial", "joined", "lost")


def add_lead(name: str, phone: str, source: str | None = None, notes: str | None = None) -> dict:
    if not name.strip() or not phone.strip():
        raise GymError("Lead name and phone are required.")
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO leads (name, phone, source, notes, created_at) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), phone.strip(), source, notes, now_str()),
        )
        return dict(conn.execute("SELECT * FROM leads WHERE id = ?", (cur.lastrowid,)).fetchone())


def list_leads(status: str | None = None) -> list[dict]:
    sql, params = "SELECT * FROM leads", ()
    if status:
        sql, params = sql + " WHERE status = ?", (status,)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql + " ORDER BY created_at DESC", params)]


def update_lead_status(lead_id: int, status: str, notes: str | None = None) -> dict:
    if status not in VALID_STATUS:
        raise GymError(f"Status must be one of {VALID_STATUS}.")
    with get_connection() as conn:
        if not conn.execute("SELECT 1 FROM leads WHERE id = ?", (lead_id,)).fetchone():
            raise GymError(f"Lead {lead_id} not found.")
        conn.execute("UPDATE leads SET status = ?, notes = COALESCE(?, notes) WHERE id = ?",
                     (status, notes, lead_id))
        return dict(conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone())
