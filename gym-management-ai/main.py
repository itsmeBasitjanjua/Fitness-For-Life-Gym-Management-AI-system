"""
Command-line entry point.

    python main.py chat --role owner       # talk to the AI (needs ANTHROPIC_API_KEY)
    python main.py report --month 2026-09  # make the PDF report (no AI needed)
    python main.py dashboard               # print quick numbers (no AI needed)

Roles: owner, admin, trainer, member  (see gym_ai/agents/roles.py)
"""
import argparse
import json
import os
import sys

from gym_ai.database import init_db
from gym_ai.services import pdf_report, reports


def run_chat(role: str, thread_id: str) -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    from gym_ai.agents.graph import ask, build_graph   # imported here so other commands work without a key

    graph = build_graph()
    print(f"Gym AI ready (role: {role}). Type 'exit' to quit.\n")
    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in ("exit", "quit"):
            break
        if text:
            print(f"\nAssistant: {ask(graph, text, role, thread_id)}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gym AI management system")
    sub = parser.add_subparsers(dest="command")

    chat = sub.add_parser("chat", help="chat with the AI agents")
    chat.add_argument("--role", default="owner", choices=["owner", "admin", "trainer", "member"])
    chat.add_argument("--thread", default="cli-session", help="conversation id (keeps memory)")

    report = sub.add_parser("report", help="create the monthly PDF report")
    report.add_argument("--month", help="YYYY-MM (default: current month)")

    sub.add_parser("dashboard", help="print gym statistics")

    args = parser.parse_args()
    init_db()
    if args.command == "report":
        print("PDF created:", pdf_report.generate_monthly_pdf(args.month))
    elif args.command == "dashboard":
        print(json.dumps(reports.dashboard_stats(), indent=2))
    else:  # default = chat
        run_chat(getattr(args, "role", "owner"), getattr(args, "thread", "cli-session"))


if __name__ == "__main__":
    main()
