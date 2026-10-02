"""
Central settings.

Everything configurable lives here, so you never have to hunt through the
code to change the gym name, currency, model or database location.
Values come from environment variables (or a local ".env" file).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Gym identity (shown on PDF reports) ---
GYM_NAME = os.getenv("GYM_NAME", "FitZone Gym")
CURRENCY = os.getenv("GYM_CURRENCY", "PKR")
TIMEZONE = os.getenv("GYM_TIMEZONE", "Asia/Karachi")

# --- AI model ---
MODEL_NAME = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

# --- Folders ---
REPORTS_DIR = BASE_DIR / "reports"

# --- Allowed payment methods (the AI can only record one of these) ---
PAYMENT_METHODS = ["Cash", "Card", "Bank Transfer", "JazzCash", "Easypaisa", "Other"]


def db_path() -> str:
    """Location of the SQLite file. Read on every call so tests can override it."""
    return os.getenv("GYM_DB_PATH", str(BASE_DIR / "data" / "gym.db"))
