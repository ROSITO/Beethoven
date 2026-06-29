"""Packaging helpers for desktop distribution."""

from __future__ import annotations

from pathlib import Path


SIDECAR_SCRIPT = """#!/usr/bin/env sh
set -eu

HOST="${BEETHOVEN_HOST:-127.0.0.1}"
PORT="${BEETHOVEN_PORT:-4173}"

exec beethoven desktop --host "$HOST" --port "$PORT"
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
    return output_path


def write_recursivemas_bridge(path: str | Path) -> Path:
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(RECURSIVEMAS_BRIDGE_SCRIPT, encoding="utf-8")
    output_path.chmod(0o755)
    return output_path
