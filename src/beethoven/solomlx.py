"""Managed SoloMLX-server runtime integration for Beethoven."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from beethoven.desktop_state import default_state_dir
from beethoven.orchestrator import DEFAULT_SOLOMLX_BASE_URL


SOLOMLX_REPOSITORY_URL = "https://github.com/ROSITO/SoloMLX-server.git"
DEFAULT_SOLOMLX_PORT = 8080
DEFAULT_SOLOMLX_HOST = "127.0.0.1"


def default_solomlx_dir() -> Path:
    return Path(os.getenv("BEETHOVEN_SOLOMLX_DIR", default_state_dir() / "SoloMLX-server")).expanduser()


def default_solomlx_pid_path() -> Path:
    return default_state_dir() / "solomlx.pid"


def solomlx_base_url(host: str = DEFAULT_SOLOMLX_HOST, port: int = DEFAULT_SOLOMLX_PORT) -> str:
    default_url = DEFAULT_SOLOMLX_BASE_URL
    if host != DEFAULT_SOLOMLX_HOST or port != DEFAULT_SOLOMLX_PORT:
        default_url = f"http://{host}:{port}/v1"
    return os.getenv("BEETHOVEN_ORCHESTRATOR_BASE_URL", default_url).rstrip("/")


def solomlx_install(
    *,
    target_dir: str | Path | None = None,
    repository_url: str = SOLOMLX_REPOSITORY_URL,
    upgrade: bool = False,
    with_mlx: bool = True,
) -> dict[str, object]:
    """Clone or update SoloMLX-server and install it into its own local venv."""
    checkout_dir = Path(target_dir).expanduser() if target_dir else default_solomlx_dir()
    checkout_dir = checkout_dir.resolve()
    created = False
    if checkout_dir.exists() and not (checkout_dir / ".git").exists():
        raise RuntimeError(f"SoloMLX target exists but is not a Git checkout: {checkout_dir}")
    if not checkout_dir.exists():
        checkout_dir.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", repository_url, str(checkout_dir)], cwd=checkout_dir.parent)
        created = True
    elif upgrade:
        _run(["git", "pull", "--ff-only"], cwd=checkout_dir)

    venv_dir = checkout_dir / ".venv"
    if not venv_dir.exists():
        _run([sys.executable, "-m", "venv", str(venv_dir)], cwd=checkout_dir)
    python = _venv_python(venv_dir)
    _run([str(python), "-m", "pip", "install", "--upgrade", "pip"], cwd=checkout_dir)
    package_spec = ".[mlx]" if with_mlx else "."
    _run([str(python), "-m", "pip", "install", "-e", package_spec], cwd=checkout_dir)
    return {
        "id": "solomlx",
        "installed": True,
        "created": created,
        "path": str(checkout_dir),
        "python": str(python),
        "repository": repository_url,
        "with_mlx": with_mlx,
    }


def solomlx_status(
    *,
    base_url: str | None = None,
    pid_path: str | Path | None = None,
) -> dict[str, object]:
    """Return installation, process, and OpenAI-compatible API health."""
    checkout_dir = default_solomlx_dir().resolve()
    selected_pid_path = Path(pid_path).expanduser() if pid_path else default_solomlx_pid_path()
    api_url = (base_url or solomlx_base_url()).rstrip("/")
    pid = _read_pid(selected_pid_path)
    process_running = _pid_running(pid) if pid else False
    report: dict[str, object] = {
        "id": "solomlx",
        "repository": SOLOMLX_REPOSITORY_URL,
        "path": str(checkout_dir),
        "installed": (checkout_dir / ".git").exists(),
        "venv": str(checkout_dir / ".venv"),
        "pid_path": str(selected_pid_path),
        "pid": pid,
        "process_running": process_running,
        "base_url": api_url,
        "available": False,
        "status": "unavailable",
    }
    api_report = _api_status(api_url)
    report.update(api_report)
    if api_report["available"]:
        report["status"] = "available"
        report["message"] = "SoloMLX-server is reachable and can back Beethoven's local orchestrator."
    elif not report["installed"]:
        report["status"] = "not_installed"
        report["message"] = "Run `beethoven solomlx install` to add SoloMLX-server as a Beethoven runtime brick."
    elif process_running:
        report["status"] = "starting_or_unhealthy"
        report["message"] = str(api_report.get("message", "SoloMLX process is running but API is not ready."))
    else:
        report["status"] = "stopped"
        report["message"] = "SoloMLX-server is installed but not running."
    return report


def solomlx_start(
    *,
    host: str = DEFAULT_SOLOMLX_HOST,
    port: int = DEFAULT_SOLOMLX_PORT,
    target_dir: str | Path | None = None,
    pid_path: str | Path | None = None,
) -> dict[str, object]:
    """Start SoloMLX-server as a detached Beethoven-managed process."""
    checkout_dir = Path(target_dir).expanduser() if target_dir else default_solomlx_dir()
    checkout_dir = checkout_dir.resolve()
    if not checkout_dir.exists():
        raise RuntimeError("SoloMLX-server is not installed. Run `beethoven solomlx install` first.")
    selected_pid_path = Path(pid_path).expanduser() if pid_path else default_solomlx_pid_path()
    existing_pid = _read_pid(selected_pid_path)
    if existing_pid and _pid_running(existing_pid):
        return {
            **solomlx_status(base_url=solomlx_base_url(host, port), pid_path=selected_pid_path),
            "started": False,
            "message": f"SoloMLX-server is already running with pid {existing_pid}.",
        }

    python = _venv_python(checkout_dir / ".venv")
    if not python.exists():
        raise RuntimeError("SoloMLX virtualenv is missing. Run `beethoven solomlx install` again.")
    log_path = default_state_dir() / "solomlx.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("ab")
    command = _start_command(checkout_dir=checkout_dir)
    env = {
        **os.environ,
        "MLXSERVE_HOST": host,
        "MLXSERVE_PORT": str(port),
    }
    process = subprocess.Popen(
        command,
        cwd=checkout_dir,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=env,
    )
    selected_pid_path.parent.mkdir(parents=True, exist_ok=True)
    selected_pid_path.write_text(str(process.pid), encoding="utf-8")
    return {
        **solomlx_status(base_url=solomlx_base_url(host, port), pid_path=selected_pid_path),
        "started": True,
        "pid": process.pid,
        "log": str(log_path),
        "command": command,
    }


def solomlx_stop(*, pid_path: str | Path | None = None) -> dict[str, object]:
    selected_pid_path = Path(pid_path).expanduser() if pid_path else default_solomlx_pid_path()
    pid = _read_pid(selected_pid_path)
    if not pid:
        return {"id": "solomlx", "stopped": False, "message": "No SoloMLX pid file found."}
    if not _pid_running(pid):
        selected_pid_path.unlink(missing_ok=True)
        return {"id": "solomlx", "stopped": False, "pid": pid, "message": "SoloMLX was not running."}
    os.kill(pid, signal.SIGTERM)
    selected_pid_path.unlink(missing_ok=True)
    return {"id": "solomlx", "stopped": True, "pid": pid, "message": "SoloMLX-server stopped."}


def _api_status(base_url: str) -> dict[str, object]:
    try:
        headers = {}
        api_key = os.getenv("BEETHOVEN_ORCHESTRATOR_API_KEY", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = Request(f"{base_url.rstrip('/')}/models", headers=headers, method="GET")
        with urlopen(request, timeout=0.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        return {
            "available": False,
            "api_status": "unreachable",
            "models": [],
            "message": f"SoloMLX API is not reachable at {base_url}: {error}",
        }
    models = _models_from_payload(payload)
    return {
        "available": True,
        "api_status": "available",
        "models": models,
        "model": models[0] if models else "",
        "message": "SoloMLX API responded.",
    }


def _models_from_payload(payload: dict[str, Any]) -> list[str]:
    data = payload.get("data", [])
    if not isinstance(data, list):
        return []
    return [str(item["id"]) for item in data if isinstance(item, dict) and item.get("id")]


def _read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _venv_python(venv_dir: Path) -> Path:
    return venv_dir / "bin" / "python"


def _start_command(*, checkout_dir: Path) -> list[str]:
    return [str(checkout_dir / ".venv" / "bin" / "mlxserve"), "serve"]


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Command failed: {command}")
    return result
