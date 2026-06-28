"""Shared runtime helpers used by CLI and desktop surfaces."""

from __future__ import annotations

from dataclasses import dataclass, replace

from beethoven.conductor import Conductor
from beethoven.core import ExecutionContext, Score
from beethoven.planning import create_baseline_score
from beethoven.routing import CapabilityRouter, SoloistRegistry
from beethoven.soloists import EchoSoloist


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
    return registry


def list_soloists() -> list[dict[str, object]]:
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
            "id": "ollama",
            "name": "Ollama",
            "provider": "Local model",
            "status": "planned",
            "locality": "local",
            "capabilities": ["analyze", "plan", "synthesize"],
            "description": "Local-first model adapter planned for private orchestration.",
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


def score_objective(objective: str, metadata: dict[str, object] | None = None) -> Score:
    score = create_baseline_score(objective)
    if not metadata:
        return score
    return replace(score, metadata={**score.metadata, **metadata})


def run_objective(
    objective: str,
    *,
    soloist: str = "local-echo",
    permission_mode: str = "ask",
    effort: str = "medium",
) -> ExecutionContext:
    score = score_objective(
        objective,
        metadata={
            "soloist": soloist,
            "permission_mode": permission_mode,
            "effort": effort,
        },
    )
    registry = create_default_registry()
    return Conductor(CapabilityRouter(registry)).perform(score)
