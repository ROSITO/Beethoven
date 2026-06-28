"""Beethoven: universal orchestration primitives for AI systems."""

from beethoven.conductor import Conductor
from beethoven.core import (
    Capability,
    ExecutionContext,
    Score,
    Soloist,
    SoloistResult,
    Task,
    TaskStatus,
)
from beethoven.packaging import write_sidecar_script
from beethoven.planning import create_baseline_score
from beethoven.routing import CapabilityRouter, SoloistRegistry
from beethoven.runtime import list_soloists, run_objective, score_objective
from beethoven.soloists import EchoSoloist, OllamaSoloist
from beethoven.workspace import inspect_workspace

__all__ = [
    "Capability",
    "CapabilityRouter",
    "Conductor",
    "ExecutionContext",
    "Score",
    "Soloist",
    "SoloistRegistry",
    "SoloistResult",
    "Task",
    "TaskStatus",
    "EchoSoloist",
    "OllamaSoloist",
    "create_baseline_score",
    "list_soloists",
    "inspect_workspace",
    "run_objective",
    "score_objective",
    "write_sidecar_script",
]
