"""
Who may talk to which agent (role-based access control).

The supervisor checks this BEFORE any specialist runs, so a trainer asking
"show me the salaries" is stopped even if the AI would have understood it.
"""
ALL_AGENTS = ["members", "billing", "finance", "fitness", "operations", "analytics", "general"]

ROLE_PERMISSIONS = {
    "owner":   ["members", "billing", "finance", "fitness", "operations", "analytics", "general"],
    "admin":   ["members", "billing", "fitness", "operations", "general"],
    "trainer": ["fitness", "operations", "general"],
    "member":  ["fitness", "general"],
}


def allowed_agents(role: str) -> list[str]:
    """Agents this role may use. Unknown roles get the safest option: general chat only."""
    return ROLE_PERMISSIONS.get(role, ["general"])
