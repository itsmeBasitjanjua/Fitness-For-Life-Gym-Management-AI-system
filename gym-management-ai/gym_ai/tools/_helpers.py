"""Shared helper for all tools."""
import functools

from gym_ai.utils import GymError


def safe(func):
    """
    Turn business errors into a result the AI can read.

    Without this, a mistake like "Member 99 not found" would crash the agent.
    With it, the AI receives {"error": "Member 99 not found."} and can explain
    it to the user or ask for the missing detail.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except GymError as error:
            return {"error": str(error)}
    return wrapper


def needs_confirmation(action: str) -> dict:
    """Standard reply for sensitive actions that were not confirmed by the user yet."""
    return {
        "needs_confirmation": True,
        "message": f"This action needs explicit approval: {action}. "
                   "Ask the user to confirm, then call the tool again with confirmed=True.",
    }
