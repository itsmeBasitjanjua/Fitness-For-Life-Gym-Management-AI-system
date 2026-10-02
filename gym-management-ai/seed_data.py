"""
Fill the database with realistic DEMO data so you can try the system at once.

    python seed_data.py            # add demo data to an empty database
    python seed_data.py --reset    # delete the old database first

All data is fictional.
"""
import argparse
import os
import random
from datetime import datetime, timedelta

from gym_ai import config
from gym_ai.database import get_connection, init_db
from gym_ai.services import (attendance, classes, equipment, expenses, leads, members,
                             payments, plans, progress, staff)
from gym_ai.utils import month_end, now, today_str

rng = random.Random(42)  # fixed seed -> same demo data every time


def days_ago(n: int, hour: int | None = None) -> str:
    """A 'YYYY-MM-DD HH:MM:SS' string n days before today, at a random working time."""
    moment = now() - timedelta(days=n)
    hour = rng.randint(7, 21) if hour is None else hour
    return moment.replace(hour=hour, minute=rng.randint(0, 59), second=rng.randint(0, 59)).strftime("%Y-%m-%d %H:%M:%S")


def previous_month(date: datetime) -> str:
    first = date.replace(day=1)
    return (first - timedelta(days=1)).strftime("%Y-%m")


FIRST_NAMES = ["Ahsan", "Zeeshan", "Hamza", "Saad", "Faizan", "Owais", "Adnan", "Waqas", "Haris", "Junaid",
               "Areeba", "Mehwish", "Rabia", "Anam", "Iqra", "Komal", "Sidra", "Nimra", "Mahnoor", "Zara"]
LAST_NAMES = ["Khan", "Ali", "Malik", "Raza", "Hussain", "Sheikh", "Butt", "Mirza", "Ansari", "Chaudhry", "Memon", "Shah"]


def generated_members(monthly, quarterly, yearly, count: int = 50) -> list:
    """Extra fictional members so the demo gym looks like a real, busy gym."""
    result = []
    for i in range(count):
        gender = "female" if i % 3 == 0 else "male"
        first = rng.choice(FIRST_NAMES[10:] if gender == "female" else FIRST_NAMES[:10])
        plan = rng.choices([monthly, quarterly, yearly], weights=[80, 15, 5])[0]
        dur = {monthly["id"]: 30, quarterly["id"]: 90, yearly["id"]: 365}[plan["id"]]
        first_pay = rng.randint(10, 95)
        full = first_pay // dur + 1                  # payments needed to be active today
        lapsed = rng.random() < 0.12                 # ~12% let their membership expire
        n_pay = max(full - 1, 0) if lapsed else full
        result.append((f"{first} {rng.choice(LAST_NAMES)}", f"0300-2222{i:03d}", plan, gender,
                       rng.randint(18, 45), rng.randint(155, 188), rng.randint(50, 95),
                       rng.choice(["lose fat", "build muscle", "stay fit", "tone up"]),
                       rng.choice(["beginner", "intermediate", "advanced"]), first_pay, n_pay))
    return result


