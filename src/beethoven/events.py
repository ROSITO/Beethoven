"""Execution event helpers."""

from __future__ import annotations

from beethoven.core import ExecutionContext


def context_events(context: ExecutionContext) -> list[dict[str, object]]:
    events: list[dict[str, object]] = [
        {
            "type": "score_started",
            "score_id": context.score.id,
            "objective": context.score.objective,
        }
    ]
    for trace_item in context.trace:
        task_id, _, soloist = trace_item.partition(":")
        events.append(
            {
                "type": "task_routed",
                "task_id": task_id,
                "soloist": soloist,
            }
        )
        events.append(
            {
                "type": "task_started",
                "task_id": task_id,
            }
        )
        if task_id in context.artifacts:
            events.append(
                {
                    "type": "artifact_produced",
                    "task_id": task_id,
                }
            )
        status = context.statuses.get(task_id)
        if status is not None:
            events.append(
                {
                    "type": "task_completed",
                    "task_id": task_id,
                    "status": status.value,
                }
            )
    if "validation" in context.artifacts:
        events.append({"type": "validation_completed"})
    events.append(
        {
            "type": "score_completed",
            "score_id": context.score.id,
            "status": "completed",
        }
    )
    return events
