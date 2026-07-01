"""Persistent local configuration for Beethoven adapters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from beethoven.desktop_state import default_state_dir


def default_config_path() -> Path:
    return default_state_dir() / "config.json"


class BeethovenConfig:
    """Tiny JSON-backed configuration store."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path).expanduser().resolve() if path else default_config_path()

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, dict) else {}

    def write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(".tmp")
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        temporary_path.replace(self.path)

    def get_recursivemas_command(self) -> str:
        soloists = self.read().get("soloists", {})
        if not isinstance(soloists, dict):
            return ""
        recursivemas = soloists.get("recursivemas", {})
        if not isinstance(recursivemas, dict):
            return ""
        return str(recursivemas.get("command", "")).strip()

    def set_recursivemas_command(self, command: str) -> Path:
        payload = self.read()
        soloists = payload.setdefault("soloists", {})
        if not isinstance(soloists, dict):
            soloists = {}
            payload["soloists"] = soloists
        recursivemas = soloists.setdefault("recursivemas", {})
        if not isinstance(recursivemas, dict):
            recursivemas = {}
            soloists["recursivemas"] = recursivemas
        recursivemas["command"] = command.strip()
        self.write(payload)
        return self.path

    def clear_recursivemas_command(self) -> Path:
        payload = self.read()
        soloists = payload.get("soloists", {})
        if isinstance(soloists, dict):
            recursivemas = soloists.get("recursivemas", {})
            if isinstance(recursivemas, dict):
                recursivemas.pop("command", None)
        self.write(payload)
        return self.path

    def get_openai_compatible(self) -> dict[str, str]:
        soloists = self.read().get("soloists", {})
        if not isinstance(soloists, dict):
            return {}
        adapter = soloists.get("openai-compatible", {})
        if not isinstance(adapter, dict):
            return {}
        return {
            "base_url": str(adapter.get("base_url", "")).strip(),
            "model": str(adapter.get("model", "")).strip(),
            "api_key": str(adapter.get("api_key", "")).strip(),
        }

    def set_openai_compatible(
        self,
        *,
        base_url: str,
        model: str = "",
        api_key: str = "",
    ) -> Path:
        payload = self.read()
        soloists = payload.setdefault("soloists", {})
        if not isinstance(soloists, dict):
            soloists = {}
            payload["soloists"] = soloists
        adapter = soloists.setdefault("openai-compatible", {})
        if not isinstance(adapter, dict):
            adapter = {}
            soloists["openai-compatible"] = adapter
        adapter["base_url"] = base_url.strip().rstrip("/")
        adapter["model"] = model.strip()
        if api_key.strip():
            adapter["api_key"] = api_key.strip()
        self.write(payload)
        return self.path

    def clear_openai_compatible(self) -> Path:
        payload = self.read()
        soloists = payload.get("soloists", {})
        if isinstance(soloists, dict):
            soloists.pop("openai-compatible", None)
        self.write(payload)
        return self.path
