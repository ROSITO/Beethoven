"""Core orchestration contracts.

These primitives are intentionally small: providers, agents, local tools, and
future distributed workers should all be able to implement them without pulling
Beethoven internals into their own runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class Capability(StrEnum):
    """Portable capability labels used by the router."""

    ANALYZE = "analyze"
    PLAN = "plan"
    CODE = "code"
    REVIEW = "review"
    VALIDATE = "validate"
    SYNTHESIZE = "synthesize"
    TOOL_USE = "tool_use"


class TaskStatus(StrEnum):
    """Execution status for a score task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class Task:
    """One unit of work inside a score."""

    id: str
    instruction: str
    capability: Capability
    depends_on: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Score:
    """A portable execution plan produced by a planner."""

    id: str
    objective: str
    tasks: tuple[Task, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def task_ids(self) -> set[str]:
        return {task.id for task in self.tasks}


@dataclass
class ExecutionContext:
    """Mutable state shared across one score execution."""

    score: Score
    artifacts: dict[str, Any] = field(default_factory=dict)
    statuses: dict[str, TaskStatus] = field(default_factory=dict)
    trace: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SoloistResult:
    """Result returned by any model, agent, provider, or tool adapter."""

    output: Any
    cost: float = 0.0
    tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class Soloist(Protocol):
    """Adapter contract implemented by every orchestratable intelligence."""

    name: str
    capabilities: frozenset[Capability]

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        """Execute a task and return a normalized result."""
