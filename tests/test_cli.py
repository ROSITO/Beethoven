from __future__ import annotations

import json

from beethoven.cli import main


def test_score_command_prints_json(capsys) -> None:
    exit_code = main(["score", "Build", "a", "CLI", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["objective"] == "Build a CLI"
    assert [task["id"] for task in data["tasks"]] == ["understand", "plan", "synthesize"]


def test_run_command_prints_trace(capsys) -> None:
    exit_code = main(["run", "Build", "a", "CLI"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Beethoven performed score-" in captured.out
    assert "understand:local-echo" in captured.out
    assert "synthesize:local-echo" in captured.out
