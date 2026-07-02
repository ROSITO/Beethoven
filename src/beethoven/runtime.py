"""Shared runtime helpers used by CLI and desktop surfaces."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, replace

from beethoven.conductor import Conductor
from beethoven.core import Capability, ExecutionContext, Score, Task
from beethoven.orchestrator import check_local_orchestrator, create_local_orchestrator
from beethoven.planning import create_baseline_score, create_dynamic_score
from beethoven.recursive import DEFAULT_RECURSIVE_STYLE, create_recursive_score
from beethoven.routing import CapabilityRouter, SoloistRegistry
from beethoven.serialization import score_to_dict
from beethoven.solomlx import ensure_solomlx_orchestrator
from beethoven.soloists import (
    ClaudeCliSoloist,
    CodexCliSoloist,
    EchoSoloist,
    LocalReaderSoloist,
    OllamaSoloist,
    OpenAICompatibleSoloist,
    RecursiveMASSoloist,
    claude_cli_is_available,
    check_openai_compatible,
    codex_cli_is_available,
    openai_compatible_is_available,
    openai_compatible_is_configured,
    check_recursivemas,
    ollama_is_available,
    ollama_is_enabled,
    recursivemas_is_available,
)
from beethoven.validation import ValidationSoloist, merge_validation_commands
from beethoven.workspace import read_workspace_attachments


@dataclass(frozen=True)
class SoloistDescriptor:
    id: str
    name: str
    provider: str
    status: str
    locality: str
    capabilities: tuple[str, ...]
    description: str


def create_default_registry() -> SoloistRegistry:
    registry = SoloistRegistry()
    registry.register(EchoSoloist())
    registry.register(LocalReaderSoloist())
    registry.register(ValidationSoloist())
    if claude_cli_is_available():
        registry.register(ClaudeCliSoloist())
    if codex_cli_is_available():
        registry.register(CodexCliSoloist())
    if ollama_is_enabled() and ollama_is_available():
        registry.register(OllamaSoloist())
    if openai_compatible_is_available():
        registry.register(OpenAICompatibleSoloist())
    if recursivemas_is_available():
        registry.register(RecursiveMASSoloist())
    return registry


def list_soloists() -> list[dict[str, object]]:
    ollama_available = ollama_is_available()
    ollama_status = "available" if ollama_is_enabled() and ollama_available else "disabled"
    if not ollama_available:
        ollama_status = "planned"
    openai_check = check_openai_compatible() if openai_compatible_is_configured() else {"status": "planned"}
    openai_status = "available" if openai_check.get("available") else str(openai_check.get("status", "planned"))
    recursivemas_status = "available" if recursivemas_is_available() else "planned"
    return [
        {
            "id": "local-echo",
            "name": "Local Echo",
            "provider": "Beethoven",
            "status": "available",
            "locality": "local",
            "capabilities": [
                "analyze",
                "plan",
                "code",
                "review",
                "validate",
                "synthesize",
                "tool_use",
            ],
            "description": "Deterministic offline soloist for local testing and UI flows.",
        },
        {
            "id": "local-reader",
            "name": "Local Reader",
            "provider": "Beethoven",
            "status": "available",
            "locality": "local",
            "capabilities": ["analyze", "review", "synthesize"],
            "description": "Safe local text reader for attached workspace files without external models.",
        },
        {
            "id": "claude-cli",
            "name": "Claude CLI",
            "provider": "Claude Code",
            "status": "available" if claude_cli_is_available() else "planned",
            "locality": "cloud",
            "capabilities": ["analyze", "plan", "code", "review", "synthesize"],
            "description": "Claude Code CLI adapter using non-interactive print mode.",
        },
        {
            "id": "codex-cli",
            "name": "Codex CLI",
            "provider": "OpenAI Codex",
            "status": "available" if codex_cli_is_available() else "planned",
            "locality": "cloud",
            "capabilities": ["analyze", "plan", "code", "review", "synthesize"],
            "description": "Codex CLI adapter using non-interactive read-only execution.",
        },
        {
            "id": "ollama",
            "name": "Ollama",
            "provider": "Local model",
            "status": ollama_status,
            "locality": "local",
            "capabilities": ["analyze", "plan", "code", "review", "synthesize"],
            "description": (
                "Local-first Ollama adapter. Disabled by default because large local models "
                "can create heavy memory pressure; set BEETHOVEN_ENABLE_OLLAMA=1 to enable."
            ),
        },
        {
            "id": "recursivemas",
            "name": "RecursiveMAS",
            "provider": "RecursiveMAS",
            "status": recursivemas_status,
            "locality": "local",
            "capabilities": ["analyze", "plan", "code", "review", "validate", "synthesize"],
            "description": (
                "Optional RecursiveMAS sidecar target using BEETHOVEN_RECURSIVEMAS_COMMAND "
                "and Beethoven's JSON stdin/stdout protocol."
            ),
        },
        {
            "id": "openai-compatible",
            "name": "OpenAI-compatible",
            "provider": "OpenAI-compatible API",
            "status": openai_status,
            "locality": "hybrid",
            "capabilities": ["analyze", "plan", "code", "review", "synthesize"],
            "description": (
                "Execution soloist for OpenAI, OpenRouter, LiteLLM, SoloMLX, "
                "and compatible /v1 chat completions APIs."
            ),
        },
        {
            "id": "codex",
            "name": "Codex",
            "provider": "Coding agent",
            "status": "planned",
            "locality": "hybrid",
            "capabilities": ["code", "review", "validate", "tool_use"],
            "description": "Coding workflow soloist planned for repository-aware execution.",
        },
    ]


def list_skills() -> list[dict[str, object]]:
    """Return capability groups derived from the configured soloist catalog."""
    grouped: dict[str, dict[str, object]] = {}
    for soloist in list_soloists():
        status = str(soloist["status"])
        for capability in soloist["capabilities"]:
            skill = grouped.setdefault(
                str(capability),
                {
                    "id": capability,
                    "name": str(capability).replace("_", " ").title(),
                    "status": "planned",
                    "soloists": [],
                    "description": f"Route {capability} work to compatible Beethoven soloists.",
                },
            )
            assert isinstance(skill["soloists"], list)
            skill["soloists"].append(
                {
                    "id": soloist["id"],
                    "name": soloist["name"],
                    "status": status,
                    "locality": soloist["locality"],
                }
            )
            if status == "available":
                skill["status"] = "available"

    return sorted(grouped.values(), key=lambda item: str(item["id"]))


def check_soloist(soloist_id: str) -> dict[str, object]:
    if soloist_id == "openai-compatible":
        return check_openai_compatible()
    if soloist_id == "recursivemas":
        return check_recursivemas()
    soloist = next((item for item in list_soloists() if item["id"] == soloist_id), None)
    if soloist is None:
        return {
            "id": soloist_id,
            "available": False,
            "status": "unknown",
            "message": f"Unknown soloist: {soloist_id}",
        }
    return {
        "id": soloist_id,
        "available": soloist["status"] == "available",
        "status": soloist["status"],
        "message": str(soloist["description"]),
    }


def check_orchestrator() -> dict[str, object]:
    """Return the hidden local planner status used before execution routing."""
    return check_local_orchestrator()


def score_objective(
    objective: str,
    metadata: dict[str, object] | None = None,
    *,
    planner_soloist: str | None = None,
    strategy: str = "baseline",
    recursive_style: str = DEFAULT_RECURSIVE_STYLE,
    recursive_rounds: int = 2,
) -> Score:
    score = create_baseline_score(objective)
    attachments = read_workspace_attachments(objective)
    combined_metadata: dict[str, object] = {**score.metadata}
    if attachments:
        combined_metadata["attachments"] = attachments
    if metadata:
        combined_metadata.update(metadata)
    if strategy == "recursive":
        recursive_score = create_recursive_score(
            objective,
            style=recursive_style,
            rounds=recursive_rounds,
            metadata=combined_metadata,
        )
        if recursivemas_is_available():
            return _prefer_recursivemas_for_recursive_score(recursive_score)
        return recursive_score
    if _local_orchestrator_planning_enabled():
        runtime_report = ensure_solomlx_orchestrator()
        combined_metadata["orchestrator_runtime"] = _public_runtime_report(runtime_report)
        orchestrator = create_local_orchestrator()
        if orchestrator is not None:
            planned_score = create_dynamic_score(
                objective,
                orchestrator,
                {
                    **combined_metadata,
                    "available_soloists": list_soloists(),
                    "orchestrator": "beethoven-local",
                    "orchestrator_policy": "local-first",
                },
            )
            if planned_score.metadata.get("planning_mode") != "baseline_fallback":
                return planned_score
            combined_metadata = {
                **planned_score.metadata,
                "orchestrator_fallback": True,
            }
    elif planner_soloist:
        combined_metadata["legacy_planner_soloist"] = planner_soloist
    if combined_metadata:
        return replace(
            score,
            metadata={
                **combined_metadata,
                "planning_mode": combined_metadata.get("planning_mode", "baseline"),
                "orchestrator": combined_metadata.get("orchestrator", "baseline"),
            },
        )
    return score


def run_objective(
    objective: str,
    *,
    soloist: str = "local-echo",
    permission_mode: str = "ask",
    effort: str = "medium",
    strategy: str = "baseline",
    recursive_style: str = DEFAULT_RECURSIVE_STYLE,
    recursive_rounds: int = 2,
    validation_commands: list[str] | None = None,
    validation_profiles: list[str] | None = None,
    approved_validation_commands: list[str] | None = None,
    event_sink: Callable[[dict[str, object]], None] | None = None,
) -> ExecutionContext:
    preferred_soloist = None if soloist == "auto" else soloist
    if soloist == "ollama" and not ollama_is_enabled():
        raise RuntimeError("Ollama is disabled by default. Restart with BEETHOVEN_ENABLE_OLLAMA=1 to opt in.")
    if soloist == "ollama" and not ollama_is_available():
        raise RuntimeError("Ollama soloist requested but the configured local model is unavailable.")
    registry = create_default_registry()
    if preferred_soloist and not any(candidate.name == preferred_soloist for candidate in registry.all()):
        raise RuntimeError(f"Soloist requested but unavailable: {soloist}")
    merged_validation_commands, selected_validation_profiles = merge_validation_commands(
        validation_commands,
        validation_profiles,
    )
    score = score_objective(
        objective,
        metadata={
            "soloist": soloist,
            "permission_mode": permission_mode,
            "effort": effort,
            "strategy": strategy,
            "recursive_style": recursive_style if strategy == "recursive" else None,
            "recursive_rounds": recursive_rounds if strategy == "recursive" else None,
            "validation_commands": merged_validation_commands,
            "validation_profiles": selected_validation_profiles,
            "approved_validation_commands": [
                str(command).strip()
                for command in approved_validation_commands or []
                if str(command).strip()
            ],
        },
        planner_soloist=preferred_soloist,
        strategy=strategy,
        recursive_style=recursive_style,
        recursive_rounds=recursive_rounds,
    )
    if merged_validation_commands:
        score = _with_validation_task(score, merged_validation_commands)
    if event_sink is not None:
        event_sink({"type": "score_planned", "score": score_to_dict(score)})
    context = Conductor(
        CapabilityRouter(registry, preferred_soloist=preferred_soloist),
        event_sink=event_sink,
    ).perform(score)
    return context


def _local_orchestrator_planning_enabled() -> bool:
    return os.getenv("BEETHOVEN_DYNAMIC_PLANNING", "1").lower() not in {"0", "false", "no"}


def _public_runtime_report(report: dict[str, object]) -> dict[str, object]:
    return {
        key: report[key]
        for key in (
            "id",
            "status",
            "available",
            "installed",
            "process_running",
            "base_url",
            "preferred_orchestrator_model",
            "ensured",
        )
        if key in report
    }


def _with_validation_task(score: Score, commands: list[str]) -> Score:
    task_id = _unique_task_id(score, "validation")
    dependency = score.tasks[-1].id if score.tasks else ""
    return replace(
        score,
        tasks=(
            *score.tasks,
            Task(
                id=task_id,
                instruction="Run governed validation commands and report pass, fail, or blocked policy decisions.",
                capability=Capability.VALIDATE,
                depends_on=(dependency,) if dependency else (),
                metadata={
                    "preferred_soloist": "validation-runner",
                    "validation_commands": commands,
                },
            ),
        ),
    )


def _unique_task_id(score: Score, desired: str) -> str:
    existing = score.task_ids()
    if desired not in existing:
        return desired
    index = 2
    while f"{desired}_{index}" in existing:
        index += 1
    return f"{desired}_{index}"


def _prefer_recursivemas_for_recursive_score(score: Score) -> Score:
    routed_tasks = tuple(
        Task(
            id=task.id,
            instruction=task.instruction,
            capability=task.capability,
            depends_on=task.depends_on,
            metadata={**task.metadata, "preferred_soloist": "recursivemas"},
        )
        for task in score.tasks
    )
    return replace(
        score,
        tasks=routed_tasks,
        metadata={
            **score.metadata,
            "recursive_backend": "recursivemas",
            "orchestrator_recursive_routing": "recursivemas",
        },
    )
