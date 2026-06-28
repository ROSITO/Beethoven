"""Command line interface for Beethoven."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from beethoven.desktop_server import serve_desktop
from beethoven.core import Score
from beethoven.desktop_state import DesktopSessionStore
from beethoven.runtime import run_objective, score_objective
from beethoven.serialization import context_to_dict, score_to_dict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="beethoven",
        description="Universal orchestration CLI for AI scores, soloists, and traces.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    score = subparsers.add_parser("score", help="Create a baseline score from an objective.")
    score.add_argument("objective", nargs="+", help="Objective to transform into a score.")
    score.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    run = subparsers.add_parser("run", help="Run a baseline score with the local echo soloist.")
    run.add_argument("objective", nargs="+", help="Objective to orchestrate.")
    run.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    desktop = subparsers.add_parser(
        "desktop",
        help="Serve the local desktop workbench.",
        description="Serve the local desktop workbench.",
    )
    desktop.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    desktop.add_argument("--port", default=4173, type=int, help="Port to bind.")
    desktop.add_argument("--open", action="store_true", help="Open the workbench in a browser.")

    sessions = subparsers.add_parser("sessions", help="Inspect local desktop session history.")
    session_subparsers = sessions.add_subparsers(dest="sessions_command", required=True)
    sessions_list = session_subparsers.add_parser("list", help="List recent desktop sessions.")
    sessions_list.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "score":
        objective = " ".join(args.objective)
        generated_score = score_objective(objective)
        if args.json:
            print(json.dumps(score_to_dict(generated_score), indent=2, ensure_ascii=False))
        else:
            print_score(generated_score)
        return 0

    if args.command == "run":
        objective = " ".join(args.objective)
        context = run_objective(objective)
        if args.json:
            print(json.dumps(context_to_dict(context), indent=2, ensure_ascii=False))
        else:
            print_run(context_to_dict(context))
        return 0

    if args.command == "desktop":
        serve_desktop(host=args.host, port=args.port, open_browser=args.open)
        return 0

    if args.command == "sessions":
        store = DesktopSessionStore()
        sessions = store.list_sessions()
        if args.sessions_command == "list":
            if args.json:
                print(json.dumps({"sessions": sessions}, indent=2, ensure_ascii=False))
            else:
                print_sessions(sessions)
            return 0

    parser.print_help(sys.stderr)
    return 2


def print_score(score: Score) -> None:
    data = score_to_dict(score)
    print(f"Score: {data['id']}")
    print(f"Objective: {data['objective']}")
    print()
    for task in data["tasks"]:
        dependencies = ", ".join(task["depends_on"]) or "none"
        print(f"- {task['id']} [{task['capability']}]")
        print(f"  depends_on: {dependencies}")
        print(f"  instruction: {task['instruction']}")


def print_run(data: dict[str, object]) -> None:
    score = data["score"]
    assert isinstance(score, dict)
    print(f"Beethoven performed {score['id']}")
    print(f"Objective: {score['objective']}")
    print()
    print("Trace")
    for event in data["trace"]:
        print(f"- {event}")
    print()
    print("Statuses")
    statuses = data["statuses"]
    assert isinstance(statuses, dict)
    for task_id, status in statuses.items():
        print(f"- {task_id}: {status}")


def print_sessions(sessions: list[dict[str, object]]) -> None:
    if not sessions:
        print("No desktop sessions yet.")
        return

    for session in sessions:
        title = session.get("title", "Untitled score")
        score_id = session.get("score_id", session.get("id", "unknown"))
        project = session.get("project", "Beethoven")
        branch = session.get("branch", "main")
        status = session.get("status", "unknown")
        print(f"- {title} [{status}]")
        print(f"  score: {score_id} · project: {project} · branch: {branch}")


if __name__ == "__main__":
    raise SystemExit(main())
