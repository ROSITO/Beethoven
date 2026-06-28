"""Validation hooks for local Beethoven runs."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationHook:
    command: tuple[str, ...]


def run_validation_hooks(commands: list[str]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for command in commands:
        result = subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )
        results.append(
            {
                "command": command,
                "returncode": result.returncode,
                "passed": result.returncode == 0,
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-4000:],
            }
        )
    return results
