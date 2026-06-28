"""Command line interface for Beethoven."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from beethoven.desktop_server import serve_desktop
from beethoven.core import Score
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
        serve_desktop(host=args.host, port=args.port)
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


if __name__ == "__main__":
    raise SystemExit(main())
