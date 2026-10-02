"""Gym staff and their monthly salaries."""
from gym_ai.database import get_connection
from gym_ai.utils import (GymError, normalize_method, now_str, positive_amount,
                          today_str, validate_month)


def add_staff(name: str, role: str, monthly_salary: float, phone: str | None = None) -> dict:
    if not name.strip() or not role.strip():
        raise GymError("Staff name and role are required.")
    monthly_salary = positive_amount(monthly_salary)
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO staff (name, role, phone, monthly_salary, join_date) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), role.strip(), phone, monthly_salary, today_str()),
        )
        return get_staff(cur.lastrowid, conn)


def get_staff(staff_id: int, conn=None) -> dict:
    def _fetch(c):
        row = c.execute("SELECT * FROM staff WHERE id = ?", (staff_id,)).fetchone()
        if row is None:
            raise GymError(f"Staff member {staff_id} not found.")
        return dict(row)

    if conn is not None:
        return _fetch(conn)
    with get_connection() as c:
        return _fetch(c)


def list_staff(active_only: bool = True) -> list[dict]:
    sql = "SELECT * FROM staff" + (" WHERE active = 1" if active_only else "") + " ORDER BY id"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql)]


def pay_salary(staff_id: int, month: str | None = None, method: str = "Cash",
               amount: float | None = None, paid_at: str | None = None) -> dict:
    """Record a salary payment (default amount = the staff member's monthly salary)."""
    month = validate_month(month)
    method = normalize_method(method)
    with get_connection() as conn:
        person = get_staff(staff_id, conn)
        if not person["active"]:
            raise GymError(f"{person['name']} is no longer active staff.")
        amount = positive_amount(amount if amount is not None else person["monthly_salary"])
        paid_at = paid_at or now_str()
        already = conn.execute(
            "SELECT paid_at FROM salary_payments WHERE staff_id = ? AND month = ?", (staff_id, month)
        ).fetchone()
        if already:
            raise GymError(f"{person['name']}'s salary for {month} was already paid on {already['paid_at']}.")
        conn.execute(
            "INSERT INTO salary_payments (staff_id, month, amount, method, paid_at) VALUES (?, ?, ?, ?, ?)",
            (staff_id, month, amount, method, paid_at),
        )
    return {"staff_id": staff_id, "staff_name": person["name"], "month": month,
            "amount": amount, "method": method, "paid_at": paid_at}


def salary_status(month: str | None = None) -> list[dict]:
    """For every active staff member: salary, and whether/when it was paid this month."""
    month = validate_month(month)
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT s.id, s.name, s.role, s.monthly_salary,
                      sp.amount AS paid_amount, sp.method, sp.paid_at
               FROM staff s
               LEFT JOIN salary_payments sp ON sp.staff_id = s.id AND sp.month = ?
               WHERE s.active = 1 ORDER BY s.id""",
            (month,),
        ).fetchall()
    result = []
    for r in rows:
        item = dict(r)
        item["status"] = "Paid" if r["paid_at"] else "Unpaid"
        result.append(item)
    return result
