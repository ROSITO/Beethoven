"""Local desktop server for the Beethoven workbench prototype."""

from __future__ import annotations

import json
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from beethoven.desktop_state import DesktopSessionStore
from beethoven.runtime import list_skills, list_soloists, run_objective, score_objective
from beethoven.serialization import context_to_dict, score_to_dict
from beethoven.workspace import inspect_workspace, list_workspace_files


DESKTOP_ROOT = Path(__file__).resolve().parents[2] / "desktop"


class BeethovenDesktopHandler(SimpleHTTPRequestHandler):
    """Serve desktop assets and the first local orchestration API."""

    server_version = "BeethovenDesktop/0.1"
    store = DesktopSessionStore()

    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, directory=directory or str(DESKTOP_ROOT), **kwargs)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json({"status": "ok", "surface": "desktop"})
            return
        if path == "/api/sessions":
            self._send_json({"sessions": self.store.list_sessions()})
            return
        if path.startswith("/api/sessions/"):
            session_id = unquote(path.removeprefix("/api/sessions/"))
            session = self.store.get_session(session_id)
            if session is None:
                self._send_json({"error": "Session not found"}, HTTPStatus.NOT_FOUND)
                return
            self._send_json({"session": session})
            return
        if path == "/api/soloists":
            self._send_json({"soloists": list_soloists()})
            return
        if path == "/api/skills":
            self._send_json({"skills": list_skills()})
            return
        if path == "/api/workspace":
            self._send_json({"workspace": inspect_workspace()})
            return
        if path == "/api/files":
            self._send_json(list_workspace_files())
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/score":
            payload = self._read_payload()
            if payload is None:
                return
            objective = self._read_objective(payload)
            if objective is None:
                return
            soloist = str(payload.get("soloist", "local-echo"))
            self._send_json(score_to_dict(score_objective(objective, planner_soloist=soloist)))
            return

        if path == "/api/run":
            payload = self._read_payload()
            if payload is None:
                return
            objective = self._read_objective(payload)
            if objective is None:
                return
            soloist = str(payload.get("soloist", "local-echo"))
            permission_mode = str(payload.get("permission_mode", "ask"))
            effort = str(payload.get("effort", "medium"))
            validation_commands = self._read_validation_commands(payload)
            context = run_objective(
                objective,
                soloist=soloist,
                permission_mode=permission_mode,
                effort=effort,
                validation_commands=validation_commands,
            )
            session = self.store.save_run(
                context,
                project=str(payload.get("project", "Beethoven")),
                branch=str(payload.get("branch", "main")),
                soloist=soloist,
                permission_mode=permission_mode,
                effort=effort,
            )
            response = context_to_dict(context)
            response["session"] = session
            self._send_json(response)
            return

        if path == "/api/run/stream":
            payload = self._read_payload()
            if payload is None:
                return
            objective = self._read_objective(payload)
            if objective is None:
                return
            soloist = str(payload.get("soloist", "local-echo"))
            permission_mode = str(payload.get("permission_mode", "ask"))
            effort = str(payload.get("effort", "medium"))
            validation_commands = self._read_validation_commands(payload)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

            def write_event(event: dict[str, object]) -> None:
                self.wfile.write(json.dumps({"event": event}, ensure_ascii=False).encode("utf-8") + b"\n")
                self.wfile.flush()

            try:
                context = run_objective(
                    objective,
                    soloist=soloist,
                    permission_mode=permission_mode,
                    effort=effort,
                    validation_commands=validation_commands,
                    event_sink=write_event,
                )
                session = self.store.save_run(
                    context,
                    project=str(payload.get("project", "Beethoven")),
                    branch=str(payload.get("branch", "main")),
                    soloist=soloist,
                    permission_mode=permission_mode,
                    effort=effort,
                )
                response = context_to_dict(context)
                response["session"] = session
                write_event({"type": "run_completed", "context": response})
            except Exception as error:
                write_event({"type": "run_failed", "error": str(error)})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _read_payload(self) -> dict[str, Any] | None:
        content_length = int(self.headers.get("Content-Length", "0"))
        try:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(raw_body or "{}")
        except json.JSONDecodeError:
            self._send_json({"error": "Request body must be valid JSON"}, HTTPStatus.BAD_REQUEST)
            return None
        if not isinstance(payload, dict):
            self._send_json({"error": "Request body must be a JSON object"}, HTTPStatus.BAD_REQUEST)
            return None
        return payload

    def _read_objective(self, payload: dict[str, Any] | None = None) -> str | None:
        if payload is None:
            payload = self._read_payload()
        if payload is None:
            return None
        objective = str(payload.get("objective", "")).strip()
        if not objective:
            self._send_json({"error": "Missing objective"}, HTTPStatus.BAD_REQUEST)
            return None
        return objective

    def _read_validation_commands(self, payload: dict[str, Any]) -> list[str]:
        raw_validation_commands = payload.get("validation_commands", [])
        return (
            [
                str(command)
                for command in raw_validation_commands
                if str(command).strip()
            ]
            if isinstance(raw_validation_commands, list)
            else []
        )

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve_desktop(host: str = "127.0.0.1", port: int = 4173, open_browser: bool = False) -> None:
    server = ThreadingHTTPServer((host, port), BeethovenDesktopHandler)
    url = f"http://{host}:{port}"
    print(f"Beethoven desktop running at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
