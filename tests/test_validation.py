from __future__ import annotations

import sys

import pytest

from beethoven.runtime import run_objective
from beethoven.serialization import context_to_dict
from beethoven.validation import (
    classify_validation_command,
    list_validation_profiles,
    merge_validation_commands,
    plan_validation_hooks,
    resolve_validation_profiles,
)


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


def test_validation_policy_approves_known_read_only_commands() -> None:
    decision = classify_validation_command("git diff --check", permission_mode="ask")

    assert decision.status == "approved"
    assert decision.risk == "read_only"


def test_validation_policy_blocks_mutating_commands_without_auto_permission() -> None:
    plan = plan_validation_hooks(["rm -rf build"], permission_mode="ask")

    assert plan["approved"] == []
    assert plan["blocked"][0]["command"] == "rm -rf build"
    assert plan["blocked"][0]["risk"] == "mutating"


def test_validation_policy_allows_risky_commands_in_auto_permission() -> None:
    plan = plan_validation_hooks(["rm -rf build"], permission_mode="auto")

    assert plan["approved"] == ["rm -rf build"]
    assert plan["blocked"] == []


def test_run_objective_records_blocked_validation_without_executing() -> None:
    context = run_objective(
        "block risky validation",
        validation_commands=["rm -rf build"],
        permission_mode="ask",
    )

    validation = context.artifacts["validation"]
    assert validation.output[0]["blocked"] is True
    assert validation.output[0]["passed"] is False
    assert validation.metadata["approved_commands"] == []
    assert validation.metadata["blocked_commands"][0]["risk"] == "mutating"
    assert any(event["type"] == "validation_blocked" for event in context_to_dict(context)["events"])
