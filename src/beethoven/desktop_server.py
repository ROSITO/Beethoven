"""Local desktop server for the Beethoven workbench prototype."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from beethoven.runtime import run_objective, score_objective
from beethoven.serialization import context_to_dict, score_to_dict


DESKTOP_ROOT = Path(__file__).resolve().parents[2] / "desktop"


class BeethovenDesktopHandler(SimpleHTTPRequestHandler):
    """Serve desktop assets and the first local orchestration API."""

    server_version = "BeethovenDesktop/0.1"

    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, directory=directory or str(DESKTOP_ROOT), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json({"status": "ok", "surface": "desktop"})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/score":
            objective = self._read_objective()
            if objective is None:
                return
            self._send_json(score_to_dict(score_objective(objective)))
            return

        if self.path == "/api/run":
            objective = self._read_objective()
            if objective is None:
                return
            self._send_json(context_to_dict(run_objective(objective)))
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_objective(self) -> str | None:
        content_length = int(self.headers.get("Content-Length", "0"))
        try:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(raw_body or "{}")
        except json.JSONDecodeError:
            self._send_json({"error": "Request body must be valid JSON"}, HTTPStatus.BAD_REQUEST)
            return None

        objective = str(payload.get("objective", "")).strip()
        if not objective:
            self._send_json({"error": "Missing objective"}, HTTPStatus.BAD_REQUEST)
            return None
        return objective

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve_desktop(host: str = "127.0.0.1", port: int = 4173) -> None:
    server = ThreadingHTTPServer((host, port), BeethovenDesktopHandler)
    print(f"Beethoven desktop running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
