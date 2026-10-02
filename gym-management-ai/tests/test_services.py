"""Tests for the business logic (no AI involved)."""
import pytest

from gym_ai.services import (analytics, attendance, classes, expenses, members, nutrition,
                             payments, pdf_report, plans, reports, staff)
from gym_ai.utils import GymError, add_days, today_str


@pytest.fixture
def monthly_member():
    plan = plans.add_plan("Monthly", 30, 5000)
    return members.add_member("Test Member", "0300-0000001", plan["id"])


# ---------- members & payments ----------
def test_new_member_has_no_payment_yet(monthly_member):
    assert monthly_member["membership_state"] == "no_payment_yet"


def test_duplicate_phone_is_rejected(monthly_member):
    with pytest.raises(GymError):
        members.add_member("Other", "0300-0000001")


def test_full_payment_extends_membership_and_stores_method_and_time(monthly_member):
    result = payments.record_payment(monthly_member["id"], 5000, "jazzcash")
    assert result["method"] == "JazzCash"                      # normalised
    assert len(result["paid_at"]) == 19                        # date AND time
    assert result["membership_expiry"] == add_days(today_str(), 30)
    assert members.get_member(monthly_member["id"])["membership_state"] == "active"


def test_second_payment_stacks_on_existing_expiry(monthly_member):
    payments.record_payment(monthly_member["id"], 5000, "Cash")
    second = payments.record_payment(monthly_member["id"], 5000, "Cash")
    assert second["membership_expiry"] == add_days(today_str(), 60)


def test_partial_payment_does_not_extend(monthly_member):
    result = payments.record_payment(monthly_member["id"], 2000, "Cash")
    assert result["extended_days"] == 0
    assert members.get_member(monthly_member["id"])["membership_expiry"] is None


def test_invalid_method_and_amount(monthly_member):
    with pytest.raises(GymError):
        payments.record_payment(monthly_member["id"], 5000, "Bitcoin")
    with pytest.raises(GymError):
        payments.record_payment(monthly_member["id"], -5, "Cash")


def test_overdue_and_expiring(monthly_member):
    assert [m["id"] for m in payments.list_overdue_members()] == [monthly_member["id"]]
    payments.record_payment(monthly_member["id"], 5000, "Cash", paid_at=f"{add_days(today_str(), -26)} 10:00:00")
    assert payments.list_overdue_members() == []
    assert len(payments.list_expiring_members(7)) == 1


# ---------- attendance & classes ----------
def test_check_in_requires_valid_membership(monthly_member):
    assert attendance.check_in(monthly_member["id"])["allowed"] is False
    payments.record_payment(monthly_member["id"], 5000, "Cash")
    assert attendance.check_in(monthly_member["id"])["allowed"] is True
    assert "Already" in attendance.check_in(monthly_member["id"])["message"]


def test_class_waitlist_and_promotion(monthly_member):
    payments.record_payment(monthly_member["id"], 5000, "Cash")
    plan = plans.list_plans()[0]
    other = members.add_member("Second", "0300-0000002", plan["id"])
    payments.record_payment(other["id"], 5000, "Cash")

    yoga = classes.add_class("Yoga", "Monday", "18:00", capacity=1)
    first = classes.book_class(yoga["id"], monthly_member["id"], "2026-10-05")
    second = classes.book_class(yoga["id"], other["id"], "2026-10-05")
    assert (first["status"], second["status"]) == ("confirmed", "waitlist")

    cancel = classes.cancel_booking(yoga["id"], monthly_member["id"], "2026-10-05")
    assert cancel["promoted_from_waitlist"]["member_id"] == other["id"]


# ---------- staff, expenses, finance ----------
def test_salary_cannot_be_paid_twice():
    person = staff.add_staff("Coach", "Trainer", 40000)
    staff.pay_salary(person["id"], "2026-09", "Cash")
    with pytest.raises(GymError):
        staff.pay_salary(person["id"], "2026-09", "Cash")


def test_monthly_summary_math(monthly_member):
    month = today_str()[:7]
    payments.record_payment(monthly_member["id"], 5000, "Cash")
    person = staff.add_staff("Coach", "Trainer", 1000)
    staff.pay_salary(person["id"], month, "Cash")
    expenses.add_expense("Rent", 1500)
    summary = reports.monthly_financial_summary(month)
    assert summary["income_total"] == 5000
    assert summary["net_profit"] == 5000 - 1500 - 1000


# ---------- nutrition ----------
def test_nutrition_targets_make_sense():
    t = nutrition.calculate_targets(80, 180, 30, "male", "moderate", "fat_loss")
    assert t["target_kcal"] < t["maintenance_kcal"]
    assert t["protein_g"] == 160
    with pytest.raises(GymError):
        nutrition.calculate_targets(80, 180, 30, "male", "super_active", "fat_loss")


# ---------- safety of the SQL tool ----------
def test_sql_tool_is_read_only(monthly_member):
    assert analytics.run_read_only_query("SELECT COUNT(*) AS n FROM members")["rows"][0]["n"] == 1
    for bad in ["DROP TABLE members", "DELETE FROM members", "SELECT 1; DROP TABLE members",
                "SELECT * FROM members WHERE 1=1 UNION SELECT 1; --"]:
        with pytest.raises(GymError):
            analytics.run_read_only_query(bad)


# ---------- PDF ----------
def test_pdf_contains_members_fees_salaries_and_expenses(tmp_path, monthly_member):
    from pypdf import PdfReader
    month = today_str()[:7]
    payments.record_payment(monthly_member["id"], 5000, "Easypaisa")
    person = staff.add_staff("Coach Ahmed", "Trainer", 40000)
    staff.pay_salary(person["id"], month, "Bank Transfer")
    expenses.add_expense("Rent", 150000, "Building rent")

    path = pdf_report.generate_monthly_pdf(month, str(tmp_path / "report.pdf"))
    text = "".join(page.extract_text() for page in PdfReader(path).pages)
    for expected in ["Test Member", "Easypaisa", "Coach Ahmed", "Bank Transfer", "Rent", "NET PROFIT", "Date & time"]:
        assert expected in text
