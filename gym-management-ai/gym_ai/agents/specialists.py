"""
Builds the specialist agents.

Each specialist is a ready-made LangChain "tool-calling agent": Claude decides
which tools to call, reads the results, and answers. They only differ in their
prompt and the tools they are given.
"""
from langchain.agents import create_agent

from gym_ai.agents import prompts
from gym_ai.tools import (ANALYTICS_TOOLS, BILLING_TOOLS, COMMON_TOOLS, FINANCE_TOOLS,
                          FITNESS_TOOLS, MEMBER_TOOLS, OPERATIONS_TOOLS)


def build_specialists(llm) -> dict:
    """Return {agent_name: compiled_agent}. The names match roles.py."""
    def make(prompt, tools, name):
        return create_agent(llm, tools=tools + COMMON_TOOLS, system_prompt=prompt, name=name)

    # `search`-style helper tools are shared: billing/fitness/operations can look members up too.
    lookup = [t for t in MEMBER_TOOLS if t.name in ("search_members", "get_member")]

    return {
        "members": make(prompts.MEMBERS_PROMPT, MEMBER_TOOLS, "members"),
        "billing": make(prompts.BILLING_PROMPT, BILLING_TOOLS + lookup, "billing"),
        "finance": make(prompts.FINANCE_PROMPT, FINANCE_TOOLS, "finance"),
        "fitness": make(prompts.FITNESS_PROMPT, FITNESS_TOOLS + [t for t in lookup if t.name == "search_members"] +
                        [t for t in MEMBER_TOOLS if t.name == "update_member"], "fitness"),
        "operations": make(prompts.OPERATIONS_PROMPT, OPERATIONS_TOOLS + lookup, "operations"),
        "analytics": make(prompts.ANALYTICS_PROMPT, ANALYTICS_TOOLS, "analytics"),
    }
