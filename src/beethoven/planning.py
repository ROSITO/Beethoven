"""Baseline planning helpers for the first CLI loop."""

from __future__ import annotations

from hashlib import sha1

from beethoven.core import Capability, Score, Task


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
