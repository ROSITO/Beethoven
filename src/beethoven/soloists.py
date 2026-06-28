"""Built-in soloists used for local execution and tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from beethoven.core import Capability, ExecutionContext, SoloistResult, Task

MAX_OLLAMA_ATTACHMENT_CHARS = int(os.getenv("BEETHOVEN_OLLAMA_ATTACHMENT_CHARS", "12000"))
CLI_ADAPTER_TIMEOUT_SECONDS = int(os.getenv("BEETHOVEN_CLI_ADAPTER_TIMEOUT", "240"))
MODEL_ADAPTER_CAPABILITIES = frozenset(
    {
        Capability.ANALYZE,
        Capability.PLAN,
        Capability.CODE,
        Capability.REVIEW,
        Capability.SYNTHESIZE,
    }
)


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
class LocalReaderSoloist:
    """Safe local file reader that summarizes attached text without a model."""

    name: str = "local-reader"
    capabilities: frozenset[Capability] = frozenset(
        {
            Capability.ANALYZE,
            Capability.REVIEW,
            Capability.SYNTHESIZE,
        }
    )

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        attachments = [
            item
            for item in context.score.metadata.get("attachments", [])
            if isinstance(item, dict) and item.get("status") == "attached"
        ]
        if not attachments:
            return SoloistResult(
                output="No attached readable files were found. Mention a workspace file such as @README.md.",
                metadata={"mode": "local-reader"},
            )

        summaries = [self._summarize_attachment(item) for item in attachments]
        return SoloistResult(
            output="\n\n".join(summaries),
            metadata={
                "mode": "local-reader",
                "attachments": [item.get("path") for item in attachments],
            },
        )

    def _summarize_attachment(self, attachment: dict[str, object]) -> str:
        path = str(attachment.get("path", "attached file"))
        content = str(attachment.get("content", ""))
        headings = [
            line.strip("# ")
            for line in content.splitlines()
            if line.lstrip().startswith("#")
        ][:8]
        bullets = [
            line.strip()[2:]
            for line in content.splitlines()
            if line.strip().startswith(("- ", "* "))
        ][:10]
        paragraphs = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and not line.lstrip().startswith(("#", "-", "*", "```", "!", ">"))
        ][:6]

        sections = [f"{path}"]
        if headings:
            sections.append("Sections: " + ", ".join(headings))
        if paragraphs:
            sections.append("Résumé: " + " ".join(paragraphs))
        if bullets:
            sections.append("Points clés: " + "; ".join(bullets))
        return "\n".join(sections)


@dataclass(frozen=True)
class ClaudeCliSoloist:
    """Claude Code CLI adapter in non-interactive print mode."""

    name: str = "claude-cli"
    timeout_seconds: int = CLI_ADAPTER_TIMEOUT_SECONDS
    capabilities: frozenset[Capability] = MODEL_ADAPTER_CAPABILITIES

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        prompt = _build_model_prompt(task, context)
        result = subprocess.run(
            [
                "claude",
                "--print",
                "--output-format",
                "text",
                "--permission-mode",
                "plan",
                "--tools",
                "",
                "--no-session-persistence",
                prompt,
            ],
            check=False,
            capture_output=True,
            input="",
            text=True,
            timeout=self.timeout_seconds,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Claude CLI returned a non-zero exit code")
        return SoloistResult(
            output=result.stdout.strip(),
            metadata={"mode": "claude-cli"},
        )


@dataclass(frozen=True)
class CodexCliSoloist:
    """Codex CLI adapter in non-interactive read-only mode."""

    name: str = "codex-cli"
    model: str = os.getenv("BEETHOVEN_CODEX_MODEL", "gpt-5.5")
    timeout_seconds: int = CLI_ADAPTER_TIMEOUT_SECONDS
    capabilities: frozenset[Capability] = MODEL_ADAPTER_CAPABILITIES

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        prompt = _build_model_prompt(task, context)
        with tempfile.NamedTemporaryFile(prefix="beethoven-codex-", suffix=".txt") as output_file:
            result = subprocess.run(
                [
                    "codex",
                    "exec",
                    "--model",
                    self.model,
                    "--cd",
                    str(Path.cwd()),
                    "--sandbox",
                    "read-only",
                    "--color",
                    "never",
                    "--output-last-message",
                    output_file.name,
                    prompt,
                ],
                check=False,
                capture_output=True,
                input="",
                text=True,
                timeout=self.timeout_seconds,
            )
            output = Path(output_file.name).read_text(encoding="utf-8", errors="replace").strip()
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Codex CLI returned a non-zero exit code")
        return SoloistResult(
            output=output or result.stdout.strip(),
            metadata={"mode": "codex-cli", "model": self.model},
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
        prompt = _build_model_prompt(task, context)
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


def claude_cli_is_available() -> bool:
    return shutil.which("claude") is not None


def codex_cli_is_available() -> bool:
    return shutil.which("codex") is not None


def _build_model_prompt(task: Task, context: ExecutionContext) -> str:
    attachments = context.score.metadata.get("attachments", [])
    attachment_text = "\n\n".join(
        f"File: {item.get('path')}\n{str(item.get('content', ''))[:MAX_OLLAMA_ATTACHMENT_CHARS]}"
        for item in attachments
        if isinstance(item, dict)
    )
    previous = "\n".join(
        f"- {task_id}: {artifact.output}" for task_id, artifact in context.artifacts.items()
    )
    sections = [
        "You are a Beethoven soloist executing one task from an orchestration score.",
        "Do not modify files unless the surrounding Beethoven runtime explicitly asks for edits.",
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
