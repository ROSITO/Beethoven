"""Governed patch approval helpers."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from beethoven.workspace import inspect_workspace

MAX_PATCH_BYTES = 256_000


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
