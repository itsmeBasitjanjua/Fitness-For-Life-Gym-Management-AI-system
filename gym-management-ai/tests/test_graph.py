"""Tests for the LangGraph workflow: routing, tools, permissions and safety gates."""
import pytest

from gym_ai.agents.graph import ask, build_graph
from gym_ai.database import get_connection
from gym_ai.services import members, plans, staff
from tests.fake_llm import FakeClaude


@pytest.fixture
def graph():
    return build_graph(llm=FakeClaude())


@pytest.fixture
def setup_data():
    plan = plans.add_plan("Monthly", 30, 5000)
    members.add_member("Graph Tester", "0300-9999999", plan["id"])
    staff.add_staff("Coach", "Trainer", 40000)


def _count(table: str) -> int:
    with get_connection() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_owner_payment_request_runs_billing_tool(graph, setup_data):
    reply = ask(graph, "Record a payment for member 1", role="owner")
    assert "RCPT-" in reply                      # the tool ran and returned a receipt
    assert _count("payments") == 1


def test_trainer_cannot_reach_finance(graph, setup_data):
    reply = ask(graph, "Pay the salary", role="trainer")
    assert "does not have access" in reply
    assert _count("salary_payments") == 0


def test_salary_needs_confirmation_before_money_moves(graph, setup_data):
    reply = ask(graph, "Pay the salary", role="owner")
    assert "needs_confirmation" in reply or "explicit approval" in reply
    assert _count("salary_payments") == 0        # nothing paid without confirmed=True


def test_unknown_role_is_limited(graph, setup_data):
    assert "does not have access" in ask(graph, "Record a payment", role="stranger")


def test_conversation_memory_is_kept_per_thread(graph, setup_data):
    ask(graph, "hello", role="owner", thread_id="t1")
    ask(graph, "hello again", role="owner", thread_id="t1")
    state = graph.get_state({"configurable": {"thread_id": "t1"}})
    assert len(state.values["messages"]) == 4    # 2 questions + 2 answers
