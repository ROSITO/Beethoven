"""Validation hooks for local Beethoven runs."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

from beethoven.core import Capability, ExecutionContext, SoloistResult, Task


@dataclass(frozen=True)
class ValidationHook:
    command: tuple[str, ...]


@dataclass(frozen=True)
class ValidationProfile:
    id: str
    name: str
    description: str
    commands: tuple[str, ...]


@dataclass(frozen=True)
class ValidationDecision:
    command: str
    status: str
    risk: str
    reason: str


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


@dataclass(frozen=True)
class ValidationSoloist:
    """Internal soloist that executes governed validation commands."""

    name: str = "validation-runner"
    capabilities: frozenset[Capability] = frozenset({Capability.VALIDATE})

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        commands = [
            str(command)
            for command in task.metadata.get("validation_commands", [])
            if str(command).strip()
        ]
        permission_mode = str(context.score.metadata.get("permission_mode", "ask"))
        profiles = context.score.metadata.get("validation_profiles", [])
        validation_plan = plan_validation_hooks(commands, permission_mode=permission_mode)
        approved_commands = [
            str(command)
            for command in validation_plan.get("approved", [])
        ]
        blocked_commands = [
            item
            for item in validation_plan.get("blocked", [])
            if isinstance(item, dict)
        ]
        validation_results = run_validation_hooks(approved_commands)
        validation_results.extend(
            {
                "command": item.get("command", ""),
                "returncode": None,
                "passed": False,
                "blocked": True,
                "risk": item.get("risk", "requires_approval"),
                "reason": item.get("reason", "Validation command was blocked by policy."),
                "stdout": "",
                "stderr": "",
            }
            for item in blocked_commands
        )
        return SoloistResult(
            output=validation_results,
            metadata={
                "mode": "validation",
                "profiles": profiles if isinstance(profiles, list) else [],
                "commands": commands,
                "approved_commands": approved_commands,
                "blocked_commands": blocked_commands,
                "policy": validation_plan,
            },
        )


def plan_validation_hooks(commands: list[str], *, permission_mode: str = "ask") -> dict[str, object]:
    decisions = [classify_validation_command(command, permission_mode=permission_mode) for command in commands]
    approved = [decision.command for decision in decisions if decision.status == "approved"]
    blocked = [decision for decision in decisions if decision.status == "blocked"]
    return {
        "permission_mode": permission_mode,
        "approved": approved,
        "blocked": [
            {
                "command": decision.command,
                "status": decision.status,
                "risk": decision.risk,
                "reason": decision.reason,
            }
            for decision in blocked
        ],
        "decisions": [
            {
                "command": decision.command,
                "status": decision.status,
                "risk": decision.risk,
                "reason": decision.reason,
            }
            for decision in decisions
        ],
    }


def classify_validation_command(command: str, *, permission_mode: str = "ask") -> ValidationDecision:
    clean_command = str(command).strip()
    risk, reason = _validation_risk(clean_command)
    normalized_permission = str(permission_mode).strip().lower()
    if risk == "read_only":
        return ValidationDecision(clean_command, "approved", risk, reason)
    if normalized_permission == "auto":
        return ValidationDecision(clean_command, "approved", risk, "Permission mode auto approved validation command.")
    if normalized_permission == "read-only":
        return ValidationDecision(clean_command, "blocked", risk, "Read-only permission blocks mutating or unknown validation commands.")
    return ValidationDecision(clean_command, "blocked", risk, "Ask permission requires explicit approval before this validation command can run.")


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


def _validation_risk(command: str) -> tuple[str, str]:
    lowered = command.lower()
    dangerous_fragments = (
        " rm ",
        "rm -",
        " rmdir ",
        " mv ",
        " cp ",
        " chmod ",
        " chown ",
        "git clean",
        "git reset",
        "git checkout",
        "git switch",
        "git apply",
        "git commit",
        "git push",
        "npm install",
        "pip install",
        ">",
        ">>",
    )
    padded = f" {lowered} "
    if any(fragment in padded for fragment in dangerous_fragments):
        return "mutating", "Command appears able to modify files, dependencies, or Git state."
    read_only_prefixes = (
        "node --check ",
        ".venv/bin/ruff check ",
        "ruff check ",
        ".venv/bin/python -m pytest",
        f"{sys.executable} -m pytest",
        "python -m pytest",
        "python3 -m pytest",
        "pytest",
        "git diff --check",
        "git status",
        "git show",
    )
    if lowered.startswith(read_only_prefixes):
        return "read_only", "Command matches a known read-only validation command."
    if _is_simple_python_print(command):
        return "read_only", "Command is a simple Python print smoke test."
    return "requires_approval", "Command is not in Beethoven's read-only validation allowlist."


def _is_simple_python_print(command: str) -> bool:
    lowered = command.lower()
    python_markers = ("python -c", "python3 -c", f"{sys.executable.lower()} -c")
    if not any(marker in lowered for marker in python_markers):
        return False
    blocked = ("open(", "write(", "import os", "import subprocess", "import pathlib", "import shutil", "socket", "__import__")
    return "print(" in lowered and not any(fragment in lowered for fragment in blocked)
