"""
Database layer (SQLite).

One file, one place to see every table in the system. SQLite needs no
server, so the project runs anywhere. To move to PostgreSQL later, only this
file and the SQL in the services need to change.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from gym_ai import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS plans (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,          -- e.g. 'Monthly'
    duration_days INTEGER NOT NULL,              -- 30, 90, 365 ...
    fee           REAL NOT NULL                  -- price for one period
);

CREATE TABLE IF NOT EXISTS members (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    phone             TEXT NOT NULL,
    email             TEXT,
    gender            TEXT,
    age               INTEGER,
    height_cm         REAL,
    weight_kg         REAL,
    goal              TEXT,                      -- e.g. 'lose fat', 'build muscle'
    fitness_level     TEXT,                      -- beginner / intermediate / advanced
    plan_id           INTEGER REFERENCES plans(id),
    join_date         TEXT NOT NULL,             -- YYYY-MM-DD
    membership_expiry TEXT,                      -- YYYY-MM-DD, set by payments
    status            TEXT NOT NULL DEFAULT 'active'   -- active / inactive
);

CREATE TABLE IF NOT EXISTS payments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id     INTEGER NOT NULL REFERENCES members(id),
    amount        REAL NOT NULL,
    method        TEXT NOT NULL,                 -- Cash, Card, JazzCash ...
    paid_at       TEXT NOT NULL,                 -- YYYY-MM-DD HH:MM:SS  (date AND time)
    receipt_no    TEXT,
    note          TEXT,
    extended_days INTEGER NOT NULL DEFAULT 0     -- how many days this payment added
);

CREATE TABLE IF NOT EXISTS staff (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    role           TEXT NOT NULL,                -- Trainer, Receptionist, Cleaner ...
    phone          TEXT,
    monthly_salary REAL NOT NULL,
    join_date      TEXT NOT NULL,
    active         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS salary_payments (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER NOT NULL REFERENCES staff(id),
    month    TEXT NOT NULL,                      -- YYYY-MM the salary is for
    amount   REAL NOT NULL,
    method   TEXT NOT NULL,
    paid_at  TEXT NOT NULL,                      -- YYYY-MM-DD HH:MM:SS
    UNIQUE (staff_id, month)                     -- cannot pay the same month twice
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category    TEXT NOT NULL,                   -- Rent, Electricity, Equipment ...
    description TEXT,
    amount      REAL NOT NULL,
    spent_at    TEXT NOT NULL                    -- YYYY-MM-DD HH:MM:SS
);

CREATE TABLE IF NOT EXISTS attendance (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES members(id),
    check_in  TEXT NOT NULL                      -- YYYY-MM-DD HH:MM:SS
);

CREATE TABLE IF NOT EXISTS classes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    trainer_id INTEGER REFERENCES staff(id),
    weekday    TEXT NOT NULL,                    -- Monday ...
    start_time TEXT NOT NULL,                    -- HH:MM
    capacity   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id   INTEGER NOT NULL REFERENCES classes(id),
    member_id  INTEGER NOT NULL REFERENCES members(id),
    class_date TEXT NOT NULL,                    -- YYYY-MM-DD
    status     TEXT NOT NULL,                    -- confirmed / waitlist / cancelled
    booked_at  TEXT NOT NULL,
    UNIQUE (class_id, member_id, class_date)
);

CREATE TABLE IF NOT EXISTS equipment (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'working', -- working / faulty / under_maintenance
    last_service TEXT,
    next_service TEXT,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS leads (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    phone      TEXT NOT NULL,
    source     TEXT,                             -- Instagram, walk-in, referral ...
    status     TEXT NOT NULL DEFAULT 'new',      -- new / contacted / trial / joined / lost
    notes      TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id    INTEGER NOT NULL REFERENCES members(id),
    logged_at    TEXT NOT NULL,
    weight_kg    REAL,
    body_fat_pct REAL,
    note         TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id  INTEGER REFERENCES members(id),
    channel    TEXT NOT NULL,                    -- whatsapp / sms / email
    message    TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'queued',   -- queued / simulated_sent
    created_at TEXT NOT NULL
);
"""


def _prepare_folder(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    """
    Open the database, commit if everything worked, roll back on any error.

        with get_connection() as conn:
            conn.execute("INSERT ...")
    """
    path = config.db_path()
    _prepare_folder(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row            # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_readonly_connection() -> sqlite3.Connection:
    """A connection that physically cannot change data (used by the SQL analytics tool)."""
    path = Path(config.db_path()).resolve()
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables if they do not exist yet. Safe to call many times."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
