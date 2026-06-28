"""Shared runtime helpers used by CLI and desktop surfaces."""

from __future__ import annotations

from beethoven.conductor import Conductor
from beethoven.core import ExecutionContext, Score
from beethoven.planning import create_baseline_score
from beethoven.routing import CapabilityRouter, SoloistRegistry
from beethoven.soloists import EchoSoloist


def create_default_registry() -> SoloistRegistry:
    registry = SoloistRegistry()
    registry.register(EchoSoloist())
    return registry


def score_objective(objective: str) -> Score:
    return create_baseline_score(objective)


def run_objective(objective: str) -> ExecutionContext:
    score = score_objective(objective)
    registry = create_default_registry()
    return Conductor(CapabilityRouter(registry)).perform(score)
