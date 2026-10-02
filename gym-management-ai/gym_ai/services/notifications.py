"""
Reminder messages (renewals and overdue fees).

Messages are saved in the `notifications` table. Delivery is SIMULATED
(printed to the console) so the project runs with no paid accounts.
To send real WhatsApp/SMS, replace `deliver()` with a call to your provider
(e.g. Twilio or the WhatsApp Business API) - nothing else needs to change.
"""
from gym_ai.database import get_connection
from gym_ai.services.payments import list_expiring_members, list_overdue_members
from gym_ai.utils import now_str


def deliver(channel: str, phone: str, message: str) -> None:
    """PLACEHOLDER for a real sender. Currently just prints."""
    print(f"[{channel.upper()} -> {phone}] {message}")


def _queue_and_send(member_id: int, phone: str, message: str, channel: str = "whatsapp") -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO notifications (member_id, channel, message, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (member_id, channel, message, "simulated_sent", now_str()),
        )
    deliver(channel, phone, message)


def send_renewal_reminders(days_ahead: int = 7) -> dict:
    """Remind members expiring soon, and chase members who are already overdue."""
    expiring = list_expiring_members(days_ahead)
    overdue = list_overdue_members()

    for m in expiring:
        _queue_and_send(m["id"], m["phone"],
                        f"Hi {m['name']}, your gym membership ends on {m['membership_expiry']}. "
                        f"Renew for {m['renewal_fee']:,.0f} to keep training without a break!")
    for m in overdue:
        _queue_and_send(m["id"], m["phone"],
                        f"Hi {m['name']}, your gym fee of {m['amount_due']:,.0f} is due. "
                        "Please pay at the front desk to continue your membership.")
    return {"expiring_reminders": len(expiring), "overdue_reminders": len(overdue),
            "delivery": "simulated (printed to console)"}


def list_notifications(limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT member_id, channel, message, status, created_at FROM notifications "
            "ORDER BY id DESC LIMIT ?", (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
