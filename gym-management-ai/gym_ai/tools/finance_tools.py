"""Tools for the FINANCE agent (owner only): staff, salaries, expenses and the PDF report."""
from langchain_core.tools import tool

from gym_ai.services import expenses, pdf_report, reports, staff
from gym_ai.tools._helpers import needs_confirmation, safe


@tool
@safe
def add_staff(name: str, role: str, monthly_salary: float, phone: str | None = None) -> dict:
    """Add a staff member (trainer, receptionist, cleaner ...) with their monthly salary."""
    return staff.add_staff(name, role, monthly_salary, phone)


@tool
@safe
def list_staff(active_only: bool = True) -> list:
    """List gym staff with roles and monthly salaries."""
    return staff.list_staff(active_only)


@tool
@safe
def salary_status(month: str | None = None) -> list:
    """For a month (YYYY-MM, default current): each staff member's salary and whether/when it was paid."""
    return staff.salary_status(month)


@tool
@safe
def pay_salary(staff_id: int, month: str | None = None, method: str = "Cash",
               amount: float | None = None, confirmed: bool = False) -> dict:
    """Pay a staff member's salary for a month. Date and time are saved automatically.
    SENSITIVE (moves money): ask the user to confirm first, then pass confirmed=True.
    Default amount is the staff member's monthly salary."""
    if not confirmed:
        return needs_confirmation(f"pay salary of staff {staff_id} for {month or 'this month'} via {method}")
    return staff.pay_salary(staff_id, month, method, amount)


@tool
@safe
def add_expense(category: str, amount: float, description: str | None = None) -> dict:
    """Record a gym expense such as Rent, Electricity, Equipment, Maintenance, Supplements, Marketing or Cleaning."""
    return expenses.add_expense(category, amount, description)


@tool
@safe
def list_expenses(month: str | None = None) -> list:
    """List expenses for a month (YYYY-MM, default current)."""
    return expenses.list_expenses(month)


@tool
@safe
def monthly_financial_summary(month: str | None = None) -> dict:
    """Income, expenses, salaries paid and net profit for a month (YYYY-MM, default current)."""
    return reports.monthly_financial_summary(month)


@tool
@safe
def generate_monthly_pdf_report(month: str | None = None) -> dict:
    """Create the PDF report for a month: all members with fees and payment date/time/method,
    staff salaries, expenses and net profit. Returns the file path."""
    return {"pdf_path": pdf_report.generate_monthly_pdf(month),
            "message": "PDF report created."}


FINANCE_TOOLS = [add_staff, list_staff, salary_status, pay_salary, add_expense,
                 list_expenses, monthly_financial_summary, generate_monthly_pdf_report]
