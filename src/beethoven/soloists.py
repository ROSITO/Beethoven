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
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from beethoven.config import BeethovenConfig
from beethoven.core import Capability, ExecutionContext, Score, SoloistResult, Task

MAX_OLLAMA_ATTACHMENT_CHARS = int(os.getenv("BEETHOVEN_OLLAMA_ATTACHMENT_CHARS", "12000"))
CLI_ADAPTER_TIMEOUT_SECONDS = int(os.getenv("BEETHOVEN_CLI_ADAPTER_TIMEOUT", "240"))
RECURSIVEMAS_TIMEOUT_SECONDS = int(os.getenv("BEETHOVEN_RECURSIVEMAS_TIMEOUT", "240"))
OPENAI_COMPATIBLE_TIMEOUT_SECONDS = float(os.getenv("BEETHOVEN_OPENAI_COMPAT_TIMEOUT", "120"))
OPENAI_COMPATIBLE_CHECK_TIMEOUT_SECONDS = float(os.getenv("BEETHOVEN_OPENAI_COMPAT_CHECK_TIMEOUT", "1.5"))
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
        if task.capability == Capability.SYNTHESIZE and context.artifacts:
            return SoloistResult(
                output=self._synthesize_artifacts(context),
                metadata={"mode": "local-reader", "synthesis": True},
            )
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

    def _synthesize_artifacts(self, context: ExecutionContext) -> str:
        attachments = [
            item
            for item in context.score.metadata.get("attachments", [])
            if isinstance(item, dict) and item.get("status") == "attached"
        ]
        lines = [f"Synthèse locale pour: {context.score.objective}"]
        if attachments:
            sample = ", ".join(str(item.get("path")) for item in attachments[:8])
            suffix = "..." if len(attachments) > 8 else ""
            lines.append(f"Contexte lu: {len(attachments)} fichier(s) ({sample}{suffix}).")
        for task_id, artifact in context.artifacts.items():
            summary = self._artifact_summary(task_id, artifact.output)
            if not summary:
                continue
            fallback = artifact.metadata.get("fallback_from")
            fallback_note = f" (fallback depuis {fallback})" if fallback else ""
            lines.append(f"- {task_id}{fallback_note}: {summary}")
        if len(lines) == 1:
            return "Le score est terminé, mais aucun artifact lisible n'a été produit."
        return "\n".join(lines)

    def _artifact_summary(self, task_id: str, output: object) -> str:
        if isinstance(output, dict):
            return self._dict_artifact_summary(output)
        if not isinstance(output, str):
            output = json.dumps(output, ensure_ascii=False, default=str)
        compact = self._compact_text(output)
        if not compact:
            return ""
        if "\n\n" in output:
            sections = []
            for block in output.split("\n\n")[:4]:
                block_summary = self._compact_text(block)
                if block_summary:
                    sections.append(block_summary[:260])
            if sections:
                return " | ".join(sections)[:900]
        return compact[:900]

    def _dict_artifact_summary(self, output: dict[str, object]) -> str:
        task = output.get("task")
        capability = output.get("capability")
        instruction = self._compact_text(str(output.get("instruction", "")))
        previous = output.get("previous_artifacts", {})
        previous_keys = []
        if isinstance(previous, dict):
            previous_keys = [str(key) for key in previous.keys()]
        parts = []
        if task or capability:
            parts.append(f"exécution locale {task or 'task'} ({capability or 'capability inconnue'})")
        if instruction:
            parts.append(instruction[:320])
        if previous_keys:
            parts.append(f"artifacts utilisés: {', '.join(previous_keys[:6])}")
        return "; ".join(parts)[:700]

    @staticmethod
    def _compact_text(value: str) -> str:
        return " ".join(value.split())


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
            raise RuntimeError(_cli_error_message("Claude CLI", result.stderr))
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
                    "--ignore-user-config",
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
            raise RuntimeError(_cli_error_message("Codex CLI", result.stderr))
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
class OpenAICompatibleSoloist:
    """Execution soloist backed by any OpenAI-compatible chat completions API."""

    name: str = "openai-compatible"
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    timeout_seconds: float = OPENAI_COMPATIBLE_TIMEOUT_SECONDS
    capabilities: frozenset[Capability] = MODEL_ADAPTER_CAPABILITIES

    def __post_init__(self) -> None:
        config = openai_compatible_config()
        object.__setattr__(self, "base_url", (self.base_url or config.get("base_url", "")).rstrip("/"))
        object.__setattr__(self, "model", self.model or config.get("model", ""))
        object.__setattr__(self, "api_key", self.api_key or config.get("api_key", ""))

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        if not self.base_url:
            raise RuntimeError("OpenAI-compatible soloist is not configured.")
        model = self.model or _first_openai_compatible_model(self.base_url, self.api_key)
        if not model:
            raise RuntimeError("OpenAI-compatible soloist did not expose a model.")
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a Beethoven soloist executing one score task. Return a concise useful result.",
                },
                {"role": "user", "content": _build_model_prompt(task, context)},
            ],
            "temperature": 0.2,
            "stream": False,
        }
        request = Request(
            _join_url(self.base_url, "chat/completions"),
            data=json.dumps(payload).encode("utf-8"),
            headers=_openai_compatible_headers(self.api_key),
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        response_payload = json.loads(raw)
        usage = response_payload.get("usage", {})
        if not isinstance(usage, dict):
            usage = {}
        return SoloistResult(
            output=_chat_completion_content(response_payload),
            tokens=int(usage.get("total_tokens", 0) or 0),
            metadata={
                "mode": "openai-compatible",
                "base_url": self.base_url,
                "model": model,
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
        command = self.command or recursivemas_command()
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


def _cli_error_message(label: str, stderr: str) -> str:
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    meaningful = [
        line
        for line in lines
        if line.startswith(("ERROR:", "Error:", "error:"))
        or "usage limit" in line.lower()
        or "rate limit" in line.lower()
        or "not authenticated" in line.lower()
        or "permission" in line.lower()
        or "unknown variant" in line.lower()
    ]
    if meaningful:
        return f"{label} failed: {meaningful[-1]}"
    if lines:
        tail = lines[-1]
        return f"{label} failed: {tail[:320]}"
    return f"{label} returned a non-zero exit code"


def openai_compatible_config() -> dict[str, str]:
    stored = BeethovenConfig().get_openai_compatible()
    base_url = (
        os.getenv("BEETHOVEN_OPENAI_COMPAT_BASE_URL", "").strip()
        or os.getenv("OPENAI_BASE_URL", "").strip()
        or stored.get("base_url", "")
    ).rstrip("/")
    model = (
        os.getenv("BEETHOVEN_OPENAI_COMPAT_MODEL", "").strip()
        or os.getenv("OPENAI_MODEL", "").strip()
        or stored.get("model", "")
    )
    api_key = (
        os.getenv("BEETHOVEN_OPENAI_COMPAT_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
        or stored.get("api_key", "")
    )
    return {"base_url": base_url, "model": model, "api_key": api_key}


def openai_compatible_is_configured() -> bool:
    return bool(openai_compatible_config().get("base_url"))


def openai_compatible_is_available() -> bool:
    return bool(check_openai_compatible().get("available"))


def check_openai_compatible() -> dict[str, object]:
    config = openai_compatible_config()
    base_url = config.get("base_url", "")
    model = config.get("model", "")
    report: dict[str, object] = {
        "id": "openai-compatible",
        "configured": bool(base_url),
        "available": False,
        "base_url": base_url,
        "model": model,
    }
    if not base_url:
        return {
            **report,
            "status": "not_configured",
            "message": (
                "Configure BEETHOVEN_OPENAI_COMPAT_BASE_URL or run "
                "`beethoven soloists configure openai-compatible --base-url ...`."
            ),
        }
    try:
        models = _openai_compatible_models(base_url, config.get("api_key", ""))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        return {
            **report,
            "status": "unreachable",
            "models": [],
            "message": f"OpenAI-compatible endpoint is unreachable at {base_url}: {error}",
        }
    selected_model = model or (models[0] if models else "")
    if not selected_model:
        return {
            **report,
            "status": "no_model",
            "models": models,
            "message": "OpenAI-compatible endpoint responded but did not expose a model.",
        }
    if model and models and model not in models:
        return {
            **report,
            "status": "missing_model",
            "models": models,
            "message": f"Configured model is not exposed by the endpoint: {model}",
        }
    return {
        **report,
        "available": True,
        "status": "available",
        "model": selected_model,
        "models": models,
        "message": "OpenAI-compatible soloist is ready for execution routing.",
    }


def recursivemas_is_available(command: str | None = None) -> bool:
    selected_command = command or recursivemas_command()
    argv = shlex.split(selected_command)
    if not argv:
        return False
    executable = argv[0]
    if Path(executable).exists():
        return True
    return shutil.which(executable) is not None


def check_recursivemas(command: str | None = None) -> dict[str, object]:
    """Return a protocol health report for the optional RecursiveMAS sidecar."""

    selected_command = command or recursivemas_command()
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


def recursivemas_command() -> str:
    return os.getenv("BEETHOVEN_RECURSIVEMAS_COMMAND", "").strip() or BeethovenConfig().get_recursivemas_command()


def _first_openai_compatible_model(base_url: str, api_key: str) -> str:
    models = _openai_compatible_models(base_url, api_key)
    return models[0] if models else ""


def _openai_compatible_models(base_url: str, api_key: str) -> list[str]:
    request = Request(
        _join_url(base_url, "models"),
        headers=_openai_compatible_headers(api_key),
        method="GET",
    )
    with urlopen(request, timeout=OPENAI_COMPATIBLE_CHECK_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return _models_from_openai_payload(payload)


def _openai_compatible_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _join_url(base_url: str, suffix: str) -> str:
    return f"{base_url.rstrip('/')}/{suffix.lstrip('/')}"


def _chat_completion_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("OpenAI-compatible response did not include choices.")
    first = choices[0]
    if not isinstance(first, dict):
        raise RuntimeError("OpenAI-compatible choice is invalid.")
    message = first.get("message", {})
    if isinstance(message, dict) and "content" in message:
        return str(message["content"]).strip()
    text = first.get("text")
    if text is not None:
        return str(text).strip()
    raise RuntimeError("OpenAI-compatible response did not include message content.")


def _models_from_openai_payload(payload: dict[str, Any]) -> list[str]:
    data = payload.get("data", [])
    if not isinstance(data, list):
        return []
    return [str(item["id"]) for item in data if isinstance(item, dict) and item.get("id")]


def _build_model_prompt(task: Task, context: ExecutionContext) -> str:
    attachments = context.score.metadata.get("attachments", [])
    attachment_text = "\n\n".join(
        "\n".join(
            [
                f"File: {item.get('path')}",
                f"Type: {item.get('media_type', 'text/plain')} · {item.get('bytes', 0)} bytes",
                str(item.get("content", ""))[:MAX_OLLAMA_ATTACHMENT_CHARS],
            ]
        )
        for item in attachments
        if isinstance(item, dict) and item.get("status") == "attached"
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
