from __future__ import annotations

import os
from pathlib import Path

from beethoven.solomlx import (
    DEFAULT_MINISTRAL_ORCHESTRATOR_MODEL,
    SoloMLXRuntime,
    ensure_solomlx_orchestrator,
    solomlx_prepare_orchestrator,
    solomlx_python,
    solomlx_start,
)


def test_solomlx_prepare_orchestrator_uses_mlxserve_models_pull(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BEETHOVEN_SOLOMLX_CACHE", str(tmp_path / "hf-cache"))
    checkout = tmp_path / "SoloMLX-server"
    executable = checkout / ".venv" / "bin" / "mlxserve"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    (checkout / ".venv" / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")
    calls = []

    def fake_run(command, *, cwd, env=None):
        calls.append((command, cwd, env))

        class Result:
            stdout = "pulled"

        return Result()

    monkeypatch.setattr("beethoven.solomlx._run", fake_run)

    report = solomlx_prepare_orchestrator(target_dir=checkout)

    assert report["model"] == DEFAULT_MINISTRAL_ORCHESTRATOR_MODEL
    assert calls == [
        (
            [str(executable), "models-pull", "--model", DEFAULT_MINISTRAL_ORCHESTRATOR_MODEL],
            checkout.resolve(),
            {
                **os.environ,
                "HF_HOME": str(tmp_path / "hf-cache"),
                "HUGGINGFACE_HUB_CACHE": str(tmp_path / "hf-cache" / "hub"),
                "TRANSFORMERS_CACHE": str(tmp_path / "hf-cache" / "transformers"),
            },
        )
    ]


def test_solomlx_python_prefers_configured_interpreter(monkeypatch) -> None:
    monkeypatch.setenv("BEETHOVEN_SOLOMLX_PYTHON", "/opt/custom/python")

    assert solomlx_python() == "/opt/custom/python"


def test_solomlx_start_sets_ministral_default_model(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BEETHOVEN_HOME", str(tmp_path / "home"))
    checkout = tmp_path / "SoloMLX-server"
    executable = checkout / ".venv" / "bin" / "mlxserve"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    (checkout / ".venv" / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")
    popen_calls = []

    class FakeProcess:
        pid = 4242

    def fake_popen(command, **kwargs):
        popen_calls.append((command, kwargs))
        return FakeProcess()

    monkeypatch.setattr("beethoven.solomlx.subprocess.Popen", fake_popen)
    monkeypatch.setattr("beethoven.solomlx.solomlx_status", lambda **kwargs: {"id": "solomlx"})

    report = solomlx_start(target_dir=checkout)

    command, kwargs = popen_calls[0]
    assert command == [str(executable), "serve"]
    assert kwargs["env"]["MLXSERVE_DEFAULT_MODEL"] == DEFAULT_MINISTRAL_ORCHESTRATOR_MODEL
    assert kwargs["env"]["HF_HOME"] == str(tmp_path / "home" / "huggingface")
    assert float(kwargs["env"]["MLXSERVE_MAX_MEMORY_GB"]) >= 14.0
    assert float(kwargs["env"]["MLXSERVE_HARD_MEMORY_GB"]) >= 15.0
    assert kwargs["env"]["MLXSERVE_HOST"] == "127.0.0.1"
    assert kwargs["env"]["MLXSERVE_PORT"] == "8080"
    assert Path(report["log"]).name == "solomlx.log"
    assert report["pid"] == 4242
    assert os.environ["BEETHOVEN_HOME"] == str(tmp_path / "home")


def test_solomlx_runtime_ensure_does_not_start_without_policy(monkeypatch) -> None:
    calls: list[str] = []
    runtime = SoloMLXRuntime()

    monkeypatch.setattr(
        "beethoven.solomlx.solomlx_status",
        lambda **kwargs: {
            "id": "solomlx",
            "installed": True,
            "available": False,
            "status": "stopped",
        },
    )
    monkeypatch.setattr("beethoven.solomlx.solomlx_start", lambda **kwargs: calls.append("start"))

    report = runtime.ensure_orchestrator()

    assert report["ensured"] is False
    assert report["actions"] == []
    assert calls == []


def test_solomlx_runtime_ensure_can_start_installed_runtime(monkeypatch) -> None:
    statuses = iter(
        [
            {
                "id": "solomlx",
                "installed": True,
                "available": False,
                "status": "stopped",
            },
            {
                "id": "solomlx",
                "installed": True,
                "available": True,
                "status": "available",
            },
            {
                "id": "solomlx",
                "installed": True,
                "available": True,
                "status": "available",
            },
        ]
    )
    monkeypatch.setattr("beethoven.solomlx.solomlx_status", lambda **kwargs: next(statuses))
    monkeypatch.setattr(
        "beethoven.solomlx.solomlx_start",
        lambda **kwargs: {
            "id": "solomlx",
            "started": True,
            "pid": 4242,
        },
    )

    report = SoloMLXRuntime().ensure_orchestrator(auto_start=True)

    assert report["ensured"] is True
    assert report["status"] == "available"
    assert report["actions"][0]["action"] == "start"


def test_ensure_solomlx_orchestrator_uses_env_policy(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_ensure(self, **kwargs):
        captured.update(kwargs)
        return {"id": "solomlx", "ensured": False}

    monkeypatch.setenv("BEETHOVEN_SOLOMLX_AUTOSTART", "1")
    monkeypatch.setenv("BEETHOVEN_SOLOMLX_AUTOPREPARE", "true")
    monkeypatch.setattr("beethoven.solomlx.SoloMLXRuntime.ensure_orchestrator", fake_ensure)

    report = ensure_solomlx_orchestrator()

    assert report["id"] == "solomlx"
    assert captured["auto_start"] is True
    assert captured["auto_prepare"] is True
    assert captured["auto_install"] is False
