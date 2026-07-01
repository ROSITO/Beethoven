"""Local state for the desktop workbench."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from beethoven.core import ExecutionContext
from beethoven.serialization import context_to_dict


def default_state_dir() -> Path:
    configured = os.environ.get("BEETHOVEN_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".beethoven"


@dataclass
class DesktopSessionStore:
    """Tiny JSON-backed store for local workbench sessions."""

    path: Path = field(default_factory=lambda: default_state_dir() / "desktop_sessions.json")

    def list_sessions(self) -> list[dict[str, Any]]:
        return [self._summary(session) for session in self._read_sessions()]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        for session in self._read_sessions():
            if session.get("id") == session_id:
                return session
        return None

    def clear(self) -> int:
        sessions = self._read_sessions()
        self._write([])
        return len(sessions)

    def _read_sessions(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        sessions = payload.get("sessions", [])
        if not isinstance(sessions, list):
            return []
        return sorted(sessions, key=lambda item: str(item.get("updated_at", "")), reverse=True)

    def save_run(
        self,
        context: ExecutionContext,
        *,
        project: str = "Beethoven",
        branch: str = "main",
        soloist: str = "local-echo",
        permission_mode: str = "ask",
        effort: str = "medium",
    ) -> dict[str, Any]:
        sessions = [session for session in self._read_sessions() if session.get("id") != context.score.id]
        session = {
            "id": context.score.id,
            "title": self._title_from_objective(context.score.objective),
            "objective": context.score.objective,
            "project": project,
            "branch": branch,
            "score_id": context.score.id,
            "soloist": soloist,
            "permission_mode": permission_mode,
            "effort": effort,
            "trace": context.trace,
            "status": "completed",
            "updated_at": datetime.now(UTC).isoformat(),
            "run": context_to_dict(context),
        }
        sessions.insert(0, session)
        self._write(sessions[:25])
        return session

    def _write(self, sessions: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(".tmp")
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump({"sessions": sessions}, file, ensure_ascii=False, indent=2)
        temporary_path.replace(self.path)

    @staticmethod
    def _title_from_objective(objective: str) -> str:
        words = objective.split()
        title = " ".join(words[:7])
        if len(words) > 7:
            title += "..."
        return title or "Untitled score"

    @staticmethod
    def _summary(session: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in session.items() if key != "run"}
