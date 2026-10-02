"""Tools every agent can use."""
from langchain_core.tools import tool

from gym_ai.utils import now_str


@tool
def get_current_datetime() -> str:
    """Get the current date and time at the gym (YYYY-MM-DD HH:MM:SS). Use it to resolve 'today' or 'this month'."""
    return now_str()


COMMON_TOOLS = [get_current_datetime]
