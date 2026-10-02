"""Tools for the BILLING agent: member fee payments and reminders."""
from langchain_core.tools import tool

from gym_ai.services import notifications, payments
from gym_ai.tools._helpers import safe


@tool
@safe
def record_payment(member_id: int, amount: float, method: str, note: str | None = None) -> dict:
    """Record a member's fee payment. The date and time are saved automatically.
    method must be one of: Cash, Card, Bank Transfer, JazzCash, Easypaisa, Other.
    A full plan fee extends the membership automatically."""
    return payments.record_payment(member_id, amount, method, note)


@tool
@safe
def payment_history(member_id: int, limit: int = 20) -> list:
    """Show a member's past payments with receipt number, amount, method and date/time."""
    return payments.payment_history(member_id, limit)


@tool
@safe
def list_overdue_members() -> list:
    """Active members whose membership has expired or who never paid, with the amount due."""
    return payments.list_overdue_members()


@tool
@safe
def list_expiring_members(days: int = 7) -> list:
    """Active members whose membership ends within the next N days."""
    return payments.list_expiring_members(days)


@tool
@safe
def monthly_revenue(month: str | None = None) -> dict:
    """Fees received in a month (YYYY-MM, default current) split by payment method."""
    return payments.revenue_by_method(month)


@tool
@safe
def send_renewal_reminders(days_ahead: int = 7) -> dict:
    """Send reminders to members expiring soon and to members with overdue fees (delivery is simulated)."""
    return notifications.send_renewal_reminders(days_ahead)


BILLING_TOOLS = [record_payment, payment_history, list_overdue_members,
                 list_expiring_members, monthly_revenue, send_renewal_reminders]
