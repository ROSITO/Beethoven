"""Built-in soloists used for local execution and tests."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass

from beethoven.core import Capability, ExecutionContext, SoloistResult, Task

MAX_OLLAMA_ATTACHMENT_CHARS = int(os.getenv("BEETHOVEN_OLLAMA_ATTACHMENT_CHARS", "12000"))


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
                "attachments": context.score.metadata.get("attachments", []),
                "previous_artifacts": previous,
            },
            metadata={"mode": "offline"},
        )


@dataclass(frozen=True)
class OllamaSoloist:
    """Local Ollama adapter using the `ollama run` CLI."""

    name: str = "ollama"
    model: str = os.getenv("BEETHOVEN_OLLAMA_MODEL", "qwen3-coder:latest")
    timeout_seconds: int = int(os.getenv("BEETHOVEN_OLLAMA_TIMEOUT", "120"))
    capabilities: frozenset[Capability] = frozenset(
        {
            Capability.ANALYZE,
            Capability.PLAN,
            Capability.CODE,
            Capability.REVIEW,
            Capability.SYNTHESIZE,
        }
    )

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        prompt = self._build_prompt(task, context)
        result = subprocess.run(
            ["ollama", "run", self.model, prompt],
            check=False,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Ollama returned a non-zero exit code")
        return SoloistResult(
            output=result.stdout.strip(),
            metadata={
                "mode": "ollama",
                "model": self.model,
            },
        )

    def _build_prompt(self, task: Task, context: ExecutionContext) -> str:
        attachments = context.score.metadata.get("attachments", [])
        attachment_text = "\n\n".join(
            f"File: {item.get('path')}\n{str(item.get('content', ''))[:MAX_OLLAMA_ATTACHMENT_CHARS]}"
            for item in attachments
        )
        previous = "\n".join(
            f"- {task_id}: {artifact.output}" for task_id, artifact in context.artifacts.items()
        )
        sections = [
            "You are a Beethoven soloist executing one task from an orchestration score.",
            f"Objective: {context.score.objective}",
            f"Task: {task.id}",
            f"Capability: {task.capability.value}",
            f"Instruction: {task.instruction}",
        ]
        if attachment_text:
            sections.append(f"Attached context:\n{attachment_text}")
        if previous:
            sections.append(f"Previous artifacts:\n{previous}")
        sections.append("Return a concise, useful result for this task.")
        return "\n\n".join(sections)


def ollama_is_enabled() -> bool:
    return os.getenv("BEETHOVEN_ENABLE_OLLAMA", "").lower() in {"1", "true", "yes"}


def ollama_is_available(model: str | None = None) -> bool:
    if shutil.which("ollama") is None:
        return False
    selected_model = model or os.getenv("BEETHOVEN_OLLAMA_MODEL", "qwen3-coder:latest")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and selected_model in result.stdout
