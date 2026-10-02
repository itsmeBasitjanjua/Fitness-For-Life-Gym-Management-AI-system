"""Tools for the ANALYTICS agent (owner only): dashboard and read-only SQL questions."""
from langchain_core.tools import tool

from gym_ai.services import analytics, reports
from gym_ai.tools._helpers import safe


@tool
@safe
def dashboard_stats() -> dict:
    """Snapshot of the gym: member counts, expiring/expired, today's visits, revenue and expenses this month."""
    return reports.dashboard_stats()


@tool
@safe
def get_database_schema() -> str:
    """Return the database tables and columns. Call this before writing SQL."""
    return analytics.database_schema()


@tool
@safe
def run_sql_query(sql: str) -> dict:
    """Run ONE read-only SELECT query on the gym database (max 100 rows). Use for questions the other tools cannot answer."""
    return analytics.run_read_only_query(sql)


ANALYTICS_TOOLS = [dashboard_stats, get_database_schema, run_sql_query]
