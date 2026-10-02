"""Tools for the MEMBERS agent: registration, profiles, plans."""
from langchain_core.tools import tool

from gym_ai.services import members, plans
from gym_ai.tools._helpers import needs_confirmation, safe


@tool
@safe
def list_plans() -> list:
    """List all membership plans with their id, duration in days and fee."""
    return plans.list_plans()


@tool
@safe
def add_plan(name: str, duration_days: int, fee: float) -> dict:
    """Create a new membership plan, e.g. name='Quarterly', duration_days=90, fee=8000."""
    return plans.add_plan(name, duration_days, fee)


@tool
@safe
def add_member(name: str, phone: str, plan_id: int | None = None, email: str | None = None,
               gender: str | None = None, age: int | None = None, height_cm: float | None = None,
               weight_kg: float | None = None, goal: str | None = None,
               fitness_level: str | None = None) -> dict:
    """Register a new gym member. Name and phone are required. The member must make a payment before the membership becomes active."""
    return members.add_member(name, phone, plan_id, email, gender, age, height_cm, weight_kg, goal, fitness_level)


@tool
@safe
def get_member(member_id: int) -> dict:
    """Get one member's full profile, plan, expiry date and membership_state (active / expired / no_payment_yet / inactive)."""
    return members.get_member(member_id)


@tool
@safe
def search_members(query: str) -> list:
    """Find members by part of their name or phone number."""
    return members.search_members(query)


@tool
@safe
def list_members(status: str | None = None) -> list:
    """List all members. Optionally filter by status: 'active' or 'inactive'."""
    return members.list_members(status)


@tool
@safe
def update_member(member_id: int, name: str | None = None, phone: str | None = None,
                  email: str | None = None, gender: str | None = None, age: int | None = None,
                  height_cm: float | None = None, weight_kg: float | None = None,
                  goal: str | None = None, fitness_level: str | None = None,
                  plan_id: int | None = None) -> dict:
    """Update details of an existing member. Only pass the fields that change."""
    return members.update_member(member_id, name=name, phone=phone, email=email, gender=gender, age=age,
                                 height_cm=height_cm, weight_kg=weight_kg, goal=goal,
                                 fitness_level=fitness_level, plan_id=plan_id)


@tool
@safe
def deactivate_member(member_id: int, confirmed: bool = False) -> dict:
    """Deactivate a member (stops check-ins and payments). SENSITIVE: ask the user to confirm first, then pass confirmed=True."""
    if not confirmed:
        return needs_confirmation(f"deactivate member {member_id}")
    return members.set_member_status(member_id, "inactive")


@tool
@safe
def reactivate_member(member_id: int) -> dict:
    """Reactivate a previously deactivated member."""
    return members.set_member_status(member_id, "active")


MEMBER_TOOLS = [list_plans, add_plan, add_member, get_member, search_members,
                list_members, update_member, deactivate_member, reactivate_member]
