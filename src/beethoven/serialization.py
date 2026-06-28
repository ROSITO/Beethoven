"""Serialization helpers for scores and execution traces."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from beethoven.core import ExecutionContext, Score, SoloistResult
from beethoven.events import context_events


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_jsonable(item) for item in value]
    return value


def score_to_dict(score: Score) -> dict[str, Any]:
    return to_jsonable(score)


def context_to_dict(context: ExecutionContext) -> dict[str, Any]:
    artifacts = {
        task_id: to_jsonable(result if isinstance(result, SoloistResult) else result)
        for task_id, result in context.artifacts.items()
    }
    return {
        "score": score_to_dict(context.score),
        "trace": context.trace,
        "statuses": to_jsonable(context.statuses),
        "events": context_events(context),
        "artifacts": artifacts,
    }
