"""Small helpers used everywhere: dates/times, money formatting, and errors."""
import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from gym_ai import config


class GymError(ValueError):
    """
    A business-rule problem with a human-readable message.

    Example: "Member 5 not found". The tools catch this and hand the message
    back to the AI so it can explain the problem to the user.
    """


# ---------- date & time (always in the gym's timezone) ----------
def now() -> datetime:
    return datetime.now(ZoneInfo(config.TIMEZONE))


def now_str() -> str:
    """Current date AND time, e.g. '2026-10-01 14:35:09'."""
    return now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return now().strftime("%Y-%m-%d")


def current_month() -> str:
    return now().strftime("%Y-%m")


def validate_month(month: str | None) -> str:
    """Return a valid 'YYYY-MM' string (defaults to the current month)."""
    if not month:
        return current_month()
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise GymError("Month must look like YYYY-MM, for example 2026-10.")
    return month


def month_end(month: str) -> str:
    """Last calendar day of a month: '2026-10' -> '2026-10-31'."""
    year, mon = map(int, month.split("-"))
    return f"{month}-{calendar.monthrange(year, mon)[1]:02d}"


def add_days(date_str: str, days: int) -> str:
    return (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")


def days_between(start: str, end: str) -> int:
    """Whole days from start to end (negative if end is earlier)."""
    fmt = "%Y-%m-%d"
    return (datetime.strptime(end, fmt) - datetime.strptime(start, fmt)).days


# ---------- money ----------
def money(amount: float) -> str:
    return f"{config.CURRENCY} {amount:,.0f}"


def normalize_method(method: str) -> str:
    """Match user text like 'cash' or 'jazzcash' to an allowed payment method."""
    wanted = (method or "").strip().lower().replace(" ", "")
    for allowed in config.PAYMENT_METHODS:
        if allowed.lower().replace(" ", "") == wanted:
            return allowed
    raise GymError(f"Unknown payment method '{method}'. Allowed: {', '.join(config.PAYMENT_METHODS)}.")


def positive_amount(amount: float) -> float:
    if amount is None or amount <= 0:
        raise GymError("Amount must be greater than zero.")
    return float(amount)
