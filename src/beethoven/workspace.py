"""Workspace and Git context helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def inspect_workspace(path: str | Path | None = None) -> dict[str, Any]:
    root = Path(path or Path.cwd()).resolve()
    git_root = _git(root, "rev-parse", "--show-toplevel")
    workspace_root = Path(git_root).resolve() if git_root else root
    branch = _git(workspace_root, "branch", "--show-current") if git_root else None
    status_lines = _git_lines(workspace_root, "status", "--short") if git_root else []

    return {
        "name": workspace_root.name,
        "path": str(workspace_root),
        "is_git": bool(git_root),
        "branch": branch or None,
        "dirty": bool(status_lines),
        "changes": len(status_lines),
        "status": status_lines,
    }


def _git(cwd: Path, *args: str) -> str | None:
    result = _git_result(cwd, *args)
    if result is None:
        return None
    value = result.stdout.strip()
    return value or None


def _git_lines(cwd: Path, *args: str) -> list[str]:
    result = _git_result(cwd, *args)
    if result is None:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _git_result(cwd: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result
