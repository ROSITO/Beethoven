"""Validation hooks for local Beethoven runs."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationHook:
    command: tuple[str, ...]


@dataclass(frozen=True)
class ValidationProfile:
    id: str
    name: str
    description: str
    commands: tuple[str, ...]


DEFAULT_VALIDATION_PROFILES: tuple[ValidationProfile, ...] = (
    ValidationProfile(
        id="desktop",
        name="Desktop JS",
        description="Check the desktop application JavaScript syntax.",
        commands=("node --check desktop/app.js",),
    ),
    ValidationProfile(
        id="lint",
        name="Python lint",
        description="Run Ruff across the repository.",
        commands=(".venv/bin/ruff check .",),
    ),
    ValidationProfile(
        id="tests",
        name="Python tests",
        description="Run the Python test suite.",
        commands=(".venv/bin/python -m pytest",),
    ),
    ValidationProfile(
        id="full",
        name="Full local gate",
        description="Run desktop syntax, lint, tests, and whitespace checks.",
        commands=(
            "node --check desktop/app.js",
            ".venv/bin/ruff check .",
            ".venv/bin/python -m pytest",
            "git diff --check",
        ),
    ),
)


def list_validation_profiles() -> list[dict[str, object]]:
    return [
        {
            "id": profile.id,
            "name": profile.name,
            "description": profile.description,
            "commands": list(profile.commands),
        }
        for profile in DEFAULT_VALIDATION_PROFILES
    ]


def resolve_validation_profiles(profile_ids: list[str] | None) -> tuple[list[str], list[dict[str, object]]]:
    if not profile_ids:
        return [], []
    profiles_by_id = {profile.id: profile for profile in DEFAULT_VALIDATION_PROFILES}
    commands: list[str] = []
    selected: list[dict[str, object]] = []
    seen_profiles: set[str] = set()
    for profile_id in profile_ids:
        clean_id = str(profile_id).strip()
        if not clean_id or clean_id in seen_profiles:
            continue
        profile = profiles_by_id.get(clean_id)
        if profile is None:
            available = ", ".join(sorted(profiles_by_id))
            raise ValueError(f"Unknown validation profile: {clean_id}. Available profiles: {available}")
        seen_profiles.add(clean_id)
        selected.append(
            {
                "id": profile.id,
                "name": profile.name,
                "description": profile.description,
                "commands": list(profile.commands),
            }
        )
        commands.extend(profile.commands)
    return _dedupe_commands(commands), selected


def merge_validation_commands(commands: list[str] | None, profile_ids: list[str] | None) -> tuple[list[str], list[dict[str, object]]]:
    profile_commands, profiles = resolve_validation_profiles(profile_ids)
    return _dedupe_commands([*(commands or []), *profile_commands]), profiles


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


def _dedupe_commands(commands: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for command in commands:
        clean_command = str(command).strip()
        if not clean_command or clean_command in seen:
            continue
        deduped.append(clean_command)
        seen.add(clean_command)
    return deduped
