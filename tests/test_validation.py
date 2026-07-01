from __future__ import annotations

import sys

import pytest

from beethoven.runtime import run_objective
from beethoven.validation import list_validation_profiles, merge_validation_commands, resolve_validation_profiles


def test_validation_profiles_are_discoverable() -> None:
    profiles = list_validation_profiles()

    assert [profile["id"] for profile in profiles] == ["desktop", "lint", "tests", "full"]
    assert any("node --check desktop/app.js" in profile["commands"] for profile in profiles)


def test_validation_profiles_merge_and_dedupe_commands() -> None:
    commands, profiles = merge_validation_commands(
        ["node --check desktop/app.js"],
        ["desktop", "tests"],
    )

    assert commands == ["node --check desktop/app.js", ".venv/bin/python -m pytest"]
    assert [profile["id"] for profile in profiles] == ["desktop", "tests"]


def test_unknown_validation_profile_fails_fast() -> None:
    with pytest.raises(ValueError, match="Unknown validation profile"):
        resolve_validation_profiles(["missing"])


def test_run_objective_records_validation_profile_metadata() -> None:
    command = f"{sys.executable} -c \"print('ok')\""

    context = run_objective(
        "validate with profile",
        validation_commands=[command],
        validation_profiles=["desktop"],
    )

    validation = context.artifacts["validation"]
    commands = validation.metadata["commands"]
    profiles = validation.metadata["profiles"]
    assert command in commands
    assert "node --check desktop/app.js" in commands
    assert profiles[0]["id"] == "desktop"
    assert context.score.metadata["validation_profiles"][0]["id"] == "desktop"
