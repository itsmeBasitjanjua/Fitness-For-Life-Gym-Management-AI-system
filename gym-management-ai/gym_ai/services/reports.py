"""
Numbers for the owner: dashboard, monthly profit & loss, and the member fee table.
The PDF report and the AI analytics agent both read from here.
"""
from gym_ai.database import get_connection
from gym_ai.services import expenses, payments, staff
from gym_ai.utils import month_end, today_str, validate_month, current_month, add_days


def dashboard_stats() -> dict:
    """Quick snapshot of the whole gym right now."""
    today = today_str()
    month = current_month()
    with get_connection() as conn:
        one = lambda sql, *p: conn.execute(sql, p).fetchone()[0]
        stats = {
            "date": today,
            "total_members": one("SELECT COUNT(*) FROM members"),
            "active_members": one("SELECT COUNT(*) FROM members WHERE status='active' AND membership_expiry >= ?", today),
            "expired_members": one("SELECT COUNT(*) FROM members WHERE status='active' AND membership_expiry < ?", today),
            "never_paid_members": one("SELECT COUNT(*) FROM members WHERE status='active' AND membership_expiry IS NULL"),
            "expiring_in_7_days": one("SELECT COUNT(*) FROM members WHERE status='active' AND membership_expiry BETWEEN ? AND ?",
                                      today, add_days(today, 7)),
            "visits_today": one("SELECT COUNT(*) FROM attendance WHERE substr(check_in,1,10) = ?", today),
            "faulty_equipment": one("SELECT COUNT(*) FROM equipment WHERE status != 'working'"),
            "open_leads": one("SELECT COUNT(*) FROM leads WHERE status IN ('new','contacted','trial')"),
        }
    stats["revenue_this_month"] = payments.revenue_by_method(month)["total"]
    stats["expenses_this_month"] = expenses.expense_summary(month)["total"]
    return stats


def monthly_financial_summary(month: str | None = None) -> dict:
    """Income, expenses, salaries and net profit for one month."""
    month = validate_month(month)
    income = payments.revenue_by_method(month)
    spending = expenses.expense_summary(month)
    salaries = staff.salary_status(month)
    salaries_paid = sum(s["paid_amount"] for s in salaries if s["paid_amount"])
    salaries_due = sum(s["monthly_salary"] for s in salaries if not s["paid_amount"])
    net = income["total"] - spending["total"] - salaries_paid
    return {
        "month": month,
        "income_total": income["total"],
        "income_by_method": income["by_method"],
        "expenses_total": spending["total"],
        "expenses_by_category": spending["by_category"],
        "salaries_paid": salaries_paid,
        "salaries_still_unpaid": salaries_due,
        "net_profit": net,
    }


def members_fee_table(month: str | None = None) -> list[dict]:
    """
    One row per member for the PDF: plan fee, fee status for the month,
    and the date + time + method of their latest payment.

    fee_status:
      Paid    - member paid at least once during that month
      Prepaid - no payment this month, but membership still covers the month end
      Unpaid  - nothing paid and membership not covering the month
      Inactive - member was deactivated
    """
    month = validate_month(month)
    end = month_end(month)
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT m.id, m.name, m.phone, m.status, m.join_date, m.membership_expiry,
                      p.name AS plan_name, p.fee AS plan_fee,
                      (SELECT COALESCE(SUM(amount), 0) FROM payments
                        WHERE member_id = m.id AND substr(paid_at, 1, 7) = :month) AS paid_in_month,
                      (SELECT paid_at FROM payments
                        WHERE member_id = m.id AND substr(paid_at, 1, 7) <= :month
                        ORDER BY paid_at DESC LIMIT 1) AS last_paid_at,
                      (SELECT method FROM payments
                        WHERE member_id = m.id AND substr(paid_at, 1, 7) <= :month
                        ORDER BY paid_at DESC LIMIT 1) AS last_method
               FROM members m LEFT JOIN plans p ON p.id = m.plan_id
               WHERE m.join_date <= :end ORDER BY m.id""",
            {"month": month, "end": end},
        ).fetchall()

    table = []
    for r in rows:
        item = dict(r)
        if item["status"] != "active":
            item["fee_status"] = "Inactive"
        elif item["paid_in_month"] > 0:
            item["fee_status"] = "Paid"
        elif item["membership_expiry"] and item["membership_expiry"] >= end:
            item["fee_status"] = "Prepaid"
        else:
            item["fee_status"] = "Unpaid"
        table.append(item)
    return table
