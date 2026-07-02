"""Packaging helpers for desktop distribution."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


SIDECAR_SCRIPT = """#!/usr/bin/env sh
set -eu

HOST="${BEETHOVEN_HOST:-127.0.0.1}"
PORT="${BEETHOVEN_PORT:-4173}"
BEETHOVEN_HOME="${BEETHOVEN_HOME:-$HOME/.beethoven}"
export BEETHOVEN_HOME

if command -v curl >/dev/null 2>&1; then
  if curl -fsS "http://$HOST:$PORT/api/health" >/dev/null 2>&1; then
    echo "Beethoven sidecar found an existing desktop server at http://$HOST:$PORT"
    trap 'exit 0' INT TERM
    while :; do
      sleep 3600 &
      wait $!
    done
  fi
fi

if [ -n "${BEETHOVEN_BIN:-}" ]; then
  exec "$BEETHOVEN_BIN" desktop --host "$HOST" --port "$PORT"
fi

if command -v beethoven >/dev/null 2>&1; then
  exec beethoven desktop --host "$HOST" --port "$PORT"
fi

if [ -n "${BEETHOVEN_PYTHON:-}" ]; then
  PYTHON="$BEETHOVEN_PYTHON"
elif [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  echo "Beethoven sidecar could not find beethoven or python3." >&2
  exit 127
fi

exec "$PYTHON" -m beethoven.cli desktop --host "$HOST" --port "$PORT"
"""

RECURSIVEMAS_BRIDGE_SCRIPT = '''#!/usr/bin/env python3
"""Beethoven <-> RecursiveMAS sidecar bridge.

This bridge speaks Beethoven's `beethoven.recursivemas.v1` JSON protocol on
stdin/stdout. It is intentionally dependency-light so it can be generated before
the real RecursiveMAS runtime is installed. Replace `run_recursivemas` with
imports/calls into a local RecursiveMAS checkout or environment.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    if payload.get("protocol") != "beethoven.recursivemas.v1":
        raise SystemExit("Unsupported protocol")

    task = payload.get("task", {})
    score = payload.get("score", {})
    artifacts = payload.get("artifacts", {})
    output = run_recursivemas(task=task, score=score, artifacts=artifacts)
    print(json.dumps(output, ensure_ascii=False))
    return 0


def run_recursivemas(
    *,
    task: dict[str, Any],
    score: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    """Replace this fallback with the real RecursiveMAS runtime call.

    The real integration point should map Beethoven's recursive task metadata to
    RecursiveMAS styles such as sequential, deliberation, mixture, or
    distillation, then return the current task's output.
    """

    task_id = str(task.get("id", "task"))
    capability = str(task.get("capability", "analyze"))
    role = task.get("metadata", {}).get("recursive_role", "soloist")
    style = score.get("metadata", {}).get("recursive_style", "deliberation")
    prior_count = len(artifacts)
    return {
        "output": (
            f"RecursiveMAS bridge handled {task_id} "
            f"as {role}/{capability} in {style} mode with {prior_count} prior artifacts."
        ),
        "metadata": {
            "backend": "recursivemas-bridge",
            "style": style,
            "role": role,
        },
        "tokens": 0,
        "cost": 0.0,
    }


if __name__ == "__main__":
    raise SystemExit(main())
'''


def write_sidecar_script(path: str | Path) -> Path:
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(SIDECAR_SCRIPT, encoding="utf-8")
    output_path.chmod(0o755)
    target_path = tauri_target_sidecar_path(output_path)
    if target_path != output_path:
        target_path.write_text(SIDECAR_SCRIPT, encoding="utf-8")
        target_path.chmod(0o755)
    return output_path


def tauri_target_sidecar_path(path: str | Path) -> Path:
    output_path = Path(path).expanduser().resolve()
    target_triple = current_tauri_target_triple()
    if output_path.name.endswith(f"-{target_triple}"):
        return output_path
    return output_path.with_name(f"{output_path.name}-{target_triple}")


def current_tauri_target_triple() -> str:
    try:
        result = subprocess.run(
            ["rustc", "-vV"],
            check=False,
            capture_output=True,
            text=True,
            timeout=4,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return _fallback_target_triple()
    for line in result.stdout.splitlines():
        if line.startswith("host:"):
            return line.partition(":")[2].strip()
    return _fallback_target_triple()


def _fallback_target_triple() -> str:
    import platform

    machine = platform.machine().lower()
    if machine in {"arm64", "aarch64"}:
        return "aarch64-apple-darwin"
    return "x86_64-apple-darwin"


def write_recursivemas_bridge(path: str | Path) -> Path:
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(RECURSIVEMAS_BRIDGE_SCRIPT, encoding="utf-8")
    output_path.chmod(0o755)
    return output_path


def packaging_doctor(root: str | Path | None = None) -> dict[str, Any]:
    project_root = Path(root or Path.cwd()).expanduser().resolve()
    src_tauri = project_root / "src-tauri"
    tauri_conf = src_tauri / "tauri.conf.json"
    sidecar = src_tauri / "bin" / "beethoven-sidecar"
    target_sidecar = tauri_target_sidecar_path(sidecar)
    package_json = project_root / "package.json"
    lockfile = project_root / "package-lock.json"

    npm_path = shutil.which("npm")
    cargo_path = shutil.which("cargo")
    checks: list[dict[str, Any]] = []

    def add_check(
        check_id: str,
        name: str,
        ok: bool,
        message: str,
        *,
        required: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        checks.append(
            {
                "id": check_id,
                "name": name,
                "ok": ok,
                "required": required,
                "message": message,
                "details": details or {},
            }
        )

    add_check(
        "package_json",
        "Node package manifest",
        package_json.exists(),
        f"Found {package_json}" if package_json.exists() else "package.json is missing.",
        details={"path": str(package_json)},
    )
    add_check(
        "package_lock",
        "Pinned desktop dependencies",
        lockfile.exists(),
        f"Found {lockfile}" if lockfile.exists() else "package-lock.json is missing.",
        details={"path": str(lockfile)},
    )
    add_check(
        "npm",
        "npm",
        npm_path is not None,
        f"Using {npm_path}" if npm_path else "npm is required to run Tauri scripts.",
        details={"path": npm_path},
    )

    tauri_cli = _run_command(["npm", "run", "tauri", "--", "--version"], cwd=project_root) if npm_path else None
    add_check(
        "tauri_cli",
        "Tauri CLI",
        bool(tauri_cli and tauri_cli["ok"]),
        tauri_cli["message"] if tauri_cli else "Install npm dependencies before checking the Tauri CLI.",
        details=tauri_cli or {},
    )
    add_check(
        "cargo",
        "Rust Cargo",
        cargo_path is not None,
        f"Using {cargo_path}" if cargo_path else "Cargo is required by `npm run tauri:dev` and Tauri builds.",
        details={"path": cargo_path},
    )
    add_check(
        "sidecar",
        "Beethoven sidecar",
        sidecar.exists() and sidecar.is_file() and sidecar.stat().st_mode & 0o111 != 0,
        f"Executable sidecar found at {sidecar}"
        if sidecar.exists() and sidecar.stat().st_mode & 0o111 != 0
        else "Run `beethoven package sidecar` to generate the executable desktop sidecar.",
        details={"path": str(sidecar)},
    )
    add_check(
        "target_sidecar",
        "Tauri target sidecar",
        target_sidecar.exists() and target_sidecar.is_file() and target_sidecar.stat().st_mode & 0o111 != 0,
        f"Executable Tauri target sidecar found at {target_sidecar}"
        if target_sidecar.exists() and target_sidecar.stat().st_mode & 0o111 != 0
        else f"Run `beethoven package sidecar` to generate {target_sidecar.name}.",
        details={"path": str(target_sidecar), "target": current_tauri_target_triple()},
    )

    tauri_config = _inspect_tauri_config(tauri_conf)
    add_check(
        "tauri_config",
        "Tauri sidecar config",
        tauri_config["ok"],
        tauri_config["message"],
        details=tauri_config,
    )

    blockers = [check for check in checks if check["required"] and not check["ok"]]
    return {
        "id": "tauri-packaging",
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "root": str(project_root),
        "checks": checks,
        "blockers": blockers,
        "message": "Desktop packaging prerequisites are ready."
        if not blockers
        else f"{len(blockers)} packaging prerequisite(s) need attention.",
    }


def _run_command(command: list[str], *, cwd: Path, timeout: float = 6.0) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return {"ok": False, "command": command, "message": f"{command[0]} was not found."}
    except subprocess.TimeoutExpired:
        return {"ok": False, "command": command, "message": f"{' '.join(command)} timed out."}

    output = (result.stdout or result.stderr).strip()
    lines = [line for line in output.splitlines() if line and not line.startswith(">")]
    return {
        "ok": result.returncode == 0,
        "command": command,
        "returncode": result.returncode,
        "output": output[:500],
        "message": lines[-1] if lines else f"{' '.join(command)} exited with {result.returncode}.",
    }


def _inspect_tauri_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "path": str(path), "message": "src-tauri/tauri.conf.json is missing."}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "path": str(path), "message": f"Tauri config is invalid JSON: {exc}"}

    bundle = config.get("bundle", {})
    external_bin = bundle.get("externalBin", []) if isinstance(bundle, dict) else []
    build = config.get("build", {})
    before_build = build.get("beforeBuildCommand") if isinstance(build, dict) else None
    before_dev = build.get("beforeDevCommand") if isinstance(build, dict) else None
    has_sidecar = "bin/beethoven-sidecar" in external_bin
    has_before_build = isinstance(before_build, str) and "package sidecar" in before_build
    has_before_dev = isinstance(before_dev, str) and "beethoven-sidecar" in before_dev
    missing = []
    if not has_sidecar:
        missing.append("bundle.externalBin must include bin/beethoven-sidecar")
    if not has_before_build:
        missing.append("build.beforeBuildCommand must regenerate the sidecar")
    if not has_before_dev:
        missing.append("build.beforeDevCommand must launch the Beethoven sidecar")

    return {
        "ok": not missing,
        "path": str(path),
        "externalBin": external_bin,
        "beforeBuildCommand": before_build,
        "beforeDevCommand": before_dev,
        "message": "Tauri config wires the Beethoven sidecar." if not missing else "; ".join(missing),
    }
