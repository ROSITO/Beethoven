"""The conductor coordinates score execution without owning provider logic."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from beethoven.core import Capability, ExecutionContext, Score, Task, TaskStatus
from beethoven.routing import CapabilityRouter


class InvalidScoreError(ValueError):
    """Raised when a score cannot be executed safely."""


@dataclass(frozen=True)
class Conductor:
    """Execute a score by routing every task to an appropriate soloist."""

    router: CapabilityRouter
    event_sink: Callable[[dict[str, object]], None] | None = None

    def perform(self, score: Score) -> ExecutionContext:
        self._validate(score)
        context = ExecutionContext(
            score=score,
            statuses={task.id: TaskStatus.PENDING for task in score.tasks},
        )
        self._emit({"type": "score_started", "score_id": score.id, "objective": score.objective})

        remaining = list(score.tasks)
        while remaining:
            ready = [task for task in remaining if self._dependencies_completed(task, context)]
            if not ready:
                unresolved = ", ".join(task.id for task in remaining)
                raise InvalidScoreError(f"Score contains unresolved dependencies: {unresolved}")

            for task in ready:
                self._perform_task(task, context)
                remaining.remove(task)

        self._emit({"type": "score_completed", "score_id": score.id, "status": "completed"})
        return context

    def _perform_task(self, task: Task, context: ExecutionContext) -> None:
        soloist = self.router.choose(task)
        context.statuses[task.id] = TaskStatus.RUNNING
        context.trace.append(f"{task.id}:{soloist.name}")
        self._emit({"type": "task_routed", "task_id": task.id, "soloist": soloist.name})
        self._emit({"type": "task_started", "task_id": task.id})
        if task.capability == Capability.VALIDATE:
            self._emit(
                {
                    "type": "validation_started",
                    "task_id": task.id,
                    "commands": task.metadata.get("validation_commands", []),
                }
            )

        try:
            result = soloist.perform(task, context)
        except Exception as error:
            context.statuses[task.id] = TaskStatus.FAILED
            self._emit(
                {
                    "type": "task_failed",
                    "task_id": task.id,
                    "status": TaskStatus.FAILED.value,
                    "soloist": soloist.name,
                    "error": str(error),
                }
            )
            fallback = self.router.choose_fallback(task, soloist.name)
            if fallback is None:
                raise
            context.statuses[task.id] = TaskStatus.RUNNING
            context.trace.append(f"{task.id}:{fallback.name}")
            self._emit(
                {
                    "type": "task_routed",
                    "task_id": task.id,
                    "soloist": fallback.name,
                    "fallback_from": soloist.name,
                }
            )
            self._emit({"type": "task_started", "task_id": task.id})
            try:
                result = fallback.perform(task, context)
            except Exception:
                context.statuses[task.id] = TaskStatus.FAILED
                self._emit(
                    {
                        "type": "task_failed",
                        "task_id": task.id,
                        "status": TaskStatus.FAILED.value,
                        "soloist": fallback.name,
                    }
                )
                raise
            result = replace(
                result,
                metadata={
                    **result.metadata,
                    "fallback_from": soloist.name,
                    "fallback_error": str(error),
                },
            )

        context.artifacts[task.id] = result
        context.statuses[task.id] = TaskStatus.COMPLETED
        self._emit({"type": "artifact_produced", "task_id": task.id})
        if task.capability == Capability.VALIDATE:
            blocked = result.metadata.get("blocked_commands", [])
            if blocked:
                self._emit({"type": "validation_blocked", "task_id": task.id, "commands": blocked})
            self._emit(
                {
                    "type": "validation_completed",
                    "task_id": task.id,
                    "commands": result.metadata.get("approved_commands", []),
                    "blocked": blocked,
                }
            )
        self._emit({"type": "task_completed", "task_id": task.id, "status": TaskStatus.COMPLETED.value})

    def _emit(self, event: dict[str, object]) -> None:
        if self.event_sink is not None:
            self.event_sink(event)

    @staticmethod
    def _dependencies_completed(task: Task, context: ExecutionContext) -> bool:
        return all(context.statuses.get(task_id) == TaskStatus.COMPLETED for task_id in task.depends_on)

    @staticmethod
    def _validate(score: Score) -> None:
        task_ids = score.task_ids()
        if len(task_ids) != len(score.tasks):
            raise InvalidScoreError("Score task ids must be unique")

        unknown_dependencies = {
            dependency
            for task in score.tasks
            for dependency in task.depends_on
            if dependency not in task_ids
        }
        if unknown_dependencies:
            formatted = ", ".join(sorted(unknown_dependencies))
            raise InvalidScoreError(f"Score references unknown dependencies: {formatted}")
