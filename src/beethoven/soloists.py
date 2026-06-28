"""Built-in soloists used for local execution and tests."""

from __future__ import annotations

from dataclasses import dataclass

from beethoven.core import Capability, ExecutionContext, SoloistResult, Task


@dataclass(frozen=True)
class EchoSoloist:
    """Deterministic local soloist for smoke tests and offline demos."""

    name: str = "local-echo"
    capabilities: frozenset[Capability] = frozenset(Capability)

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        previous = {
            task_id: result.output for task_id, result in context.artifacts.items()
        }
        return SoloistResult(
            output={
                "task": task.id,
                "capability": task.capability.value,
                "instruction": task.instruction,
                "previous_artifacts": previous,
            },
            metadata={"mode": "offline"},
        )
