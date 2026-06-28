"""Command line interface for Beethoven."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from beethoven.conductor import Conductor
from beethoven.core import Score
from beethoven.planning import create_baseline_score
from beethoven.routing import CapabilityRouter, SoloistRegistry
from beethoven.serialization import context_to_dict, score_to_dict
from beethoven.soloists import EchoSoloist


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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    objective = " ".join(args.objective)

    if args.command == "score":
        generated_score = create_baseline_score(objective)
        if args.json:
            print(json.dumps(score_to_dict(generated_score), indent=2, ensure_ascii=False))
        else:
            print_score(generated_score)
        return 0

    if args.command == "run":
        generated_score = create_baseline_score(objective)
        registry = SoloistRegistry()
        registry.register(EchoSoloist())
        context = Conductor(CapabilityRouter(registry)).perform(generated_score)
        if args.json:
            print(json.dumps(context_to_dict(context), indent=2, ensure_ascii=False))
        else:
            print_run(context_to_dict(context))
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
