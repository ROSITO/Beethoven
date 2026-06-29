from __future__ import annotations

import os
from pathlib import Path

from beethoven.solomlx import (
    DEFAULT_MINISTRAL_ORCHESTRATOR_MODEL,
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
