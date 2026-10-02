"""Tools for the FITNESS agent: member profile, calorie targets and progress tracking."""
from langchain_core.tools import tool

from gym_ai.services import members, nutrition, progress
from gym_ai.tools._helpers import safe


@tool
@safe
def get_member_profile(member_id: int) -> dict:
    """Get a member's profile: age, gender, height, weight, goal and fitness level. Use before making a plan."""
    return members.get_member(member_id)


@tool
@safe
def calculate_nutrition_targets(member_id: int, activity_level: str = "moderate",
                                goal: str = "maintain") -> dict:
    """Calculate daily calories and protein/carbs/fat for a member using their stored profile.
    activity_level: sedentary, light, moderate, active, very_active.
    goal: fat_loss, maintain or muscle_gain."""
    m = members.get_member(member_id)
    missing = [f for f in ("weight_kg", "height_cm", "age", "gender") if not m.get(f)]
    if missing:
        return {"error": f"Member profile is missing: {', '.join(missing)}. Ask the user and use update_member first."}
    return nutrition.calculate_targets(m["weight_kg"], m["height_cm"], m["age"], m["gender"], activity_level, goal)


@tool
@safe
def log_progress(member_id: int, weight_kg: float | None = None,
                 body_fat_pct: float | None = None, note: str | None = None) -> dict:
    """Save a progress entry (weight, body-fat % and/or a note) for a member."""
    return progress.log_progress(member_id, weight_kg, body_fat_pct, note)


@tool
@safe
def get_progress(member_id: int, limit: int = 12) -> dict:
    """Get a member's recent progress entries and total weight change."""
    return progress.get_progress(member_id, limit)


FITNESS_TOOLS = [get_member_profile, calculate_nutrition_targets, log_progress, get_progress]
