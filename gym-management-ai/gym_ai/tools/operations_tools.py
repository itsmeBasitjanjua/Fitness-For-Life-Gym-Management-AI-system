"""Tools for the OPERATIONS agent: attendance, classes, equipment and sales leads."""
from langchain_core.tools import tool

from gym_ai.services import attendance, classes, equipment, leads
from gym_ai.tools._helpers import safe


# ----- attendance -----
@tool
@safe
def check_in_member(member_id: int) -> dict:
    """Check a member in at the front desk. Entry is denied if the membership is expired or unpaid."""
    return attendance.check_in(member_id)


@tool
@safe
def attendance_today(date: str | None = None) -> list:
    """Who visited the gym on a date (YYYY-MM-DD, default today)."""
    return attendance.attendance_on(date)


@tool
@safe
def member_attendance_history(member_id: int) -> dict:
    """A member's recent visits and number of visits this month."""
    return attendance.member_attendance(member_id)


# ----- classes -----
@tool
@safe
def list_classes() -> list:
    """List all group classes with weekday, time, trainer and capacity."""
    return classes.list_classes()


@tool
@safe
def add_class(name: str, weekday: str, start_time: str, capacity: int, trainer_id: int | None = None) -> dict:
    """Create a group class, e.g. name='Yoga', weekday='Monday', start_time='18:00', capacity=15."""
    return classes.add_class(name, weekday, start_time, capacity, trainer_id)


@tool
@safe
def book_class(class_id: int, member_id: int, class_date: str) -> dict:
    """Book a member into a class on a date (YYYY-MM-DD). Goes to the waitlist when the class is full."""
    return classes.book_class(class_id, member_id, class_date)


@tool
@safe
def cancel_booking(class_id: int, member_id: int, class_date: str) -> dict:
    """Cancel a class booking. The first waitlisted member is promoted automatically."""
    return classes.cancel_booking(class_id, member_id, class_date)


@tool
@safe
def class_roster(class_id: int, class_date: str) -> dict:
    """Who is booked (confirmed and waitlisted) for a class on a date."""
    return classes.class_roster(class_id, class_date)


# ----- equipment -----
@tool
@safe
def list_equipment(status: str | None = None) -> list:
    """List equipment. Optional status filter: working, faulty, under_maintenance."""
    return equipment.list_equipment(status)


@tool
@safe
def add_equipment(name: str, next_service: str | None = None) -> dict:
    """Add a machine or equipment item. next_service is an optional date YYYY-MM-DD."""
    return equipment.add_equipment(name, next_service)


@tool
@safe
def report_equipment_fault(equipment_id: int, note: str) -> dict:
    """Mark equipment as faulty and describe the problem."""
    return equipment.report_fault(equipment_id, note)


@tool
@safe
def mark_equipment_serviced(equipment_id: int, next_service: str | None = None) -> dict:
    """Mark equipment as repaired/serviced today and optionally set the next service date."""
    return equipment.mark_serviced(equipment_id, next_service)


# ----- sales leads -----
@tool
@safe
def add_lead(name: str, phone: str, source: str | None = None, notes: str | None = None) -> dict:
    """Save a new sales lead (someone interested in joining)."""
    return leads.add_lead(name, phone, source, notes)


@tool
@safe
def list_leads(status: str | None = None) -> list:
    """List leads. Optional status: new, contacted, trial, joined, lost."""
    return leads.list_leads(status)


@tool
@safe
def update_lead_status(lead_id: int, status: str, notes: str | None = None) -> dict:
    """Move a lead to a new status: new, contacted, trial, joined or lost."""
    return leads.update_lead_status(lead_id, status, notes)


OPERATIONS_TOOLS = [check_in_member, attendance_today, member_attendance_history, list_classes, add_class,
                    book_class, cancel_booking, class_roster, list_equipment, add_equipment,
                    report_equipment_fault, mark_equipment_serviced, add_lead, list_leads, update_lead_status]
