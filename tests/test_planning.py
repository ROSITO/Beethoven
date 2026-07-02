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
                  "depends_on": ["inspect_context"],
                  "soloist": "codex-cli"
                }
              ]
            }
            """
        )


def test_dynamic_planner_creates_valid_score() -> None:
    score = create_dynamic_score(
        "Improve the app",
        FakePlanner(),
        metadata={"available_soloists": [{"id": "codex-cli", "status": "available"}]},
    )

    assert score.metadata["planning_mode"] == "dynamic"
    assert score.metadata["planner"] == "fake-planner"
    assert [task.id for task in score.tasks] == [
        "inspect_context",
        "draft_changes",
        "synthesize",
    ]
    assert score.tasks[1].depends_on == ("inspect_context",)
    assert score.tasks[1].metadata["preferred_soloist"] == "codex-cli"
    assert score.tasks[-1].capability == Capability.SYNTHESIZE
    assert "available_soloists" not in score.metadata


def test_dynamic_planner_drops_unavailable_soloist_hint() -> None:
    score = create_dynamic_score(
        "Improve the app",
        FakePlanner(),
        metadata={"available_soloists": [{"id": "local-echo", "status": "available"}]},
    )

    assert "preferred_soloist" not in score.tasks[1].metadata


def test_dynamic_planner_repairs_control_characters_inside_json_strings() -> None:
    @dataclass(frozen=True)
    class NewlinePlanner:
        name: str = "newline-planner"
        capabilities: frozenset[Capability] = frozenset({Capability.PLAN})

        def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
            return SoloistResult(
                output='{"tasks":[{"id":"inspect","capability":"analyze","instruction":"Inspect line one\nline two","depends_on":[]}]}'
            )

    score = create_dynamic_score("Improve the app", NewlinePlanner())

    assert score.metadata["planning_mode"] == "dynamic"
    assert score.tasks[0].instruction == "Inspect line one\nline two"
    assert score.tasks[-1].id == "synthesize"


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


def test_dynamic_planner_falls_back_when_planner_raises() -> None:
    @dataclass(frozen=True)
    class RaisingPlanner:
        name: str = "raising-planner"
        capabilities: frozenset[Capability] = frozenset({Capability.PLAN})

        def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
            raise RuntimeError("model unavailable")

    score = create_dynamic_score("Improve the app", RaisingPlanner())

    assert score.metadata["planning_mode"] == "baseline_fallback"
    assert score.metadata["planner_error"] == "model unavailable"
    assert [task.id for task in score.tasks] == ["understand", "plan", "synthesize"]
