from __future__ import annotations

from beethoven.recursive import create_recursive_score
from beethoven.runtime import run_objective, score_objective


def test_recursive_score_creates_deliberation_rounds() -> None:
    score = create_recursive_score("Integrate RecursiveMAS", style="deliberation", rounds=2)

    assert score.id.startswith("score-recursive-")
    assert score.metadata["strategy"] == "recursive"
    assert score.metadata["recursive_style"] == "deliberation"
    assert score.metadata["recursive_rounds"] == 2
    assert [task.id for task in score.tasks] == [
        "frame_problem",
        "propose_round_1",
        "critique_round_1",
        "revise_round_1",
        "propose_round_2",
        "critique_round_2",
        "revise_round_2",
        "validate_recursive_result",
        "synthesize",
    ]
    assert score.tasks[-1].depends_on == ("validate_recursive_result",)


def test_score_objective_supports_recursive_strategy() -> None:
    score = score_objective(
        "Review architecture",
        strategy="recursive",
        recursive_style="mixture",
        recursive_rounds=1,
    )

    assert score.metadata["recursive_style"] == "mixture"
    assert "aggregate_mixture" in score.task_ids()
    assert score.tasks[-1].id == "synthesize"


def test_run_objective_executes_recursive_score() -> None:
    context = run_objective(
        "Ship recursive mode",
        strategy="recursive",
        recursive_style="sequential",
        recursive_rounds=1,
    )

    assert context.score.metadata["strategy"] == "recursive"
    assert context.trace == [
        "decompose:local-echo",
        "execute_round_1:local-echo",
        "synthesize:local-echo",
    ]
    assert context.statuses["synthesize"] == "completed"
