"""Planning helpers for baseline and model-proposed scores."""

from __future__ import annotations

import json
import os
import re
from dataclasses import replace
from hashlib import sha1
from typing import Any

from beethoven.core import Capability, ExecutionContext, Score, Soloist, Task


MAX_DYNAMIC_TASKS = 6
PLANNER_SOLOISTS = {"claude-cli", "codex-cli"}


def create_baseline_score(objective: str) -> Score:
    """Create a small portable score from a user objective.

    This is deliberately deterministic. Later planners can replace it with a
    model-backed planner while preserving the same Score contract.
    """

    normalized = " ".join(objective.split())
    score_id = sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return Score(
        id=f"score-{score_id}",
        objective=normalized,
        tasks=(
            Task(
                id="understand",
                instruction=f"Clarify the intent, constraints, and risks for: {normalized}",
                capability=Capability.ANALYZE,
            ),
            Task(
                id="plan",
                instruction="Create an execution score with clear dependencies and validation gates.",
                capability=Capability.PLAN,
                depends_on=("understand",),
            ),
            Task(
                id="synthesize",
                instruction="Produce the final symphony from the completed artifacts.",
                capability=Capability.SYNTHESIZE,
                depends_on=("plan",),
            ),
        ),
    )


def should_use_dynamic_planning(soloist: str) -> bool:
    """Return whether a selected soloist can propose the score itself."""
    enabled = os.getenv("BEETHOVEN_DYNAMIC_PLANNING", "1").lower() not in {"0", "false", "no"}
    return enabled and soloist in PLANNER_SOLOISTS


def create_dynamic_score(objective: str, planner: Soloist, metadata: dict[str, object] | None = None) -> Score:
    """Ask a planner soloist for a score, then validate and normalize it.

    The model proposes structure, but Beethoven owns the contract: capabilities,
    dependencies, task count, and fallback behavior stay deterministic.
    """
    baseline = create_baseline_score(objective)
    planning_task = Task(
        id="compose_score",
        instruction=_planner_instruction(objective, metadata or {}),
        capability=Capability.PLAN,
    )
    context = ExecutionContext(score=replace(baseline, metadata=metadata or {}))
    result = planner.perform(planning_task, context)
    try:
        proposed = _extract_json_object(str(result.output))
        tasks = _tasks_from_payload(proposed)
    except (ValueError, TypeError, KeyError):
        return replace(
            baseline,
            metadata={
                **baseline.metadata,
                **(metadata or {}),
                "planning_mode": "baseline_fallback",
                "planner": planner.name,
                "planner_error": "Planner output could not be converted to a valid score.",
            },
        )

    return replace(
        baseline,
        tasks=tuple(tasks),
        metadata={
            **baseline.metadata,
            **(metadata or {}),
            "planning_mode": "dynamic",
            "planner": planner.name,
        },
    )


def _planner_instruction(objective: str, metadata: dict[str, object]) -> str:
    attachments = metadata.get("attachments", [])
    attachment_summary = "\n".join(
        f"- {item.get('path')} ({item.get('status')})"
        for item in attachments
        if isinstance(item, dict)
    )
    return f"""
Create a Beethoven orchestration score for this objective:
{objective}

Return only a JSON object with this shape:
{{
  "tasks": [
    {{
      "id": "short_snake_case",
      "capability": "analyze|plan|code|review|validate|synthesize|tool_use",
      "instruction": "clear task instruction",
      "depends_on": ["previous_task_id"]
    }}
  ]
}}

Rules:
- Use 3 to {MAX_DYNAMIC_TASKS} tasks.
- Keep task ids unique, lowercase snake_case.
- Start with analysis/planning when useful.
- End with a synthesize task.
- Only depend on earlier tasks.
- Do not include markdown outside the JSON.

Attached context:
{attachment_summary or "none"}
""".strip()


def _extract_json_object(value: str) -> dict[str, Any]:
    stripped = value.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    elif "{" in stripped and "}" in stripped:
        stripped = stripped[stripped.find("{") : stripped.rfind("}") + 1]
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError("Planner output must be a JSON object")
    return payload


def _tasks_from_payload(payload: dict[str, Any]) -> list[Task]:
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list):
        raise ValueError("Planner output must include tasks")

    tasks: list[Task] = []
    known_ids: set[str] = set()
    for index, item in enumerate(raw_tasks[:MAX_DYNAMIC_TASKS]):
        if not isinstance(item, dict):
            continue
        task_id = _normalize_task_id(str(item.get("id") or f"task_{index + 1}"))
        if not task_id or task_id in known_ids:
            task_id = f"task_{index + 1}"
        capability = _normalize_capability(str(item.get("capability", "analyze")))
        instruction = str(item.get("instruction") or item.get("description") or "").strip()
        if not instruction:
            instruction = f"Perform {capability.value} work for this objective."
        depends_on = tuple(
            dependency
            for dependency in item.get("depends_on", [])
            if isinstance(dependency, str) and dependency in known_ids
        )
        tasks.append(
            Task(
                id=task_id,
                instruction=instruction,
                capability=capability,
                depends_on=depends_on,
            )
        )
        known_ids.add(task_id)

    if not tasks:
        raise ValueError("Planner output did not include valid tasks")
    if tasks[-1].capability != Capability.SYNTHESIZE:
        if len(tasks) >= MAX_DYNAMIC_TASKS:
            tasks = tasks[: MAX_DYNAMIC_TASKS - 1]
        tasks.append(
            Task(
                id="synthesize",
                instruction="Produce the final answer from the completed artifacts.",
                capability=Capability.SYNTHESIZE,
                depends_on=(tasks[-1].id,),
            )
        )
    return tasks[:MAX_DYNAMIC_TASKS]


def _normalize_task_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized[:48]


def _normalize_capability(value: str) -> Capability:
    normalized = value.strip().lower().replace("-", "_")
    try:
        return Capability(normalized)
    except ValueError:
        return Capability.ANALYZE
