from __future__ import annotations

import os
import subprocess

from beethoven.patching import apply_approved_patch, inspect_patch, summarize_patch


def test_patch_requires_matching_approval_token(tmp_path) -> None:
    _init_repo(tmp_path)
    patch = _make_patch(tmp_path)

    inspection = inspect_patch(patch, path=tmp_path)
    denied = apply_approved_patch(patch, approval_token="wrong-token", path=tmp_path)
    applied = apply_approved_patch(patch, approval_token=str(inspection["token"]), path=tmp_path)

    assert inspection["applicable"] is True
    assert inspection["token"]
    assert denied["applied"] is False
    assert denied["status"] == "approval_required"
    assert applied["applied"] is True
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "after\n"


def test_patch_summary_reports_files_and_line_counts(tmp_path) -> None:
    _init_repo(tmp_path)
    patch = _make_patch(tmp_path)

    summary = summarize_patch(patch)

    assert summary["file_count"] == 1
    assert summary["additions"] == 1
    assert summary["deletions"] == 1
    assert summary["files"][0]["path"] == "hello.txt"
    assert summary["files"][0]["change_type"] == "modified"


def _init_repo(path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    target = path / "hello.txt"
    target.write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "hello.txt"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=path,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


def _make_patch(path) -> str:
    target = path / "hello.txt"
    target.write_text("after\n", encoding="utf-8")
    result = subprocess.run(["git", "diff"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "checkout", "--", "hello.txt"], cwd=path, check=True, capture_output=True)
    return result.stdout
