from __future__ import annotations

import json
import os
import subprocess
import sys

from beethoven.cli import main, run_terminal_session
from beethoven.desktop_state import DesktopSessionStore
from beethoven.runtime import list_soloists, run_objective


def test_score_command_prints_json(capsys) -> None:
    exit_code = main(["score", "Build", "a", "CLI", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["objective"] == "Build a CLI"
    assert [task["id"] for task in data["tasks"]] == ["understand", "plan", "synthesize"]


def test_score_command_can_print_recursive_json(capsys) -> None:
    exit_code = main(
        [
            "score",
            "Integrate",
            "RecursiveMAS",
            "--strategy",
            "recursive",
            "--recursive-style",
            "sequential",
            "--recursive-rounds",
            "1",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["metadata"]["strategy"] == "recursive"
    assert data["metadata"]["recursive_style"] == "sequential"
    assert [task["id"] for task in data["tasks"]] == [
        "decompose",
        "execute_round_1",
        "synthesize",
    ]


def test_run_command_prints_trace(capsys) -> None:
    exit_code = main(["run", "Build", "a", "CLI", "--permission", "read-only", "--effort", "high"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Beethoven performed score-" in captured.out
    assert "permission=read-only" in captured.out
    assert "effort=high" in captured.out
    assert "understand:local-echo" in captured.out
    assert "synthesize:local-echo" in captured.out


def test_run_command_accepts_recursive_strategy(capsys) -> None:
    exit_code = main(
        [
            "run",
            "Recursive",
            "task",
            "--strategy",
            "recursive",
            "--recursive-style",
            "sequential",
            "--recursive-rounds",
            "1",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "strategy=recursive" in captured.out
    assert "decompose:local-echo" in captured.out
    assert "execute_round_1:local-echo" in captured.out


def test_run_command_can_execute_validation_hook(capsys) -> None:
    command = f"{sys.executable} -c \"print('ok')\""

    exit_code = main(["run", "Validate", "hook", "--validate", command])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Validation" in captured.out
    assert f"{command}: passed" in captured.out


def test_score_command_attaches_workspace_paths(capsys) -> None:
    exit_code = main(["score", "Review", "@README.md", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    attachments = data["metadata"]["attachments"]
    assert exit_code == 0
    assert attachments[0]["path"] == "README.md"
    assert attachments[0]["status"] == "attached"
    assert "# Beethoven" in attachments[0]["content"]


def test_score_command_infers_workspace_file_mentions(capsys) -> None:
    exit_code = main(["score", "Review", "readme.md", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    attachments = data["metadata"]["attachments"]
    assert exit_code == 0
    assert attachments[0]["path"] == "README.md"
    assert attachments[0]["status"] == "attached"


def test_local_reader_summarizes_attached_files(capsys) -> None:
    exit_code = main(["run", "Explique", "readme.md", "--soloist", "local-reader"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "understand:local-reader" in captured.out
    assert "synthesize:local-reader" in captured.out


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
    assert "Ollama [" in captured.out
    assert "RecursiveMAS [planned]" in captured.out


def test_ollama_requires_explicit_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("BEETHOVEN_ENABLE_OLLAMA", raising=False)
    monkeypatch.setattr("beethoven.runtime.ollama_is_available", lambda: True)

    soloists = list_soloists()

    assert next(item for item in soloists if item["id"] == "ollama")["status"] == "disabled"


def test_cli_soloists_are_listed_when_installed(monkeypatch) -> None:
    monkeypatch.setattr("beethoven.runtime.claude_cli_is_available", lambda: True)
    monkeypatch.setattr("beethoven.runtime.codex_cli_is_available", lambda: True)

    soloists = list_soloists()

    assert next(item for item in soloists if item["id"] == "claude-cli")["status"] == "available"
    assert next(item for item in soloists if item["id"] == "codex-cli")["status"] == "available"


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


def test_workspace_files_command_prints_attachable_files(capsys) -> None:
    exit_code = main(["workspace", "files", "--limit", "5"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Workspace files: Beethoven" in captured.out
    assert "- " in captured.out


def test_terminal_session_runs_objectives_and_commands(capsys) -> None:
    inputs = iter(
        [
            "/permission read-only",
            "/score Build terminal mode",
            "/strategy recursive",
            "/recursive-style sequential",
            "/recursive-rounds 1",
            "Run terminal objective",
            "/exit",
        ]
    )
    outputs: list[str] = []

    exit_code = run_terminal_session(
        input_fn=lambda _prompt: next(inputs),
        output_fn=outputs.append,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Beethoven terminal workbench" in outputs
    assert "permission_mode=read-only" in outputs
    assert "strategy=recursive" in outputs
    assert "recursive_style=sequential" in outputs
    assert "Score: score-" in captured.out
    assert "Beethoven performed score-" in captured.out
    assert "permission=read-only" in captured.out
    assert "decompose:local-echo" in captured.out


def test_package_sidecar_command_writes_launcher(tmp_path, capsys) -> None:
    output = tmp_path / "beethoven-sidecar"

    exit_code = main(["package", "sidecar", "--output", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Sidecar launcher written" in captured.out
    assert output.exists()
    assert "beethoven desktop" in output.read_text(encoding="utf-8")
    assert output.stat().st_mode & 0o111


def test_package_recursivemas_bridge_writes_executable_bridge(tmp_path, monkeypatch, capsys) -> None:
    output = tmp_path / "recursivemas_bridge.py"

    exit_code = main(["package", "recursivemas-bridge", "--output", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "RecursiveMAS bridge written" in captured.out
    assert "BEETHOVEN_RECURSIVEMAS_COMMAND" in captured.out
    assert output.exists()
    assert "beethoven.recursivemas.v1" in output.read_text(encoding="utf-8")
    assert output.stat().st_mode & 0o111

    sample_payload = {
        "protocol": "beethoven.recursivemas.v1",
        "task": {
            "id": "decompose",
            "capability": "plan",
            "metadata": {"recursive_role": "planner"},
        },
        "score": {
            "metadata": {"recursive_style": "sequential"},
        },
        "artifacts": {},
    }
    bridge_result = subprocess.run(
        [sys.executable, str(output)],
        check=False,
        input=json.dumps(sample_payload),
        capture_output=True,
        text=True,
    )
    bridge_payload = json.loads(bridge_result.stdout)
    assert bridge_result.returncode == 0
    assert bridge_payload["metadata"]["backend"] == "recursivemas-bridge"
    assert "decompose" in bridge_payload["output"]

    monkeypatch.setenv("BEETHOVEN_RECURSIVEMAS_COMMAND", f"{sys.executable} {output}")
    run_exit_code = main(
        [
            "run",
            "Bridge",
            "smoke",
            "--soloist",
            "recursivemas",
            "--strategy",
            "recursive",
            "--recursive-style",
            "sequential",
            "--recursive-rounds",
            "1",
        ]
    )
    run_output = capsys.readouterr().out
    assert run_exit_code == 0
    assert "decompose:recursivemas" in run_output
    assert os.environ["BEETHOVEN_RECURSIVEMAS_COMMAND"].endswith(str(output))
