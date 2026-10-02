"""
A tiny stand-in for Claude so the LangGraph wiring can be tested WITHOUT an API key.

It routes by keywords and, for a few messages, asks for a tool call - exactly
what the real model would do. This tests our graph, tools and permissions,
not Claude's intelligence.
"""
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda


def _last_human_text(messages) -> str:
    humans = [m for m in messages if isinstance(m, HumanMessage)]
    return humans[-1].content.lower() if humans else ""


def _route(messages) -> str:
    text = _last_human_text(messages)
    if "salary" in text or "report" in text:
        return "finance"
    if "payment" in text or "paid" in text:
        return "billing"
    if "workout" in text:
        return "fitness"
    return "general"


class FakeClaude(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "fake-claude"

    def bind_tools(self, tools, **kwargs):
        return self

    def with_structured_output(self, schema, **kwargs):
        return RunnableLambda(lambda messages: schema(agent=_route(messages), reason="keyword match"))

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        if isinstance(messages[-1], ToolMessage):                      # tool finished -> final answer
            reply = AIMessage(content=f"TOOL RESULT: {messages[-1].content}")
        else:
            text = _last_human_text(messages)
            if "payment" in text:
                call = {"name": "record_payment", "id": "call_1",
                        "args": {"member_id": 1, "amount": 5000, "method": "cash"}}
                reply = AIMessage(content="", tool_calls=[call])
            elif "salary" in text:
                call = {"name": "pay_salary", "id": "call_2", "args": {"staff_id": 1, "month": "2026-09"}}
                reply = AIMessage(content="", tool_calls=[call])
            else:
                reply = AIMessage(content="Hello from the fake model.")
        return ChatResult(generations=[ChatGeneration(message=reply)])
