"""
The LangGraph workflow - the heart of the system.

                       +--> members ----+
                       +--> billing ----+
   START -> supervisor +--> finance ----+--> END
                       +--> fitness ----+
                       +--> operations -+
                       +--> analytics --+
                       +--> general ----+
                       +--> access_denied

1. The SUPERVISOR (Claude with structured output) picks the right specialist.
2. A permission check compares that choice with the user's role.
3. The SPECIALIST agent runs its tools and writes the answer.
4. A checkpointer remembers the conversation per thread_id.
"""
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel, Field

from gym_ai.agents import prompts
from gym_ai.agents.llm import get_llm
from gym_ai.agents.roles import ALL_AGENTS, allowed_agents
from gym_ai.agents.specialists import build_specialists


class GymState(MessagesState):
    """Shared memory passed between nodes. `messages` comes from MessagesState."""
    role: str          # owner / admin / trainer / member - who is chatting
    next_agent: str    # filled in by the supervisor


class RouteDecision(BaseModel):
    """What the supervisor must answer with."""
    agent: Literal["members", "billing", "finance", "fitness", "operations", "analytics", "general"] = Field(
        description="The agent that should handle the latest user message")
    reason: str = Field(description="One short sentence explaining the choice")


def message_text(message) -> str:
    """Claude may return text as a list of blocks - always give back plain text."""
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(block.get("text", "") for block in content if isinstance(block, dict))


def _conversation_for_routing(messages) -> list:
    """Only the human messages and final AI answers (no tool calls) - enough to pick a route."""
    kept = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            kept.append(msg)
        elif isinstance(msg, AIMessage) and not msg.tool_calls and message_text(msg).strip():
            kept.append(msg)
    return kept[-8:]


def build_graph(llm=None, checkpointer=None):
    """Create and compile the whole system. Pass your own `llm` for testing."""
    llm = llm or get_llm()
    specialists = build_specialists(llm)
    # json_schema mode is the method current Claude models support for structured output
    router = llm.with_structured_output(RouteDecision, method="json_schema")

    # ---- node 1: supervisor ----
    def supervisor(state: GymState) -> dict:
        role = state.get("role", "member")
        decision = router.invoke([SystemMessage(content=prompts.SUPERVISOR_PROMPT),
                                  *_conversation_for_routing(state["messages"])])
        chosen = decision.agent if decision else "general"
        if chosen not in allowed_agents(role):
            chosen = "access_denied"
        return {"next_agent": chosen}

    # ---- node: general chat (no tools) ----
    def general(state: GymState) -> dict:
        reply = llm.invoke([SystemMessage(content=prompts.GENERAL_PROMPT),
                            *_conversation_for_routing(state["messages"])])
        return {"messages": [reply]}

    # ---- node: access denied (no AI call needed) ----
    def access_denied(state: GymState) -> dict:
        role = state.get("role", "member")
        allowed = ", ".join(a for a in allowed_agents(role) if a != "general") or "general questions"
        text = (f"Sorry, your role ({role}) does not have access to that. "
                f"You can ask me about: {allowed}.")
        return {"messages": [AIMessage(content=text)]}

    # ---- wire everything together ----
    builder = StateGraph(GymState)
    builder.add_node("supervisor", supervisor)
    for name, agent in specialists.items():
        builder.add_node(name, agent)
    builder.add_node("general", general)
    builder.add_node("access_denied", access_denied)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", lambda s: s["next_agent"],
                                  [*ALL_AGENTS, "access_denied"])
    for name in [*ALL_AGENTS, "access_denied"]:
        builder.add_edge(name, END)

    return builder.compile(checkpointer=checkpointer or MemorySaver())


def ask(graph, text: str, role: str = "owner", thread_id: str = "default") -> str:
    """Convenience wrapper: send one message, get the answer as text."""
    result = graph.invoke(
        {"messages": [HumanMessage(content=text)], "role": role},
        config={"configurable": {"thread_id": thread_id}},
    )
    return message_text(result["messages"][-1])
