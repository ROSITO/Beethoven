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
from beethoven.planning import create_baseline_score
from beethoven.routing import CapabilityRouter, SoloistRegistry
from beethoven.soloists import EchoSoloist

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
    "create_baseline_score",
]
