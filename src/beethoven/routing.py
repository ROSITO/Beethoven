"""Routing primitives for selecting the right soloist for each task."""

from __future__ import annotations

from dataclasses import dataclass, field

from beethoven.core import Capability, Soloist, Task


class SoloistNotFoundError(LookupError):
    """Raised when no registered soloist can satisfy a task."""


@dataclass
class SoloistRegistry:
    """In-memory registry for models, agents, providers, and tools."""

    _soloists: dict[str, Soloist] = field(default_factory=dict)

    def register(self, soloist: Soloist) -> None:
        self._soloists[soloist.name] = soloist

    def all(self) -> tuple[Soloist, ...]:
        return tuple(self._soloists.values())

    def capable_of(self, capability: Capability) -> tuple[Soloist, ...]:
        return tuple(
            soloist for soloist in self._soloists.values() if capability in soloist.capabilities
        )


@dataclass(frozen=True)
class CapabilityRouter:
    """Deterministic baseline router.

    This is the simple policy Beethoven can trust before adding cost, latency,
    privacy, quality scores, and human approval gates.
    """

    registry: SoloistRegistry
    preferred_soloist: str | None = None

    def choose(self, task: Task) -> Soloist:
        candidates = self.registry.capable_of(task.capability)
        if not candidates:
            raise SoloistNotFoundError(
                f"No soloist registered for capability '{task.capability.value}'"
            )
        if self.preferred_soloist:
            for candidate in candidates:
                if candidate.name == self.preferred_soloist:
                    return candidate
        return candidates[0]
