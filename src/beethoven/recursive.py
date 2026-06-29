"""Recursive orchestration score strategies inspired by RecursiveMAS."""

from __future__ import annotations

import re
from dataclasses import replace
from hashlib import sha1
from typing import Literal

from beethoven.core import Capability, Score, Task

RecursiveStyle = Literal["sequential", "deliberation", "mixture", "distillation"]

DEFAULT_RECURSIVE_STYLE: RecursiveStyle = "deliberation"
RECURSIVE_STYLES: tuple[RecursiveStyle, ...] = (
    "sequential",
    "deliberation",
    "mixture",
    "distillation",
)
MAX_RECURSIVE_ROUNDS = 5


def create_recursive_score(
    objective: str,
    *,
    style: str = DEFAULT_RECURSIVE_STYLE,
    rounds: int = 2,
    metadata: dict[str, object] | None = None,
) -> Score:
    """Create a Beethoven score that models recursive multi-agent work.

    RecursiveMAS uses recurrent collaboration patterns between agents. Beethoven
    keeps that idea at the score layer first: every round is inspectable,
    routable, streamable, and executable by any compatible soloist.
    """

    normalized = " ".join(objective.split())
    selected_style = normalize_recursive_style(style)
    selected_rounds = clamp_recursive_rounds(rounds)
    score_id = _recursive_score_id(normalized, selected_style, selected_rounds)
    tasks = _tasks_for_style(normalized, selected_style, selected_rounds)
    return Score(
        id=score_id,
        objective=normalized,
        tasks=tuple(tasks),
        metadata={
            **(metadata or {}),
            "strategy": "recursive",
            "recursive_style": selected_style,
            "recursive_rounds": selected_rounds,
            "recursive_backend": "beethoven-score",
        },
    )


def recursive_score_from_base(
    score: Score,
    *,
    style: str = DEFAULT_RECURSIVE_STYLE,
    rounds: int = 2,
    metadata: dict[str, object] | None = None,
) -> Score:
    """Return a recursive variant while preserving base metadata."""

    recursive = create_recursive_score(
        score.objective,
        style=style,
        rounds=rounds,
        metadata={**score.metadata, **(metadata or {})},
    )
    return replace(recursive, objective=score.objective)


def normalize_recursive_style(value: str) -> RecursiveStyle:
    normalized = value.strip().lower().replace("-", "_")
    if normalized in RECURSIVE_STYLES:
        return normalized  # type: ignore[return-value]
    return DEFAULT_RECURSIVE_STYLE


def clamp_recursive_rounds(value: int) -> int:
    return max(1, min(MAX_RECURSIVE_ROUNDS, value))


def _tasks_for_style(objective: str, style: RecursiveStyle, rounds: int) -> list[Task]:
    if style == "sequential":
        return _sequential_tasks(objective, rounds)
    if style == "mixture":
        return _mixture_tasks(objective, rounds)
    if style == "distillation":
        return _distillation_tasks(objective, rounds)
    return _deliberation_tasks(objective, rounds)


def _sequential_tasks(objective: str, rounds: int) -> list[Task]:
    tasks = [
        Task(
            id="decompose",
            instruction=f"Decompose the objective into recursive work units: {objective}",
            capability=Capability.PLAN,
            metadata={"recursive_role": "planner", "round": 0},
        )
    ]
    previous = "decompose"
    for round_index in range(1, rounds + 1):
        task_id = f"execute_round_{round_index}"
        tasks.append(
            Task(
                id=task_id,
                instruction=(
                    f"Execute recursive round {round_index}. Use prior artifacts, refine the plan, "
                    "and expose remaining uncertainty."
                ),
                capability=Capability.CODE if round_index == rounds else Capability.ANALYZE,
                depends_on=(previous,),
                metadata={"recursive_role": "worker", "round": round_index},
            )
        )
        previous = task_id
    tasks.append(_synthesis_task(previous, style="sequential"))
    return tasks


