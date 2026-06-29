"""Shared runtime helpers used by CLI and desktop surfaces."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from beethoven.conductor import Conductor
from beethoven.core import ExecutionContext, Score, SoloistResult
from beethoven.planning import create_baseline_score, create_dynamic_score, should_use_dynamic_planning
from beethoven.recursive import DEFAULT_RECURSIVE_STYLE, create_recursive_score
from beethoven.routing import CapabilityRouter, SoloistRegistry
from beethoven.soloists import (
    ClaudeCliSoloist,
    CodexCliSoloist,
    EchoSoloist,
    LocalReaderSoloist,
    OllamaSoloist,
    claude_cli_is_available,
    codex_cli_is_available,
    ollama_is_available,
    ollama_is_enabled,
)
from beethoven.validation import run_validation_hooks
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
    if claude_cli_is_available():
        registry.register(ClaudeCliSoloist())
    if codex_cli_is_available():
        registry.register(CodexCliSoloist())
    if ollama_is_enabled() and ollama_is_available():
        registry.register(OllamaSoloist())
    return registry


def list_soloists() -> list[dict[str, object]]:
    ollama_available = ollama_is_available()
    ollama_status = "available" if ollama_is_enabled() and ollama_available else "disabled"
    if not ollama_available:
        ollama_status = "planned"
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
            "status": "experimental",
            "locality": "local",
            "capabilities": ["analyze", "plan", "code", "review", "validate", "synthesize"],
            "description": (
                "Experimental backend target for RecursiveMAS-style latent multi-agent collaboration. "
                "Use Beethoven's recursive strategy now; attach the external backend as a sidecar later."
            ),
        },
        {
            "id": "openai-compatible",
            "name": "OpenAI-compatible",
            "provider": "Cloud API",
            "status": "planned",
            "locality": "cloud",
            "capabilities": ["analyze", "plan", "code", "review", "synthesize"],
            "description": "Adapter target for OpenAI, OpenRouter, and compatible APIs.",
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
        return create_recursive_score(
            objective,
            style=recursive_style,
            rounds=recursive_rounds,
            metadata=combined_metadata,
        )
    if planner_soloist and should_use_dynamic_planning(planner_soloist):
        registry = create_default_registry()
        planner = CapabilityRouter(registry, preferred_soloist=planner_soloist).choose(
            next(task for task in score.tasks if task.capability.value == "plan")
        )
        return create_dynamic_score(objective, planner, combined_metadata)
    if not combined_metadata:
        return score
    return replace(score, metadata=combined_metadata)


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
    event_sink: Callable[[dict[str, object]], None] | None = None,
) -> ExecutionContext:
    if soloist == "ollama" and not ollama_is_enabled():
        raise RuntimeError("Ollama is disabled by default. Restart with BEETHOVEN_ENABLE_OLLAMA=1 to opt in.")
    if soloist == "ollama" and not ollama_is_available():
        raise RuntimeError("Ollama soloist requested but the configured local model is unavailable.")
    registry = create_default_registry()
    if not any(candidate.name == soloist for candidate in registry.all()):
        raise RuntimeError(f"Soloist requested but unavailable: {soloist}")
    score = score_objective(
        objective,
        metadata={
            "soloist": soloist,
            "permission_mode": permission_mode,
            "effort": effort,
            "strategy": strategy,
            "recursive_style": recursive_style if strategy == "recursive" else None,
            "recursive_rounds": recursive_rounds if strategy == "recursive" else None,
            "validation_commands": validation_commands or [],
        },
        planner_soloist=soloist,
        strategy=strategy,
        recursive_style=recursive_style,
        recursive_rounds=recursive_rounds,
    )
    context = Conductor(
        CapabilityRouter(registry, preferred_soloist=soloist),
        event_sink=event_sink,
    ).perform(score)
    if validation_commands:
        if event_sink is not None:
            event_sink({"type": "validation_started", "commands": validation_commands})
        context.artifacts["validation"] = SoloistResult(
            output=run_validation_hooks(validation_commands),
            metadata={"mode": "validation"},
        )
        if event_sink is not None:
            event_sink({"type": "validation_completed", "commands": validation_commands})
    return context
