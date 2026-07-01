from __future__ import annotations

import json
import os
import subprocess
import sys

from beethoven.cli import main, run_terminal_session
from beethoven.core import Capability, ExecutionContext, SoloistResult, Task
from beethoven.desktop_state import DesktopSessionStore
from beethoven.runtime import list_soloists, run_objective, score_objective


class FakeLocalOrchestrator:
    name = "beethoven-orchestrator"
    capabilities = frozenset({Capability.PLAN})

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        return SoloistResult(
            output=json.dumps(
                {
                    "tasks": [
                        {
                            "id": "inspect",
                            "capability": "analyze",
                            "instruction": "Inspect the objective.",
                            "depends_on": [],
                            "soloist": "local-reader",
                        },
                        {
                            "id": "answer",
                            "capability": "synthesize",
                            "instruction": "Answer from the inspection.",
                            "depends_on": ["inspect"],
                            "soloist": "local-echo",
                        },
                    ]
                }
            )
        )


def test_score_command_prints_json(capsys) -> None:
    exit_code = main(["score", "Build", "a", "CLI", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["objective"] == "Build a CLI"
    assert [task["id"] for task in data["tasks"]] == ["understand", "plan", "synthesize"]


def test_score_objective_uses_hidden_local_orchestrator(monkeypatch) -> None:
    monkeypatch.setenv("BEETHOVEN_DYNAMIC_PLANNING", "1")
    monkeypatch.setattr("beethoven.runtime.create_local_orchestrator", lambda: FakeLocalOrchestrator())
    monkeypatch.setattr(
        "beethoven.runtime.ensure_solomlx_orchestrator",
        lambda: {
            "id": "solomlx",
            "status": "available",
            "available": True,
            "installed": True,
            "process_running": True,
            "base_url": "http://127.0.0.1:8080/v1",
            "preferred_orchestrator_model": "ministral",
            "ensured": True,
            "actions": [{"action": "start"}],
        },
    )

    score = score_objective("Build a local orchestration brain")

    assert score.metadata["orchestrator"] == "beethoven-local"
    assert score.metadata["planner"] == "beethoven-orchestrator"
    assert score.metadata["orchestrator_runtime"]["id"] == "solomlx"
    assert score.metadata["orchestrator_runtime"]["ensured"] is True
    assert "actions" not in score.metadata["orchestrator_runtime"]
    assert [task.id for task in score.tasks] == ["inspect", "answer"]
    assert score.tasks[0].metadata["preferred_soloist"] == "local-reader"


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


def test_run_command_can_execute_validation_profile(capsys) -> None:
    exit_code = main(["run", "Validate", "profile", "--validation-profile", "desktop"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Validation" in captured.out
    assert "node --check desktop/app.js: passed" in captured.out


def test_run_command_reports_blocked_validation(capsys) -> None:
    exit_code = main(["run", "Validate", "policy", "--validate", "rm -rf build", "--permission", "ask"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "rm -rf build: blocked" in captured.out
    assert "Ask permission requires explicit approval" in captured.out


def test_run_command_can_approve_one_validation_command(capsys) -> None:
    exit_code = main(
        [
            "run",
            "Validate",
            "approval",
            "--validate",
            "printf ok",
            "--approve-validation",
            "printf ok",
            "--permission",
            "ask",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "printf ok: passed" in captured.out


def test_validation_profiles_command_lists_profiles(capsys) -> None:
    exit_code = main(["validation", "profiles", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["profiles"][0]["id"] == "desktop"
    assert data["profiles"][-1]["id"] == "full"


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


def test_orchestrator_status_command_reports_hidden_planner(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "beethoven.cli.check_orchestrator",
        lambda: {
            "id": "beethoven-orchestrator",
            "available": True,
            "status": "available",
            "provider": "solomlx",
            "model": "ministral-local",
            "profile": "ministral-recursivemas-router",
            "message": "ready",
        },
    )

    exit_code = main(["orchestrator", "status", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["orchestrator"]["provider"] == "solomlx"
    assert data["orchestrator"]["model"] == "ministral-local"
    assert data["orchestrator"]["profile"] == "ministral-recursivemas-router"


def test_solomlx_status_command_reports_runtime_brick(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "beethoven.cli.solomlx_status",
        lambda: {
            "id": "solomlx",
            "status": "available",
            "installed": True,
            "process_running": True,
            "available": True,
            "path": "/tmp/SoloMLX-server",
            "base_url": "http://127.0.0.1:8080/v1",
            "models": ["mlx-community/Qwen2.5-7B-Instruct-4bit"],
            "message": "ready",
        },
    )

    exit_code = main(["solomlx", "status", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["solomlx"]["status"] == "available"
    assert data["solomlx"]["models"] == ["mlx-community/Qwen2.5-7B-Instruct-4bit"]


def test_solomlx_install_command_can_skip_mlx_extra(monkeypatch, capsys) -> None:
    calls = []

    def fake_install(**kwargs):
        calls.append(kwargs)
        return {
            "id": "solomlx",
            "path": "/tmp/SoloMLX-server",
            "python": "/tmp/SoloMLX-server/.venv/bin/python",
        }

    monkeypatch.setattr("beethoven.cli.solomlx_install", fake_install)

    exit_code = main(["solomlx", "install", "--dir", "/tmp/SoloMLX-server", "--without-mlx"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "SoloMLX installed" in captured.out
    assert calls == [{"target_dir": "/tmp/SoloMLX-server", "upgrade": False, "with_mlx": False}]


def test_solomlx_prepare_orchestrator_pulls_model(monkeypatch, capsys) -> None:
    calls = []

    def fake_prepare(**kwargs):
        calls.append(kwargs)
        return {
            "id": "solomlx",
            "prepared": True,
            "model": "mlx-community/Ministral-3-3B-Instruct-2512-4bit",
            "path": "/tmp/SoloMLX-server",
            "output": "pulled model",
        }

    monkeypatch.setattr("beethoven.cli.solomlx_prepare_orchestrator", fake_prepare)

    exit_code = main(["solomlx", "prepare-orchestrator", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert calls == [{"target_dir": None}]
    assert data["solomlx"]["prepared"] is True
    assert "Ministral" in data["solomlx"]["model"]


def test_solomlx_ensure_command_uses_explicit_policy(monkeypatch, capsys) -> None:
    calls: list[dict[str, object]] = []

    def fake_ensure(**kwargs):
        calls.append(kwargs)
        return {"id": "solomlx", "status": "available", "ensured": True, "actions": []}

    monkeypatch.setattr("beethoven.cli.ensure_solomlx_orchestrator", fake_ensure)

    exit_code = main(["solomlx", "ensure", "--install", "--prepare", "--start", "--without-mlx", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["solomlx"]["ensured"] is True
    assert calls == [
        {
            "auto_install": True,
            "auto_prepare": True,
            "auto_start": True,
            "with_mlx": False,
        }
    ]


def test_soloists_check_reports_unconfigured_recursivemas(monkeypatch, capsys) -> None:
    monkeypatch.delenv("BEETHOVEN_RECURSIVEMAS_COMMAND", raising=False)

    exit_code = main(["soloists", "check", "recursivemas", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 1
    assert data["check"]["status"] == "not_configured"
    assert data["check"]["available"] is False


def test_openai_compatible_config_can_be_persisted_and_cleared(capsys) -> None:
    configure_exit = main(
        [
            "soloists",
            "configure",
            "openai-compatible",
            "--base-url",
            "http://127.0.0.1:8080/v1",
            "--model",
            "local-model",
            "--api-key",
            "secret",
        ]
    )
    capsys.readouterr()
    show_exit = main(["soloists", "show", "openai-compatible", "--json"])
    show_output = capsys.readouterr().out
    clear_exit = main(["soloists", "clear", "openai-compatible"])

    data = json.loads(show_output)
    assert configure_exit == 0
    assert show_exit == 0
    assert clear_exit == 0
    assert data["soloist"]["configured"] is True
    assert data["soloist"]["base_url"] == "http://127.0.0.1:8080/v1"
    assert data["soloist"]["model"] == "local-model"
    assert data["soloist"]["api_key_configured"] is True
    assert "secret" not in show_output


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


def test_workspace_diff_command_prints_status(capsys) -> None:
    exit_code = main(["workspace", "diff", "--max-chars", "200"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Workspace diff: Beethoven" in captured.out
    assert "Status:" in captured.out


def test_workspace_patch_commands_require_approval(tmp_path, monkeypatch, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    target = tmp_path / "hello.txt"
    target.write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "hello.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )
    target.write_text("after\n", encoding="utf-8")
    patch = subprocess.run(["git", "diff"], cwd=tmp_path, check=True, capture_output=True, text=True).stdout
    subprocess.run(["git", "checkout", "--", "hello.txt"], cwd=tmp_path, check=True, capture_output=True)
    patch_file = tmp_path / "change.patch"
    patch_file.write_text(patch, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    check_exit = main(["workspace", "patch-check", str(patch_file), "--json"])
    check_payload = json.loads(capsys.readouterr().out)
    denied_exit = main(["workspace", "patch-apply", str(patch_file), "--approve", "wrong"])
    denied_output = capsys.readouterr().out
    apply_exit = main(
        [
            "workspace",
            "patch-apply",
            str(patch_file),
            "--approve",
            check_payload["patch"]["token"],
        ]
    )
    apply_output = capsys.readouterr().out

    assert check_exit == 0
    assert denied_exit == 1
    assert "approval_required" in denied_output
    assert apply_exit == 0
    assert "Patch: applied" in apply_output
    assert target.read_text(encoding="utf-8") == "after\n"


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
    launcher = output.read_text(encoding="utf-8")
    assert "BEETHOVEN_BIN" in launcher
    assert "BEETHOVEN_PYTHON" in launcher
    assert "-m beethoven.cli desktop" in launcher
    assert output.stat().st_mode & 0o111


def test_package_doctor_command_reports_blockers(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "beethoven.cli.packaging_doctor",
        lambda: {
            "id": "tauri-packaging",
            "status": "blocked",
            "ready": False,
            "root": "/workspace",
            "message": "1 packaging prerequisite(s) need attention.",
            "blockers": [{"name": "Rust Cargo", "message": "Cargo is required."}],
            "checks": [{"name": "Rust Cargo", "ok": False}],
        },
    )

    exit_code = main(["package", "doctor"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Packaging: blocked" in captured.out
    assert "Rust Cargo" in captured.out


def test_package_doctor_command_can_emit_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "beethoven.cli.packaging_doctor",
        lambda: {
            "id": "tauri-packaging",
            "status": "ready",
            "ready": True,
            "root": "/workspace",
            "message": "Desktop packaging prerequisites are ready.",
            "blockers": [],
            "checks": [],
        },
    )

    exit_code = main(["package", "doctor", "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["packaging"]["ready"] is True


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
    check_exit_code = main(["soloists", "check", "recursivemas"])
    check_output = capsys.readouterr().out
    assert check_exit_code == 0
    assert "Status: available" in check_output
    assert "RecursiveMAS sidecar responded" in check_output

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


def test_recursivemas_command_can_be_persisted(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("BEETHOVEN_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("BEETHOVEN_RECURSIVEMAS_COMMAND", raising=False)
    bridge = tmp_path / "bridge.py"
    main(["package", "recursivemas-bridge", "--output", str(bridge)])
    capsys.readouterr()
    command = f"{sys.executable} {bridge}"

    configure_exit = main(["soloists", "configure", "recursivemas", "--command", command])
    configure_output = capsys.readouterr().out
    show_exit = main(["soloists", "show", "recursivemas", "--json"])
    show_payload = json.loads(capsys.readouterr().out)
    check_exit = main(["soloists", "check", "recursivemas"])
    check_output = capsys.readouterr().out
    run_exit = main(
        [
            "run",
            "Persisted",
            "bridge",
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
    clear_exit = main(["soloists", "clear", "recursivemas"])
    clear_output = capsys.readouterr().out

    assert configure_exit == 0
    assert "Configured recursivemas" in configure_output
    assert show_exit == 0
    assert show_payload["soloist"]["configured"] is True
    assert show_payload["soloist"]["command"] == command
    assert check_exit == 0
    assert "Status: available" in check_output
    assert run_exit == 0
    assert "decompose:recursivemas" in run_output
    assert clear_exit == 0
    assert "Cleared recursivemas" in clear_output
