"""Local Beethoven orchestration model adapters."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from beethoven.core import Capability, ExecutionContext, SoloistResult, Task


ORCHESTRATOR_NAME = "beethoven-orchestrator"
DEFAULT_SOLOMLX_BASE_URL = "http://127.0.0.1:8080/v1"
DEFAULT_ORCHESTRATOR_TIMEOUT = float(os.getenv("BEETHOVEN_ORCHESTRATOR_TIMEOUT", "20"))
DEFAULT_ORCHESTRATOR_CHECK_TIMEOUT = float(os.getenv("BEETHOVEN_ORCHESTRATOR_CHECK_TIMEOUT", "0.5"))
PROVIDER_ENV = "BEETHOVEN_ORCHESTRATOR_PROVIDER"
MODEL_ENV = "BEETHOVEN_ORCHESTRATOR_MODEL"
SOLOMLX_BASE_URL_ENV = "BEETHOVEN_ORCHESTRATOR_BASE_URL"
SOLOMLX_API_KEY_ENV = "BEETHOVEN_ORCHESTRATOR_API_KEY"


@dataclass(frozen=True)
class OpenAICompatibleOrchestrator:
    """Internal planner backed by a local OpenAI-compatible chat API."""

    base_url: str
    model: str
    api_key: str = ""
    timeout_seconds: float = DEFAULT_ORCHESTRATOR_TIMEOUT
    name: str = ORCHESTRATOR_NAME
    capabilities: frozenset[Capability] = frozenset({Capability.PLAN})

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Beethoven's private local orchestration model. "
                        "Create compact execution scores and route each task to the best "
                        "available soloist. Return valid JSON only."
                    ),
                },
                {"role": "user", "content": task.instruction},
            ],
            "temperature": 0.1,
            "max_tokens": 1200,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(
            _join_url(self.base_url, "chat/completions"),
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        content = _chat_completion_content(json.loads(raw))
        return SoloistResult(
            output=content,
            metadata={
                "mode": "beethoven-orchestrator",
                "provider": "openai-compatible",
                "base_url": self.base_url,
                "model": self.model,
            },
        )


@dataclass(frozen=True)
class OllamaOrchestrator:
    """Internal planner backed by a local Ollama model."""

    model: str
    timeout_seconds: float = DEFAULT_ORCHESTRATOR_TIMEOUT
    name: str = ORCHESTRATOR_NAME
    capabilities: frozenset[Capability] = frozenset({Capability.PLAN})

    def perform(self, task: Task, context: ExecutionContext) -> SoloistResult:
        prompt = "\n\n".join(
            [
                "You are Beethoven's private local orchestration model.",
                "Return valid JSON only. Do not include markdown.",
                task.instruction,
            ]
        )
        result = subprocess.run(
            ["ollama", "run", self.model, prompt],
            check=False,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Ollama orchestrator returned a non-zero exit code")
        return SoloistResult(
            output=result.stdout.strip(),
            metadata={
                "mode": "beethoven-orchestrator",
                "provider": "ollama",
                "model": self.model,
            },
        )


def local_orchestrator_enabled() -> bool:
    provider = os.getenv(PROVIDER_ENV, "auto").strip().lower()
    return provider not in {"0", "false", "no", "off", "disabled", "none"}


def create_local_orchestrator() -> OpenAICompatibleOrchestrator | OllamaOrchestrator | None:
    """Return the first available internal local orchestrator."""
    status = check_local_orchestrator()
    if not status.get("available"):
        return None
    provider = str(status.get("provider"))
    if provider == "solomlx":
        return OpenAICompatibleOrchestrator(
            base_url=str(status["base_url"]),
            model=str(status["model"]),
            api_key=os.getenv(SOLOMLX_API_KEY_ENV, ""),
        )
    if provider == "ollama":
        return OllamaOrchestrator(model=str(status["model"]))
    return None


def check_local_orchestrator() -> dict[str, object]:
    """Report the selected internal Beethoven planner, without exposing it as a soloist."""
    provider = os.getenv(PROVIDER_ENV, "auto").strip().lower() or "auto"
    report: dict[str, object] = {
        "id": ORCHESTRATOR_NAME,
        "configured_provider": provider,
        "available": False,
        "status": "unavailable",
        "message": "No local orchestration model is reachable.",
    }
    if not local_orchestrator_enabled():
        return {
            **report,
            "status": "disabled",
            "message": f"Set {PROVIDER_ENV}=auto, solomlx, or ollama to enable Beethoven's local orchestrator.",
        }

    providers = _candidate_providers(provider)
    checks = []
    for candidate in providers:
        if candidate == "solomlx":
            check = _check_solomlx()
        elif candidate == "ollama":
            check = _check_ollama()
        else:
            check = {
                "provider": candidate,
                "available": False,
                "status": "unknown_provider",
                "message": f"Unknown orchestrator provider: {candidate}",
            }
        checks.append(check)
        if check.get("available"):
            return {
                **report,
                **check,
                "status": "available",
            }
    return {
        **report,
        "checks": checks,
        "message": "; ".join(str(check.get("message", "")) for check in checks if check.get("message")),
    }


def _check_solomlx() -> dict[str, object]:
    base_url = os.getenv(SOLOMLX_BASE_URL_ENV, DEFAULT_SOLOMLX_BASE_URL).strip().rstrip("/")
    configured_model = os.getenv(MODEL_ENV, "").strip()
    try:
        request = Request(_join_url(base_url, "models"), method="GET")
        with urlopen(request, timeout=DEFAULT_ORCHESTRATOR_CHECK_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        return {
            "provider": "solomlx",
            "available": False,
            "base_url": base_url,
            "status": "unreachable",
            "message": f"SoloMLX/OpenAI-compatible endpoint is unreachable at {base_url}: {error}",
        }
    models = _models_from_openai_payload(payload)
    model = configured_model or (models[0] if models else "")
    if not model:
        return {
            "provider": "solomlx",
            "available": False,
            "base_url": base_url,
            "models": models,
            "status": "no_model",
            "message": "SoloMLX is reachable but did not expose a model.",
        }
    return {
        "provider": "solomlx",
        "available": True,
        "base_url": base_url,
        "model": model,
        "models": models,
        "message": "Beethoven will use the local OpenAI-compatible orchestration model.",
    }


def _check_ollama() -> dict[str, object]:
    if shutil.which("ollama") is None:
        return {
            "provider": "ollama",
            "available": False,
            "status": "missing_executable",
            "message": "Ollama executable was not found.",
        }
    try:
        result = subprocess.run(
            ["ollama", "list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "provider": "ollama",
            "available": False,
            "status": "unreachable",
            "message": f"Ollama did not respond: {error}",
        }
    models = _models_from_ollama_list(result.stdout)
    configured_model = os.getenv(MODEL_ENV, os.getenv("BEETHOVEN_ORCHESTRATOR_OLLAMA_MODEL", "")).strip()
    model = configured_model or _preferred_ollama_model(models)
    if result.returncode != 0:
        return {
            "provider": "ollama",
            "available": False,
            "status": "failed",
            "message": result.stderr.strip() or "ollama list failed.",
        }
    if not model:
        return {
            "provider": "ollama",
            "available": False,
            "status": "no_model",
            "models": models,
            "message": "Ollama is installed but no local model is available.",
        }
    if configured_model and configured_model not in models:
        return {
            "provider": "ollama",
            "available": False,
            "status": "missing_model",
            "model": configured_model,
            "models": models,
            "message": f"Configured orchestrator model is not installed in Ollama: {configured_model}",
        }
    return {
        "provider": "ollama",
        "available": True,
        "model": model,
        "models": models,
        "message": "Beethoven will use the local Ollama orchestration model.",
    }


def _candidate_providers(provider: str) -> tuple[str, ...]:
    if provider != "auto":
        return (provider,)
    if os.getenv("BEETHOVEN_ENABLE_OLLAMA", "").lower() in {"1", "true", "yes"}:
        return ("solomlx", "ollama")
    return ("solomlx",)


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
    models = []
    for item in data:
        if isinstance(item, dict) and item.get("id"):
            models.append(str(item["id"]))
    return models


def _models_from_ollama_list(output: str) -> list[str]:
    models: list[str] = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if parts:
            models.append(parts[0])
    return models


def _preferred_ollama_model(models: list[str]) -> str:
    if not models:
        return ""
    preferred_fragments = ("ministral", "mistral", "qwen", "llama")
    for fragment in preferred_fragments:
        for model in models:
            if fragment in model.lower():
                return model
    return models[0]
