"""Workspace and Git context helpers."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any


IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
    "target",
}
IGNORED_SUFFIXES = {
    ".DS_Store",
    ".a",
    ".dylib",
    ".jpeg",
    ".jpg",
    ".lock",
    ".mp4",
    ".png",
    ".pyc",
    ".so",
    ".webp",
}
MAX_ATTACHMENT_BYTES = 64_000
ATTACHMENT_PATTERN = re.compile(r"(?<!\S)@([A-Za-z0-9_./-]+)")


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


def list_workspace_files(path: str | Path | None = None, limit: int = 80) -> dict[str, Any]:
    workspace = inspect_workspace(path)
    root = Path(str(workspace["path"]))
    files: list[dict[str, object]] = []
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_DIRS)
        for filename in sorted(filenames):
            if len(files) >= limit:
                break
            candidate = Path(directory) / filename
            if _is_ignored(candidate, root):
                continue
            relative_path = candidate.relative_to(root).as_posix()
            files.append(
                {
                    "path": relative_path,
                    "name": candidate.name,
                    "extension": candidate.suffix.lstrip(".") or "file",
                }
            )
        if len(files) >= limit:
            break
    return {
        "workspace": workspace,
        "files": files,
        "limit": limit,
    }


def extract_attachment_paths(objective: str) -> list[str]:
    paths: list[str] = []
    for match in ATTACHMENT_PATTERN.finditer(objective):
        attachment_path = match.group(1).strip()
        if attachment_path and attachment_path not in paths:
            paths.append(attachment_path)
    return paths


def read_workspace_attachments(
    objective: str,
    path: str | Path | None = None,
    *,
    max_bytes: int = MAX_ATTACHMENT_BYTES,
) -> list[dict[str, object]]:
    workspace = inspect_workspace(path)
    root = Path(str(workspace["path"]))
    attachments: list[dict[str, object]] = []
    for attachment_path in extract_attachment_paths(objective):
        candidate = (root / attachment_path).resolve()
        if not _is_relative_to(candidate, root):
            attachments.append(
                {
                    "path": attachment_path,
                    "status": "blocked",
                    "reason": "outside workspace",
                }
            )
            continue
        if not candidate.exists() or not candidate.is_file():
            attachments.append(
                {
                    "path": attachment_path,
                    "status": "missing",
                    "reason": "file not found",
                }
            )
            continue
        if _is_ignored(candidate, root):
            attachments.append(
                {
                    "path": attachment_path,
                    "status": "blocked",
                    "reason": "ignored file type or directory",
                }
            )
            continue

        with candidate.open("rb") as file:
            raw_content = file.read(max_bytes + 1)
        truncated = len(raw_content) > max_bytes
        raw_content = raw_content[:max_bytes]
        attachments.append(
            {
                "path": attachment_path,
                "status": "attached",
                "bytes": len(raw_content),
                "truncated": truncated,
                "content": raw_content.decode("utf-8", errors="replace"),
            }
        )
    return attachments


def _is_ignored(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    if any(part in IGNORED_DIRS for part in relative_parts[:-1]):
        return True
    return path.name in IGNORED_SUFFIXES or path.suffix in IGNORED_SUFFIXES


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


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
