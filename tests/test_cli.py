from __future__ import annotations

import json

from beethoven.cli import main
from beethoven.desktop_state import DesktopSessionStore
from beethoven.runtime import run_objective


def test_score_command_prints_json(capsys) -> None:
    exit_code = main(["score", "Build", "a", "CLI", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["objective"] == "Build a CLI"
    assert [task["id"] for task in data["tasks"]] == ["understand", "plan", "synthesize"]


def test_run_command_prints_trace(capsys) -> None:
    exit_code = main(["run", "Build", "a", "CLI", "--permission", "read-only", "--effort", "high"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Beethoven performed score-" in captured.out
    assert "permission=read-only" in captured.out
    assert "effort=high" in captured.out
    assert "understand:local-echo" in captured.out
    assert "synthesize:local-echo" in captured.out


def test_desktop_command_is_registered(capsys) -> None:
    try:
        main(["desktop", "--help"])
    except SystemExit as error:
        assert error.code == 0

    captured = capsys.readouterr()
    assert "Serve the local desktop workbench" in captured.out
    assert "--open" in captured.out


def test_sessions_list_command_prints_history(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("BEETHOVEN_HOME", str(tmp_path))
    store = DesktopSessionStore()
    session = store.save_run(run_objective("review desktop session history"))

    exit_code = main(["sessions", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "review desktop session history" in captured.out
    assert "project: Beethoven" in captured.out

    show_exit_code = main(["sessions", "show", session["id"]])
    show_captured = capsys.readouterr()
    assert show_exit_code == 0
    assert "Session: review desktop session history" in show_captured.out
    assert "Trace" in show_captured.out


def test_soloists_list_command_prints_catalog(capsys) -> None:
    exit_code = main(["soloists", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Local Echo [available]" in captured.out
    assert "Ollama [planned]" in captured.out


def test_skills_list_command_prints_capability_catalog(capsys) -> None:
    exit_code = main(["skills", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Analyze [available]" in captured.out
    assert "available: Local Echo" in captured.out


def test_workspace_command_prints_current_project(capsys) -> None:
    exit_code = main(["workspace"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Workspace: Beethoven" in captured.out
    assert "Git:" in captured.out


def test_package_sidecar_command_writes_launcher(tmp_path, capsys) -> None:
    output = tmp_path / "beethoven-sidecar"

    exit_code = main(["package", "sidecar", "--output", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Sidecar launcher written" in captured.out
    assert output.exists()
    assert "beethoven desktop" in output.read_text(encoding="utf-8")
    assert output.stat().st_mode & 0o111
