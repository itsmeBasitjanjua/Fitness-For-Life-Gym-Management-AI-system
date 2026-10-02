"""
Member fee payments.

Every payment stores the AMOUNT, the PAYMENT METHOD and the exact DATE + TIME.
Paying a full plan fee automatically extends the member's membership.
"""
from gym_ai.database import get_connection
from gym_ai.services.members import _fetch_member
from gym_ai.utils import (GymError, add_days, days_between, normalize_method,
                          now_str, positive_amount, today_str, validate_month)


def record_payment(member_id: int, amount: float, method: str,
                   note: str | None = None, paid_at: str | None = None) -> dict:
    """
    Save a payment and extend the membership.

    How extension works:
      * member has a plan with fee F and duration D days
      * a payment of amount A covers floor(A / F) periods -> adds that many x D days
      * extension starts from the payment date, or from the old expiry if it is later
      * paying less than one full fee is saved as a PARTIAL payment (no extension)

    `paid_at` is only for back-dating old records (e.g. importing); normally it is "now".
    """
    amount = positive_amount(amount)
    method = normalize_method(method)
    paid_at = paid_at or now_str()

    with get_connection() as conn:
        member = _fetch_member(conn, member_id)
        if member["status"] != "active":
            raise GymError(f"Member {member_id} is inactive. Reactivate before accepting payment.")

        extended_days = 0
        new_expiry = member["membership_expiry"]
        message = "Payment recorded."

        if member["plan_id"]:
            periods = int(amount // member["plan_fee"])
            if periods >= 1:
                extended_days = periods * member["duration_days"]
                paid_date = paid_at[:10]          # normally today; older for back-dated records
                old_expiry = member["membership_expiry"]
                start = old_expiry if old_expiry and old_expiry > paid_date else paid_date
                new_expiry = add_days(start, extended_days)
                conn.execute("UPDATE members SET membership_expiry = ? WHERE id = ?", (new_expiry, member_id))
                message = f"Payment recorded. Membership extended by {extended_days} days."
            else:
                message = (f"Partial payment recorded (plan fee is {member['plan_fee']:,.0f}). "
                           "Membership was NOT extended.")
        else:
            message = "Payment recorded. Member has no plan, so no expiry was set."

        cur = conn.execute(
            """INSERT INTO payments (member_id, amount, method, paid_at, note, extended_days)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (member_id, amount, method, paid_at, note, extended_days),
        )
        receipt_no = f"RCPT-{paid_at[:10].replace('-', '')}-{cur.lastrowid:04d}"
        conn.execute("UPDATE payments SET receipt_no = ? WHERE id = ?", (receipt_no, cur.lastrowid))

    return {
        "receipt_no": receipt_no, "member_id": member_id, "member_name": member["name"],
        "amount": amount, "method": method, "paid_at": paid_at,
        "membership_expiry": new_expiry, "extended_days": extended_days, "message": message,
    }


def payment_history(member_id: int, limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        _fetch_member(conn, member_id)
        rows = conn.execute(
            """SELECT receipt_no, amount, method, paid_at, note FROM payments
               WHERE member_id = ? ORDER BY paid_at DESC LIMIT ?""",
            (member_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def payments_in_month(month: str | None = None) -> list[dict]:
    """Every payment received in a month, newest last (used by the PDF ledger)."""
    month = validate_month(month)
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT p.receipt_no, p.member_id, m.name AS member_name, p.amount, p.method, p.paid_at
               FROM payments p JOIN members m ON m.id = p.member_id
               WHERE substr(p.paid_at, 1, 7) = ? ORDER BY p.paid_at""",
            (month,),
        ).fetchall()
    return [dict(r) for r in rows]


def revenue_by_method(month: str | None = None) -> dict:
    """Total money received in a month, split by payment method."""
    month = validate_month(month)
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT method, SUM(amount) AS total, COUNT(*) AS payments FROM payments
               WHERE substr(paid_at, 1, 7) = ? GROUP BY method ORDER BY total DESC""",
            (month,),
        ).fetchall()
    by_method = [dict(r) for r in rows]
    return {"month": month, "total": sum(r["total"] for r in by_method), "by_method": by_method}


def list_overdue_members() -> list[dict]:
    """Active members whose membership has expired, or who never paid at all."""
    today = today_str()
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT m.id, m.name, m.phone, m.membership_expiry, p.name AS plan_name, p.fee AS amount_due
               FROM members m JOIN plans p ON p.id = m.plan_id
               WHERE m.status = 'active' AND (m.membership_expiry IS NULL OR m.membership_expiry < ?)
               ORDER BY m.membership_expiry""",
            (today,),
        ).fetchall()
    result = []
    for r in rows:
        item = dict(r)
        item["days_overdue"] = days_between(r["membership_expiry"], today) if r["membership_expiry"] else None
        result.append(item)
    return result


def list_expiring_members(days: int = 7) -> list[dict]:
    """Active members whose membership ends within the next `days` days."""
    today = today_str()
    limit = add_days(today, days)
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT m.id, m.name, m.phone, m.membership_expiry, p.name AS plan_name, p.fee AS renewal_fee
               FROM members m JOIN plans p ON p.id = m.plan_id
               WHERE m.status = 'active' AND m.membership_expiry BETWEEN ? AND ?
               ORDER BY m.membership_expiry""",
            (today, limit),
        ).fetchall()
    return [dict(r) for r in rows]
