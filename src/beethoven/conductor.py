"""The conductor coordinates score execution without owning provider logic."""

from __future__ import annotations

from dataclasses import dataclass

from beethoven.core import ExecutionContext, Score, Task, TaskStatus
from beethoven.routing import CapabilityRouter


class InvalidScoreError(ValueError):
    """Raised when a score cannot be executed safely."""


@dataclass(frozen=True)
class Conductor:
    """Execute a score by routing every task to an appropriate soloist."""

    router: CapabilityRouter

    def perform(self, score: Score) -> ExecutionContext:
        self._validate(score)
        context = ExecutionContext(
            score=score,
            statuses={task.id: TaskStatus.PENDING for task in score.tasks},
        )

        remaining = list(score.tasks)
        while remaining:
            ready = [task for task in remaining if self._dependencies_completed(task, context)]
            if not ready:
                unresolved = ", ".join(task.id for task in remaining)
                raise InvalidScoreError(f"Score contains unresolved dependencies: {unresolved}")

            for task in ready:
                self._perform_task(task, context)
                remaining.remove(task)

        return context

    def _perform_task(self, task: Task, context: ExecutionContext) -> None:
        soloist = self.router.choose(task)
        context.statuses[task.id] = TaskStatus.RUNNING
        context.trace.append(f"{task.id}:{soloist.name}")

        try:
            result = soloist.perform(task, context)
        except Exception:
            context.statuses[task.id] = TaskStatus.FAILED
            raise

        context.artifacts[task.id] = result
        context.statuses[task.id] = TaskStatus.COMPLETED

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
