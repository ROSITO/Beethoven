"""Packaging helpers for desktop distribution."""

from __future__ import annotations

from pathlib import Path


SIDECAR_SCRIPT = """#!/usr/bin/env sh
set -eu

HOST="${BEETHOVEN_HOST:-127.0.0.1}"
PORT="${BEETHOVEN_PORT:-4173}"

exec beethoven desktop --host "$HOST" --port "$PORT"
"""


def write_sidecar_script(path: str | Path) -> Path:
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(SIDECAR_SCRIPT, encoding="utf-8")
    output_path.chmod(0o755)
    return output_path
