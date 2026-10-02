"""Gym equipment, faults and maintenance schedule."""
from gym_ai.database import get_connection
from gym_ai.utils import GymError, today_str

VALID_STATUS = ("working", "faulty", "under_maintenance")


def add_equipment(name: str, next_service: str | None = None) -> dict:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO equipment (name, last_service, next_service) VALUES (?, ?, ?)",
            (name.strip(), today_str(), next_service),
        )
        return dict(conn.execute("SELECT * FROM equipment WHERE id = ?", (cur.lastrowid,)).fetchone())


def list_equipment(status: str | None = None) -> list[dict]:
    sql, params = "SELECT * FROM equipment", ()
    if status:
        sql, params = sql + " WHERE status = ?", (status,)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql + " ORDER BY id", params)]


def _update(equipment_id: int, status: str, note: str | None, serviced: bool = False,
            next_service: str | None = None) -> dict:
    if status not in VALID_STATUS:
        raise GymError(f"Status must be one of {VALID_STATUS}.")
    with get_connection() as conn:
        if not conn.execute("SELECT 1 FROM equipment WHERE id = ?", (equipment_id,)).fetchone():
            raise GymError(f"Equipment {equipment_id} not found.")
        conn.execute("UPDATE equipment SET status = ?, notes = COALESCE(?, notes) WHERE id = ?",
                     (status, note, equipment_id))
        if serviced:
            conn.execute("UPDATE equipment SET last_service = ?, next_service = ? WHERE id = ?",
                         (today_str(), next_service, equipment_id))
        return dict(conn.execute("SELECT * FROM equipment WHERE id = ?", (equipment_id,)).fetchone())


def report_fault(equipment_id: int, note: str) -> dict:
    return _update(equipment_id, "faulty", note)


def mark_serviced(equipment_id: int, next_service: str | None = None) -> dict:
    return _update(equipment_id, "working", "Serviced", serviced=True, next_service=next_service)
