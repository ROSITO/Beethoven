from __future__ import annotations

from dataclasses import dataclass

import pytest

from beethoven import (
    Capability,
    CapabilityRouter,
    Conductor,
    ExecutionContext,
    Score,
    SoloistRegistry,
    SoloistResult,
    Task,
    TaskStatus,
)
from beethoven.conductor import InvalidScoreError


@dataclass(frozen=True)
class FakeSoloist:
    name: str
    capabilities: frozenset[Capability]

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        return SoloistResult(output=f"{self.name}:{task.instruction}")


def test_conductor_executes_score_in_dependency_order() -> None:
    registry = SoloistRegistry()
    registry.register(FakeSoloist("planner", frozenset({Capability.PLAN})))
    registry.register(FakeSoloist("coder", frozenset({Capability.CODE})))

    score = Score(
        id="score-1",
        objective="Create a tiny feature",
        tasks=(
            Task(id="plan", instruction="Plan the work", capability=Capability.PLAN),
            Task(
                id="code",
                instruction="Implement the work",
                capability=Capability.CODE,
                depends_on=("plan",),
            ),
        ),
    )

    context = Conductor(CapabilityRouter(registry)).perform(score)

    assert context.trace == ["plan:planner", "code:coder"]
    assert context.statuses == {
        "plan": TaskStatus.COMPLETED,
        "code": TaskStatus.COMPLETED,
    }
    assert context.artifacts["code"].output == "coder:Implement the work"


def test_conductor_rejects_unknown_dependencies() -> None:
    registry = SoloistRegistry()
    registry.register(FakeSoloist("planner", frozenset({Capability.PLAN})))
    score = Score(
        id="score-1",
        objective="Invalid plan",
        tasks=(
            Task(
                id="plan",
                instruction="Plan the work",
                capability=Capability.PLAN,
                depends_on=("missing",),
            ),
        ),
    )

    with pytest.raises(InvalidScoreError, match="unknown dependencies"):
        Conductor(CapabilityRouter(registry)).perform(score)