def _deliberation_tasks(objective: str, rounds: int) -> list[Task]:
    tasks = [
        Task(
            id="frame_problem",
            instruction=f"Frame the objective, success criteria, constraints, and risks: {objective}",
            capability=Capability.ANALYZE,
            metadata={"recursive_role": "framer", "round": 0},
        )
    ]
    previous = "frame_problem"
    for round_index in range(1, rounds + 1):
        propose_id = f"propose_round_{round_index}"
        critique_id = f"critique_round_{round_index}"
        revise_id = f"revise_round_{round_index}"
        tasks.extend(
            [
                Task(
                    id=propose_id,
                    instruction=f"Propose solution round {round_index} from the current state.",
                    capability=Capability.PLAN if round_index == 1 else Capability.CODE,
                    depends_on=(previous,),
                    metadata={"recursive_role": "proposer", "round": round_index},
                ),
                Task(
                    id=critique_id,
                    instruction=(
                        f"Critique round {round_index}: find gaps, contradictions, unsafe assumptions, "
                        "and missing validation."
                    ),
                    capability=Capability.REVIEW,
                    depends_on=(propose_id,),
                    metadata={"recursive_role": "critic", "round": round_index},
                ),
                Task(
                    id=revise_id,
                    instruction=f"Revise round {round_index} using the critique and prior artifacts.",
                    capability=Capability.CODE if round_index == rounds else Capability.PLAN,
                    depends_on=(critique_id,),
                    metadata={"recursive_role": "reviser", "round": round_index},
                ),
            ]
        )
        previous = revise_id
    tasks.append(
        Task(
            id="validate_recursive_result",
            instruction="Validate the recursively revised result against the objective and constraints.",
            capability=Capability.VALIDATE,
            depends_on=(previous,),
            metadata={"recursive_role": "validator", "round": rounds},
        )
    )
    tasks.append(_synthesis_task("validate_recursive_result", style="deliberation"))
    return tasks


def _mixture_tasks(objective: str, rounds: int) -> list[Task]:
    tasks = [
        Task(
            id="route_experts",
            instruction=f"Identify complementary expert perspectives for this objective: {objective}",
            capability=Capability.PLAN,
            metadata={"recursive_role": "router", "round": 0},
        )
    ]
    expert_ids: list[str] = []
    for round_index in range(1, rounds + 1):
        for expert in ("analysis", "implementation", "risk"):
            task_id = f"{expert}_expert_round_{round_index}"
            expert_ids.append(task_id)
            tasks.append(
                Task(
                    id=task_id,
                    instruction=f"Produce the {expert} expert view for recursive round {round_index}.",
                    capability=_expert_capability(expert),
                    depends_on=("route_experts",),
                    metadata={"recursive_role": f"{expert}_expert", "round": round_index},
                )
            )
    tasks.append(
        Task(
            id="aggregate_mixture",
            instruction="Aggregate expert outputs, resolve conflicts, and pick the strongest path.",
            capability=Capability.SYNTHESIZE,
            depends_on=tuple(expert_ids),
            metadata={"recursive_role": "aggregator", "round": rounds},
        )
    )
    tasks.append(_synthesis_task("aggregate_mixture", style="mixture"))
    return tasks


def _distillation_tasks(objective: str, rounds: int) -> list[Task]:
    tasks = [
        Task(
            id="expert_solution",
            instruction=f"Produce a high-quality expert solution for: {objective}",
            capability=Capability.CODE,
            metadata={"recursive_role": "expert", "round": 0},
        )
    ]
    previous = "expert_solution"
    for round_index in range(1, rounds + 1):
        distill_id = f"distill_round_{round_index}"
        tasks.append(
            Task(
                id=distill_id,
                instruction=(
                    f"Distill round {round_index}: compress the expert solution into simpler, reusable, "
                    "validated instructions."
                ),
                capability=Capability.SYNTHESIZE,
                depends_on=(previous,),
                metadata={"recursive_role": "distiller", "round": round_index},
            )
        )
        previous = distill_id
    tasks.append(_synthesis_task(previous, style="distillation"))
    return tasks


def _synthesis_task(dependency: str, *, style: RecursiveStyle) -> Task:
    return Task(
        id="synthesize",
        instruction=f"Produce the final Beethoven response from the recursive {style} artifacts.",
        capability=Capability.SYNTHESIZE,
        depends_on=(dependency,),
        metadata={"recursive_role": "synthesizer"},
    )


def _expert_capability(expert: str) -> Capability:
    if expert == "implementation":
        return Capability.CODE
    if expert == "risk":
        return Capability.REVIEW
    return Capability.ANALYZE


def _recursive_score_id(objective: str, style: RecursiveStyle, rounds: int) -> str:
    safe_style = re.sub(r"[^a-z0-9]+", "-", style).strip("-")
    digest = sha1(f"{objective}|{safe_style}|{rounds}".encode("utf-8")).hexdigest()[:12]
    return f"score-recursive-{digest}"
