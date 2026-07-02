"""Governed patch approval helpers."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from beethoven.workspace import inspect_workspace

MAX_PATCH_BYTES = 256_000
MAX_PATCH_FILES = 80
MAX_PATCH_PREVIEW_LINES_PER_FILE = 160


def inspect_patch(
    patch: str,
    *,
    path: str | Path | None = None,
    max_bytes: int = MAX_PATCH_BYTES,
) -> dict[str, Any]:
    workspace = inspect_workspace(path)
    encoded = patch.encode("utf-8")
    if len(encoded) > max_bytes:
        return {
            "workspace": workspace,
            "approved": False,
            "applicable": False,
            "status": "too_large",
            "token": "",
            "bytes": len(encoded),
            "max_bytes": max_bytes,
            "message": f"Patch exceeds {max_bytes} bytes.",
        }
    if not workspace.get("is_git"):
        return {
            "workspace": workspace,
            "approved": False,
            "applicable": False,
            "status": "not_git",
            "token": "",
            "bytes": len(encoded),
            "max_bytes": max_bytes,
            "message": "Workspace is not a Git repository.",
        }
    token = patch_approval_token(patch)
    check = _git_apply(patch, Path(str(workspace["path"])), check_only=True)
    summary = summarize_patch(patch)
    return {
        "workspace": workspace,
        "approved": False,
        "applicable": check.returncode == 0,
        "status": "applicable" if check.returncode == 0 else "rejected",
        "token": token,
        "bytes": len(encoded),
        "max_bytes": max_bytes,
        "stdout": check.stdout[-4000:],
        "stderr": check.stderr[-4000:],
        "summary": summary,
        "message": "Patch can be applied with this approval token." if check.returncode == 0 else "Patch did not pass git apply --check.",
    }


def apply_approved_patch(
    patch: str,
    *,
    approval_token: str,
    path: str | Path | None = None,
    max_bytes: int = MAX_PATCH_BYTES,
) -> dict[str, Any]:
    inspection = inspect_patch(patch, path=path, max_bytes=max_bytes)
    expected_token = str(inspection.get("token", ""))
    if not inspection.get("applicable"):
        return {**inspection, "approved": False, "applied": False}
    if not approval_token or approval_token != expected_token:
        return {
            **inspection,
            "approved": False,
            "applied": False,
            "status": "approval_required",
            "message": "Patch approval token is missing or does not match.",
        }
    workspace = inspection["workspace"]
    assert isinstance(workspace, dict)
    result = _git_apply(patch, Path(str(workspace["path"])), check_only=False)
    return {
        **inspection,
        "approved": True,
        "applied": result.returncode == 0,
        "status": "applied" if result.returncode == 0 else "apply_failed",
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
        "message": "Patch applied." if result.returncode == 0 else "Patch failed during git apply.",
    }


def patch_approval_token(patch: str) -> str:
    digest = hashlib.sha256(patch.encode("utf-8")).hexdigest()
    return digest[:16]


def summarize_patch(patch: str, *, max_files: int = MAX_PATCH_FILES) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    total_additions = 0
    total_deletions = 0
    truncated = False
    old_line: int | None = None
    new_line: int | None = None

    for line in patch.splitlines():
        if line.startswith("diff --git "):
            if current is not None:
                files.append(current)
            if len(files) >= max_files:
                truncated = True
                current = None
                continue
            current = _patch_file_from_header(line)
            old_line = None
            new_line = None
            continue
        if current is None:
            continue
        if line.startswith("rename from "):
            current["old_path"] = line.removeprefix("rename from ").strip()
            current["change_type"] = "renamed"
            continue
        if line.startswith("rename to "):
            current["path"] = line.removeprefix("rename to ").strip()
            current["new_path"] = current["path"]
            current["change_type"] = "renamed"
            continue
        if line.startswith("new file mode"):
            current["change_type"] = "added"
            continue
        if line.startswith("deleted file mode"):
            current["change_type"] = "deleted"
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("@@"):
            old_line, new_line = _parse_hunk_header(line)
            continue
        if line.startswith("+"):
            current["additions"] += 1
            total_additions += 1
            _append_patch_preview_line(
                current,
                {
                    "kind": "addition",
                    "old_line": None,
                    "new_line": new_line,
                    "left": "",
                    "right": line[1:],
                },
            )
            if new_line is not None:
                new_line += 1
        elif line.startswith("-"):
            current["deletions"] += 1
            total_deletions += 1
            _append_patch_preview_line(
                current,
                {
                    "kind": "deletion",
                    "old_line": old_line,
                    "new_line": None,
                    "left": line[1:],
                    "right": "",
                },
            )
            if old_line is not None:
                old_line += 1
        elif line.startswith(" "):
            _append_patch_preview_line(
                current,
                {
                    "kind": "context",
                    "old_line": old_line,
                    "new_line": new_line,
                    "left": line[1:],
                    "right": line[1:],
                },
            )
            if old_line is not None:
                old_line += 1
            if new_line is not None:
                new_line += 1

    if current is not None and len(files) < max_files:
        files.append(current)
    elif current is not None:
        truncated = True

    return {
        "files": files,
        "file_count": len(files),
        "additions": total_additions,
        "deletions": total_deletions,
        "truncated": truncated,
    }


def _patch_file_from_header(line: str) -> dict[str, Any]:
    parts = line.split()
    old_path = parts[2].removeprefix("a/") if len(parts) > 2 else "unknown"
    new_path = parts[3].removeprefix("b/") if len(parts) > 3 else old_path
    return {
        "path": new_path,
        "old_path": old_path,
        "new_path": new_path,
        "change_type": "modified",
        "additions": 0,
        "deletions": 0,
        "preview_lines": [],
        "preview_truncated": False,
    }


def _append_patch_preview_line(file_summary: dict[str, Any], line: dict[str, Any]) -> None:
    preview_lines = file_summary.get("preview_lines")
    if not isinstance(preview_lines, list):
        preview_lines = []
        file_summary["preview_lines"] = preview_lines
    if len(preview_lines) >= MAX_PATCH_PREVIEW_LINES_PER_FILE:
        file_summary["preview_truncated"] = True
        return
    preview_lines.append(line)


def _parse_hunk_header(line: str) -> tuple[int | None, int | None]:
    parts = line.split()
    if len(parts) < 3:
        return None, None
    return _parse_hunk_start(parts[1], "-"), _parse_hunk_start(parts[2], "+")


def _parse_hunk_start(value: str, prefix: str) -> int | None:
    if not value.startswith(prefix):
        return None
    start = value.removeprefix(prefix).split(",", 1)[0]
    try:
        return int(start)
    except ValueError:
        return None


def _git_apply(patch: str, cwd: Path, *, check_only: bool) -> subprocess.CompletedProcess[str]:
    with NamedTemporaryFile("w", encoding="utf-8", suffix=".patch") as patch_file:
        patch_file.write(patch)
        patch_file.flush()
        command = ["git", "apply"]
        if check_only:
            command.append("--check")
        command.append(patch_file.name)
        return subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
