"""Workspace and Git context helpers."""

from __future__ import annotations

import os
import re
import subprocess
import mimetypes
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
MAX_ATTACHMENT_TOTAL_BYTES = 128_000
MAX_DIRECTORY_ATTACHMENT_FILES = 8
MAX_ATTACHMENT_SNIPPET_CHARS = 420
ATTACHMENT_PATTERN = re.compile(r"(?<!\S)@([A-Za-z0-9_./-]+)")
FILE_REFERENCE_PATTERN = re.compile(r"(?<![@\w./-])([A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,8})(?![\w./-])")


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
                    "bytes": candidate.stat().st_size,
                    "media_type": _media_type(candidate),
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


def infer_workspace_attachment_paths(objective: str, root: Path, limit: int = 5) -> list[str]:
    explicit_paths = set(extract_attachment_paths(objective))
    inferred: list[str] = []
    references = {
        match.group(1).lower()
        for match in FILE_REFERENCE_PATTERN.finditer(objective)
        if match.group(1)
    }
    if not references:
        return inferred

    workspace_files = list_workspace_files(root, limit=500)["files"]
    for item in workspace_files:
        path = str(item.get("path", ""))
        name = str(item.get("name", ""))
        if path in explicit_paths:
            continue
        if path.lower() in references or name.lower() in references:
            inferred.append(path)
        if len(inferred) >= limit:
            break
    return inferred


def read_workspace_attachments(
    objective: str,
    path: str | Path | None = None,
    *,
    max_bytes: int = MAX_ATTACHMENT_BYTES,
    max_total_bytes: int = MAX_ATTACHMENT_TOTAL_BYTES,
    max_directory_files: int = MAX_DIRECTORY_ATTACHMENT_FILES,
) -> list[dict[str, object]]:
    workspace = inspect_workspace(path)
    root = Path(str(workspace["path"]))
    attachments: list[dict[str, object]] = []
    attachment_paths = [
        *extract_attachment_paths(objective),
        *infer_workspace_attachment_paths(objective, root),
    ]
    used_bytes = 0
    seen_paths: set[str] = set()
    for attachment_path in dict.fromkeys(attachment_paths):
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
        if not candidate.exists():
            attachments.append(
                {
                    "path": attachment_path,
                    "status": "missing",
                    "reason": "path not found",
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
        if candidate.is_dir():
            bundled_files = _directory_attachment_files(candidate, root, max_directory_files)
            if not bundled_files:
                attachments.append(
                    {
                        "path": attachment_path,
                        "status": "missing",
                        "kind": "directory",
                        "reason": "directory has no attachable files",
                    }
                )
                continue
            for file_path in bundled_files:
                relative_file_path = file_path.relative_to(root).as_posix()
                if relative_file_path in seen_paths:
                    continue
                remaining_bytes = max(0, max_total_bytes - used_bytes)
                attachment, consumed = _read_file_attachment(
                    file_path,
                    root,
                    requested_path=relative_file_path,
                    max_bytes=min(max_bytes, remaining_bytes),
                    budget_exhausted=remaining_bytes <= 0,
                    source_directory=attachment_path,
                )
                attachments.append(attachment)
                seen_paths.add(relative_file_path)
                used_bytes += consumed
            continue
        if not candidate.is_file():
            attachments.append(
                {
                    "path": attachment_path,
                    "status": "blocked",
                    "reason": "not a regular file",
                }
            )
            continue
        if attachment_path in seen_paths:
            continue
        remaining_bytes = max(0, max_total_bytes - used_bytes)
        attachment, consumed = _read_file_attachment(
            candidate,
            root,
            requested_path=attachment_path,
            max_bytes=min(max_bytes, remaining_bytes),
            budget_exhausted=remaining_bytes <= 0,
        )
        attachments.append(attachment)
        seen_paths.add(attachment_path)
        used_bytes += consumed
    return attachments


def _directory_attachment_files(directory: Path, root: Path, limit: int) -> list[Path]:
    files: list[Path] = []
    for current_directory, dirnames, filenames in os.walk(directory):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_DIRS)
        for filename in sorted(filenames):
            candidate = Path(current_directory) / filename
            if _is_ignored(candidate, root) or not candidate.is_file():
                continue
            files.append(candidate)
            if len(files) >= limit:
                return files
    return files


def _read_file_attachment(
    path: Path,
    root: Path,
    *,
    requested_path: str,
    max_bytes: int,
    budget_exhausted: bool,
    source_directory: str | None = None,
) -> tuple[dict[str, object], int]:
    size = path.stat().st_size
    base: dict[str, object] = {
        "path": requested_path,
        "name": path.name,
        "extension": path.suffix.lstrip(".") or "file",
        "kind": "file",
        "media_type": _media_type(path),
        "size_bytes": size,
    }
    if source_directory:
        base["source_directory"] = source_directory
    if budget_exhausted:
        return (
            {
                **base,
                "status": "blocked",
                "reason": "attachment budget exhausted",
            },
            0,
        )

    with path.open("rb") as file:
        raw_content = file.read(max_bytes + 1)
    if _looks_binary(raw_content):
        return (
            {
                **base,
                "status": "blocked",
                "reason": "binary file",
            },
            0,
        )
    truncated = len(raw_content) > max_bytes
    raw_content = raw_content[:max_bytes]
    content = raw_content.decode("utf-8", errors="replace")
    return (
        {
            **base,
            "status": "attached",
            "bytes": len(raw_content),
            "truncated": truncated or size > len(raw_content),
            "snippet": _snippet(content),
            "content": content,
        },
        len(raw_content),
    )


def _media_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "text/plain"


def _looks_binary(raw_content: bytes) -> bool:
    if not raw_content:
        return False
    if b"\x00" in raw_content:
        return True
    sample = raw_content[:2048]
    decoded = sample.decode("utf-8", errors="replace")
    replacement_ratio = decoded.count("\ufffd") / max(1, len(decoded))
    return replacement_ratio > 0.05


def _snippet(content: str) -> str:
    compact = " ".join(line.strip() for line in content.splitlines() if line.strip())
    return compact[:MAX_ATTACHMENT_SNIPPET_CHARS]


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
