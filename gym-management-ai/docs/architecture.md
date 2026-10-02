# Architecture

## Layers (read bottom-up)

| Layer | Folder | Knows about AI? | Purpose |
|---|---|---|---|
| Data | `gym_ai/database.py` | No | SQLite schema and connections |
| Business logic | `gym_ai/services/` | No | Rules: payments extend memberships, salary paid once per month, etc. |
| Tools | `gym_ai/tools/` | Yes (LangChain `@tool`) | Wrap services so Claude can call them; errors become readable results |
| Agents | `gym_ai/agents/` | Yes | Prompts, roles, specialist agents and the LangGraph workflow |
| Interfaces | `main.py`, `api.py` | - | CLI and web API |

Keeping the AI out of the services means every rule can be unit-tested with plain `pytest`.

## The graph (`agents/graph.py`)

State (`GymState`): `messages`, `role`, `next_agent`.

Nodes: `supervisor` -> one of `members | billing | finance | fitness | operations | analytics | general | access_denied` -> `END`.

- `supervisor` calls Claude with structured output (`RouteDecision`) and writes `next_agent`.
- If `next_agent` is not in `ROLE_PERMISSIONS[role]` it is replaced with `access_denied`.
- Specialists are `langchain.agents.create_agent` agents embedded as graph nodes.
- A `MemorySaver` checkpointer stores history per `thread_id`.

## Payment flow

`record_payment(member, amount, method)` -> validate method/amount -> if the member has a plan, add
`floor(amount / fee) * duration` days starting at the later of the payment date and current expiry ->
store amount, method, exact `paid_at` timestamp and a receipt number such as `RCPT-20260902-0006`.

## Adding a feature

1. Add the rule in `services/<topic>.py` and a test in `tests/`.
2. Wrap it in `tools/<topic>_tools.py` with `@tool` + `@safe` and a clear docstring (Claude reads it).
3. Add the tool to the right list at the bottom of that file.
4. If it needs a new agent: add a prompt in `prompts.py`, register it in `specialists.py`, `roles.py`, `graph.py` (`RouteDecision` and the supervisor prompt).
