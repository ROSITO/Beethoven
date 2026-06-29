from __future__ import annotations

import sys

from beethoven.recursive import create_recursive_score
from beethoven.runtime import list_soloists, run_objective, score_objective


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


def test_recursivemas_sidecar_executes_recursive_score(tmp_path, monkeypatch) -> None:
    sidecar = tmp_path / "recursivemas_sidecar.py"
    sidecar.write_text(
        """
from __future__ import annotations

import json
import sys

payload = json.loads(sys.stdin.read())
task = payload["task"]
print(json.dumps({
    "output": f"sidecar:{task['id']}:{task['capability']}",
    "metadata": {"backend": "fake-recursivemas"},
    "tokens": 7,
}))
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("BEETHOVEN_RECURSIVEMAS_COMMAND", f"{sys.executable} {sidecar}")

    soloists = list_soloists()
    context = run_objective(
        "Use RecursiveMAS backend",
        soloist="recursivemas",
        strategy="recursive",
        recursive_style="sequential",
        recursive_rounds=1,
    )

    assert next(item for item in soloists if item["id"] == "recursivemas")["status"] == "available"
    assert context.trace == [
        "decompose:recursivemas",
        "execute_round_1:recursivemas",
        "synthesize:recursivemas",
    ]
    assert context.artifacts["decompose"].output == "sidecar:decompose:plan"
    assert context.artifacts["synthesize"].metadata["backend"] == "fake-recursivemas"
    assert context.artifacts["synthesize"].tokens == 7


def test_recursive_strategy_prefers_recursivemas_when_available(tmp_path, monkeypatch) -> None:
    sidecar = tmp_path / "recursivemas_sidecar.py"
    sidecar.write_text(
        """
from __future__ import annotations

import json
import sys

payload = json.loads(sys.stdin.read())
task = payload["task"]
print(json.dumps({
    "output": f"auto:{task['id']}:{task['metadata'].get('preferred_soloist')}",
    "metadata": {"backend": "fake-recursivemas"},
}))
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("BEETHOVEN_RECURSIVEMAS_COMMAND", f"{sys.executable} {sidecar}")

    context = run_objective(
        "Coordinate recursive backend automatically",
        strategy="recursive",
        recursive_style="sequential",
        recursive_rounds=1,
    )

    assert context.score.metadata["recursive_backend"] == "recursivemas"
    assert all(task.metadata["preferred_soloist"] == "recursivemas" for task in context.score.tasks)
    assert context.trace == [
        "decompose:recursivemas",
        "execute_round_1:recursivemas",
        "synthesize:recursivemas",
    ]
