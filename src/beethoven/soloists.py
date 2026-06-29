"""Built-in soloists used for local execution and tests."""

from __future__ import annotations

import os
import json
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from beethoven.core import Capability, ExecutionContext, Score, SoloistResult, Task

MAX_OLLAMA_ATTACHMENT_CHARS = int(os.getenv("BEETHOVEN_OLLAMA_ATTACHMENT_CHARS", "12000"))
CLI_ADAPTER_TIMEOUT_SECONDS = int(os.getenv("BEETHOVEN_CLI_ADAPTER_TIMEOUT", "240"))
RECURSIVEMAS_TIMEOUT_SECONDS = int(os.getenv("BEETHOVEN_RECURSIVEMAS_TIMEOUT", "240"))
MODEL_ADAPTER_CAPABILITIES = frozenset(
    {
        Capability.ANALYZE,
        Capability.PLAN,
        Capability.CODE,
        Capability.REVIEW,
        Capability.SYNTHESIZE,
    }
)
RECURSIVE_ADAPTER_CAPABILITIES = frozenset(Capability)


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


@dataclass(frozen=True)
class RecursiveMASSoloist:
    """Optional RecursiveMAS sidecar adapter using a JSON stdin/stdout protocol."""

    name: str = "recursivemas"
    command: str | None = None
    timeout_seconds: int = RECURSIVEMAS_TIMEOUT_SECONDS
    capabilities: frozenset[Capability] = RECURSIVE_ADAPTER_CAPABILITIES

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        command = self.command or os.getenv("BEETHOVEN_RECURSIVEMAS_COMMAND", "")
        argv = shlex.split(command)
        if not argv:
            raise RuntimeError(
                "RecursiveMAS sidecar is not configured. Set BEETHOVEN_RECURSIVEMAS_COMMAND."
            )

        payload = _recursive_mas_payload(task, context)
        result = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            timeout=self.timeout_seconds,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "RecursiveMAS sidecar returned a non-zero exit code")
        return _recursive_mas_result(result.stdout)


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


def recursivemas_is_available(command: str | None = None) -> bool:
    selected_command = command or os.getenv("BEETHOVEN_RECURSIVEMAS_COMMAND", "")
    argv = shlex.split(selected_command)
    if not argv:
        return False
    executable = argv[0]
    if Path(executable).exists():
        return True
    return shutil.which(executable) is not None


def check_recursivemas(command: str | None = None) -> dict[str, object]:
    """Return a protocol health report for the optional RecursiveMAS sidecar."""

    selected_command = command or os.getenv("BEETHOVEN_RECURSIVEMAS_COMMAND", "")
    argv = shlex.split(selected_command)
    report: dict[str, object] = {
        "id": "recursivemas",
        "configured": bool(argv),
        "available": False,
        "command": selected_command,
        "protocol": "beethoven.recursivemas.v1",
    }
    if not argv:
        return {
            **report,
            "status": "not_configured",
            "message": "Set BEETHOVEN_RECURSIVEMAS_COMMAND to a bridge command.",
        }

    executable = argv[0]
    executable_available = Path(executable).exists() or shutil.which(executable) is not None
    report["executable_available"] = executable_available
    if not executable_available:
        return {
            **report,
            "status": "missing_executable",
            "message": f"Executable not found: {executable}",
        }

    payload = _recursive_mas_health_payload()
    try:
        result = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return {
            **report,
            "status": "timeout",
            "message": "RecursiveMAS sidecar did not respond within 10 seconds.",
        }
    except OSError as error:
        return {
            **report,
            "status": "launch_failed",
            "message": str(error),
        }

    report["returncode"] = result.returncode
    if result.returncode != 0:
        return {
            **report,
            "status": "failed",
            "message": result.stderr.strip() or "RecursiveMAS sidecar returned a non-zero exit code.",
        }

    parsed = _recursive_mas_result(result.stdout)
    return {
        **report,
        "available": True,
        "status": "available",
        "message": "RecursiveMAS sidecar responded to the Beethoven protocol.",
        "output_preview": str(parsed.output)[:240],
        "metadata": parsed.metadata,
        "tokens": parsed.tokens,
        "cost": parsed.cost,
    }


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


def _recursive_mas_health_payload() -> dict[str, object]:
    task = Task(
        id="healthcheck",
        instruction="Return a minimal health response for the Beethoven RecursiveMAS protocol.",
        capability=Capability.ANALYZE,
        metadata={"recursive_role": "healthcheck", "round": 0},
    )
    score = Score(
        id="score-recursive-healthcheck",
        objective="RecursiveMAS healthcheck",
        tasks=(task,),
        metadata={
            "strategy": "recursive",
            "recursive_style": "sequential",
            "recursive_rounds": 1,
        },
    )
    context = ExecutionContext(score=score)
    return _recursive_mas_payload(task, context)


def _recursive_mas_payload(task: Task, context: ExecutionContext) -> dict[str, object]:
    return {
        "protocol": "beethoven.recursivemas.v1",
        "task": {
            "id": task.id,
            "instruction": task.instruction,
            "capability": task.capability.value,
            "depends_on": list(task.depends_on),
            "metadata": task.metadata,
        },
        "score": {
            "id": context.score.id,
            "objective": context.score.objective,
            "metadata": context.score.metadata,
            "tasks": [
                {
                    "id": score_task.id,
                    "instruction": score_task.instruction,
                    "capability": score_task.capability.value,
                    "depends_on": list(score_task.depends_on),
                    "metadata": score_task.metadata,
                }
                for score_task in context.score.tasks
            ],
        },
        "artifacts": {
            task_id: {
                "output": artifact.output,
                "metadata": artifact.metadata,
                "cost": artifact.cost,
                "tokens": artifact.tokens,
            }
            for task_id, artifact in context.artifacts.items()
        },
    }


def _recursive_mas_result(stdout: str) -> SoloistResult:
    stripped = stdout.strip()
    if not stripped:
        return SoloistResult(output="", metadata={"mode": "recursivemas"})
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return SoloistResult(output=stripped, metadata={"mode": "recursivemas", "format": "text"})
    if not isinstance(payload, dict):
        return SoloistResult(output=payload, metadata={"mode": "recursivemas", "format": "json"})
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    return SoloistResult(
        output=payload.get("output", payload),
        cost=float(payload.get("cost", 0.0) or 0.0),
        tokens=int(payload.get("tokens", 0) or 0),
        metadata={
            "mode": "recursivemas",
            **metadata,
        },
    )
