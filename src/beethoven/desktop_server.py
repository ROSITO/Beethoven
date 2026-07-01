"""Local desktop server for the Beethoven workbench prototype."""

from __future__ import annotations

import json
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from beethoven.config import BeethovenConfig
from beethoven.desktop_state import DesktopSessionStore
from beethoven.runtime import (
    check_orchestrator,
    check_soloist,
    list_skills,
    list_soloists,
    run_objective,
    score_objective,
)
from beethoven.serialization import context_to_dict, score_to_dict
from beethoven.solomlx import (
    ensure_solomlx_orchestrator,
    solomlx_install,
    solomlx_prepare_orchestrator,
    solomlx_start,
    solomlx_status,
    solomlx_stop,
)
from beethoven.validation import list_validation_profiles
from beethoven.workspace import inspect_workspace, inspect_workspace_diff, list_workspace_files


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
        if path == "/api/orchestrator":
            report = check_orchestrator()
            self._send_json({"orchestrator": report})
            return
        if path == "/api/solomlx":
            self._send_json({"solomlx": solomlx_status()})
            return
        if path.startswith("/api/soloists/") and path.endswith("/check"):
            soloist_id = unquote(path.removeprefix("/api/soloists/").removesuffix("/check"))
            report = check_soloist(soloist_id)
            self._send_json({"check": report}, HTTPStatus.OK if report.get("available") else HTTPStatus.SERVICE_UNAVAILABLE)
            return
        if path == "/api/soloists/recursivemas/config":
            command = BeethovenConfig().get_recursivemas_command()
            self._send_json({"config": {"id": "recursivemas", "command": command, "configured": bool(command)}})
            return
        if path == "/api/soloists/openai-compatible/config":
            config = BeethovenConfig().get_openai_compatible()
            self._send_json(
                {
                    "config": {
                        "id": "openai-compatible",
                        "base_url": config.get("base_url", ""),
                        "model": config.get("model", ""),
                        "api_key_configured": bool(config.get("api_key", "")),
                        "configured": bool(config.get("base_url", "")),
                    }
                }
            )
            return
        if path == "/api/skills":
            self._send_json({"skills": list_skills()})
            return
        if path == "/api/validation-profiles":
            self._send_json({"profiles": list_validation_profiles()})
            return
        if path == "/api/workspace":
            self._send_json({"workspace": inspect_workspace()})
            return
        if path == "/api/diff":
            self._send_json({"diff": inspect_workspace_diff()})
            return
        if path == "/api/files":
            self._send_json(list_workspace_files())
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/soloists/recursivemas/config":
            payload = self._read_payload()
            if payload is None:
                return
            command = str(payload.get("command", "")).strip()
            if not command:
                self._send_json({"error": "Missing command"}, HTTPStatus.BAD_REQUEST)
                return
            config_path = BeethovenConfig().set_recursivemas_command(command)
            self._send_json({"config": {"id": "recursivemas", "command": command, "configured": True, "path": str(config_path)}})
            return

        if path == "/api/soloists/openai-compatible/config":
            payload = self._read_payload()
            if payload is None:
                return
            base_url = str(payload.get("base_url", "")).strip().rstrip("/")
            if not base_url:
                self._send_json({"error": "Missing base_url"}, HTTPStatus.BAD_REQUEST)
                return
            model = str(payload.get("model", "")).strip()
            api_key = str(payload.get("api_key", "")).strip()
            config_path = BeethovenConfig().set_openai_compatible(
                base_url=base_url,
                model=model,
                api_key=api_key,
            )
            config = BeethovenConfig().get_openai_compatible()
            self._send_json(
                {
                    "config": {
                        "id": "openai-compatible",
                        "base_url": config.get("base_url", ""),
                        "model": config.get("model", ""),
                        "api_key_configured": bool(config.get("api_key", "")),
                        "configured": True,
                        "path": str(config_path),
                    }
                }
            )
            return

        if path == "/api/score":
            payload = self._read_payload()
            if payload is None:
                return
            objective = self._read_objective(payload)
            if objective is None:
                return
            soloist = str(payload.get("soloist", "local-echo"))
            strategy = str(payload.get("strategy", "baseline"))
            recursive_style = str(payload.get("recursive_style", "deliberation"))
            recursive_rounds = self._read_recursive_rounds(payload)
            self._send_json(
                score_to_dict(
                    score_objective(
                        objective,
                        planner_soloist=soloist,
                        strategy=strategy,
                        recursive_style=recursive_style,
                        recursive_rounds=recursive_rounds,
                    )
                )
            )
            return

        if path == "/api/solomlx/start":
            payload = self._read_payload()
            if payload is None:
                return
            host = str(payload.get("host", "127.0.0.1"))
            try:
                port = int(payload.get("port", 8080))
            except (TypeError, ValueError):
                self._send_json({"error": "Invalid port"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                self._send_json({"solomlx": solomlx_start(host=host, port=port)})
            except RuntimeError as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/solomlx/install":
            payload = self._read_payload()
            if payload is None:
                return
            try:
                report = solomlx_install(
                    upgrade=bool(payload.get("upgrade", False)),
                    with_mlx=bool(payload.get("with_mlx", True)),
                )
                self._send_json({"solomlx": report})
            except RuntimeError as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/solomlx/prepare-orchestrator":
            payload = self._read_payload()
            if payload is None:
                return
            kwargs: dict[str, Any] = {}
            model = str(payload.get("model", "")).strip()
            if model:
                kwargs["model"] = model
            try:
                self._send_json({"solomlx": solomlx_prepare_orchestrator(**kwargs)})
            except RuntimeError as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/solomlx/ensure":
            payload = self._read_payload()
            if payload is None:
                return
            try:
                self._send_json(
                    {
                        "solomlx": ensure_solomlx_orchestrator(
                            auto_install=bool(payload.get("install", False)),
                            auto_prepare=bool(payload.get("prepare", False)),
                            auto_start=bool(payload.get("start", False)),
                            with_mlx=bool(payload.get("with_mlx", True)),
                        )
                    }
                )
            except RuntimeError as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
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
            strategy = str(payload.get("strategy", "baseline"))
            recursive_style = str(payload.get("recursive_style", "deliberation"))
            recursive_rounds = self._read_recursive_rounds(payload)
            validation_commands = self._read_validation_commands(payload)
            validation_profiles = self._read_validation_profiles(payload)
            approved_validation_commands = self._read_approved_validation_commands(payload)
            context = run_objective(
                objective,
                soloist=soloist,
                permission_mode=permission_mode,
                effort=effort,
                strategy=strategy,
                recursive_style=recursive_style,
                recursive_rounds=recursive_rounds,
                validation_commands=validation_commands,
                validation_profiles=validation_profiles,
                approved_validation_commands=approved_validation_commands,
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
            strategy = str(payload.get("strategy", "baseline"))
            recursive_style = str(payload.get("recursive_style", "deliberation"))
            recursive_rounds = self._read_recursive_rounds(payload)
            validation_commands = self._read_validation_commands(payload)
            validation_profiles = self._read_validation_profiles(payload)
            approved_validation_commands = self._read_approved_validation_commands(payload)
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
                    strategy=strategy,
                    recursive_style=recursive_style,
                    recursive_rounds=recursive_rounds,
                    validation_commands=validation_commands,
                    validation_profiles=validation_profiles,
                    approved_validation_commands=approved_validation_commands,
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

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/soloists/recursivemas/config":
            config_path = BeethovenConfig().clear_recursivemas_command()
            self._send_json({"config": {"id": "recursivemas", "command": "", "configured": False, "path": str(config_path)}})
            return
        if path == "/api/soloists/openai-compatible/config":
            config_path = BeethovenConfig().clear_openai_compatible()
            self._send_json(
                {
                    "config": {
                        "id": "openai-compatible",
                        "base_url": "",
                        "model": "",
                        "api_key_configured": False,
                        "configured": False,
                        "path": str(config_path),
                    }
                }
            )
            return
        if path == "/api/solomlx":
            self._send_json({"solomlx": solomlx_stop()})
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

    def _read_validation_profiles(self, payload: dict[str, Any]) -> list[str]:
        raw_validation_profiles = payload.get("validation_profiles", [])
        return (
            [
                str(profile)
                for profile in raw_validation_profiles
                if str(profile).strip()
            ]
            if isinstance(raw_validation_profiles, list)
            else []
        )

    def _read_approved_validation_commands(self, payload: dict[str, Any]) -> list[str]:
        raw_commands = payload.get("approved_validation_commands", [])
        return (
            [
                str(command)
                for command in raw_commands
                if str(command).strip()
            ]
            if isinstance(raw_commands, list)
            else []
        )

    def _read_recursive_rounds(self, payload: dict[str, Any]) -> int:
        try:
            return int(payload.get("recursive_rounds", 2))
        except (TypeError, ValueError):
            return 2

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