def seed() -> None:
    init_db()
    with get_connection() as conn:
        if conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]:
            print("Database already has data. Use --reset to start fresh.")
            return

    # ---- plans ----
    monthly = plans.add_plan("Monthly", 30, 5000)
    quarterly = plans.add_plan("Quarterly", 90, 13500)
    yearly = plans.add_plan("Yearly", 365, 48000)
    duration = {monthly["id"]: 30, quarterly["id"]: 90, yearly["id"]: 365}

    # ---- members: (name, phone, plan, gender, age, height, weight, goal, level, first_payment_days_ago, payments_made)
    # payments_made decides if the membership is still active, expired, or never paid (0).
    people = [
        ("Ali Hassan",      "0300-1111001", monthly,   "male",   27, 175, 82, "lose fat",      "beginner",     75, 3),
        ("Usman Tariq",     "0300-1111002", monthly,   "male",   31, 180, 78, "build muscle",  "intermediate", 90, 4),
        ("Hira Aslam",      "0300-1111003", monthly,   "female", 24, 162, 60, "tone up",       "beginner",     60, 2),
        ("Fahad Mehmood",   "0300-1111004", quarterly, "male",   35, 172, 90, "lose fat",      "beginner",     100, 2),
        ("Maryam Sheikh",   "0300-1111005", monthly,   "female", 29, 165, 68, "lose fat",      "intermediate", 70, 3),
        ("Daniyal Qureshi", "0300-1111006", yearly,    "male",   22, 178, 70, "build muscle",  "advanced",     200, 1),
        ("Ayesha Siddiqui", "0300-1111007", monthly,   "female", 26, 158, 55, "stay fit",      "intermediate", 62, 2),
        ("Rizwan Ahmed",    "0300-1111008", monthly,   "male",   40, 170, 95, "lose fat",      "beginner",     45, 1),
        ("Sadia Khan",      "0300-1111009", quarterly, "female", 33, 160, 72, "lose fat",      "beginner",     95, 2),
        ("Kamran Baig",     "0300-1111010", monthly,   "male",   28, 183, 85, "build muscle",  "advanced",     88, 3),
        ("Noor Fatima",     "0300-1111011", monthly,   "female", 21, 164, 52, "gain weight",   "beginner",     33, 2),
        ("Talha Javed",     "0300-1111012", monthly,   "male",   25, 176, 74, "stay fit",      "intermediate", 20, 0),
        ("Bushra Iqbal",    "0300-1111013", monthly,   "female", 38, 159, 66, "tone up",       "beginner",     0, 0),
    ]
    people += generated_members(monthly, quarterly, yearly)
    methods = ["Cash", "Cash", "JazzCash", "Easypaisa", "Card", "Bank Transfer"]
    member_ids = []
    for name, phone, plan, gender, age, h, w, goal, level, first, n_pay in people:
        m = members.add_member(name, phone, plan["id"], gender=gender, age=age, height_cm=h,
                               weight_kg=w, goal=goal, fitness_level=level)
        member_ids.append(m["id"])
        join_ago = first + 2 if first else 5
        join_date = (now() - timedelta(days=join_ago)).strftime("%Y-%m-%d")
        with get_connection() as conn:
            conn.execute("UPDATE members SET join_date = ? WHERE id = ?", (join_date, m["id"]))
        for k in range(n_pay):
            offset = first - k * duration[plan["id"]]
            payments.record_payment(m["id"], plan["fee"], rng.choice(methods), paid_at=days_ago(offset))

    members.set_member_status(member_ids[7], "inactive")  # Rizwan left the gym

    # ---- staff and salaries ----
    team = [("Ahmed Raza", "Head Trainer", 40000), ("Sana Malik", "Fitness Trainer", 30000),
            ("Bilal Khan", "Receptionist", 22000), ("Imran Ali", "Cleaner", 15000),
            ("Zainab Fatima", "Nutrition Coach", 25000)]
    staff_ids = [staff.add_staff(n, r, s)["id"] for n, r, s in team]

    today = now()
    last_month = previous_month(today)
    month_before = previous_month(today.replace(day=1) - timedelta(days=1))
    for month in (month_before, last_month):
        for sid in staff_ids:
            staff.pay_salary(sid, month, rng.choice(["Bank Transfer", "Cash"]),
                             paid_at=f"{month_end(month)} {rng.randint(16, 18)}:{rng.randint(0, 59):02d}:00")

    # ---- expenses ----
    for month in (month_before, last_month):
        for cat, desc, amt in [("Rent", "Gym building rent", 70000), ("Electricity", "Monthly electricity bill", 30000),
                               ("Cleaning", "Cleaning supplies", 5000), ("Maintenance", "Machine servicing", 10000),
                               ("Marketing", "Instagram ads", 8000)]:
            day = rng.randint(1, 26)
            expenses.add_expense(cat, amt, desc, spent_at=f"{month}-{day:02d} {rng.randint(9, 18):02d}:{rng.randint(0, 59):02d}:00")
    expenses.add_expense("Rent", 70000, "Gym building rent", spent_at=f"{today.strftime('%Y-%m')}-01 10:15:00")

    # ---- classes, equipment, leads ----
    classes.add_class("Yoga", "Monday", "18:00", 12, staff_ids[1])
    classes.add_class("HIIT", "Wednesday", "19:00", 15, staff_ids[0])
    classes.add_class("Zumba", "Friday", "18:30", 20, staff_ids[1])
    for name in ["Treadmill 1", "Treadmill 2", "Squat Rack", "Leg Press", "Rowing Machine"]:
        equipment.add_equipment(name, next_service=(now() + timedelta(days=rng.randint(10, 90))).strftime("%Y-%m-%d"))
    equipment.report_fault(4, "Hydraulic jack leaking - do not use")
    leads.add_lead("Hamza Farooq", "0321-5550001", "Instagram", "Asked about quarterly plan")
    leads.add_lead("Laiba Noman", "0321-5550002", "Walk-in")
    leads.add_lead("Shahzaib Ali", "0321-5550003", "Referral", "Friend of Ali Hassan")

    # ---- attendance and progress ----
    for mid in member_ids[:6]:
        attendance.check_in(mid)
        with get_connection() as conn:   # a few older visits too
            for d in rng.sample(range(1, 25), 6):
                conn.execute("INSERT INTO attendance (member_id, check_in) VALUES (?, ?)", (mid, days_ago(d)))
    progress.log_progress(member_ids[0], 84, 26, "Starting weight")
    progress.log_progress(member_ids[0], 82, 25, "Month 1 check")

    print(f"Demo data created in {config.db_path()}")
    print(f"Try: python main.py report --month {last_month}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create demo data")
    parser.add_argument("--reset", action="store_true", help="delete the existing database first")
    args = parser.parse_args()
    if args.reset and os.path.exists(config.db_path()):
        os.remove(config.db_path())
    seed()
