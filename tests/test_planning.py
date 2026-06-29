from __future__ import annotations

from dataclasses import dataclass

from beethoven.core import Capability, ExecutionContext, SoloistResult, Task
from beethoven.planning import create_dynamic_score


@dataclass(frozen=True)
class FakePlanner:
    name: str = "fake-planner"
    capabilities: frozenset[Capability] = frozenset({Capability.PLAN})

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        return SoloistResult(
            output="""
            {
              "tasks": [
                {
                  "id": "inspect_context",
                  "capability": "analyze",
                  "instruction": "Inspect the attached files and identify constraints.",
                  "depends_on": []
                },
                {
                  "id": "draft_changes",
                  "capability": "code",
                  "instruction": "Draft the implementation approach.",
                  "depends_on": ["inspect_context"]
                }
              ]
            }
            """
        )


def test_dynamic_planner_creates_valid_score() -> None:
    score = create_dynamic_score("Improve the app", FakePlanner())

    assert score.metadata["planning_mode"] == "dynamic"
    assert score.metadata["planner"] == "fake-planner"
    assert [task.id for task in score.tasks] == [
        "inspect_context",
        "draft_changes",
        "synthesize",
    ]
    assert score.tasks[1].depends_on == ("inspect_context",)
    assert score.tasks[-1].capability == Capability.SYNTHESIZE


def test_dynamic_planner_falls_back_to_baseline_on_invalid_json() -> None:
    @dataclass(frozen=True)
    class BrokenPlanner:
        name: str = "broken-planner"
        capabilities: frozenset[Capability] = frozenset({Capability.PLAN})

        def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
            return SoloistResult(output="not json")

    score = create_dynamic_score("Improve the app", BrokenPlanner())

    assert score.metadata["planning_mode"] == "baseline_fallback"
    assert [task.id for task in score.tasks] == ["understand", "plan", "synthesize"]
