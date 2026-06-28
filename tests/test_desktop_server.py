from __future__ import annotations

import json
import sys
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from beethoven.desktop_server import BeethovenDesktopHandler
from beethoven.desktop_state import DesktopSessionStore


def test_desktop_api_runs_objective_and_lists_sessions(tmp_path) -> None:
    class TestHandler(BeethovenDesktopHandler):
        store = DesktopSessionStore(tmp_path / "sessions.json")

    server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        health = urlopen(f"http://{host}:{port}/api/health", timeout=2)
        health_data = json.loads(health.read().decode("utf-8"))
        assert health_data == {"status": "ok", "surface": "desktop"}

        soloists = urlopen(f"http://{host}:{port}/api/soloists", timeout=2)
        soloists_data = json.loads(soloists.read().decode("utf-8"))

        skills = urlopen(f"http://{host}:{port}/api/skills", timeout=2)
        skills_data = json.loads(skills.read().decode("utf-8"))

        workspace = urlopen(f"http://{host}:{port}/api/workspace", timeout=2)
        workspace_data = json.loads(workspace.read().decode("utf-8"))

        files = urlopen(f"http://{host}:{port}/api/files", timeout=2)
        files_data = json.loads(files.read().decode("utf-8"))

        request = Request(
            f"http://{host}:{port}/api/run",
            data=json.dumps(
                {
                    "objective": "test desktop api",
                    "soloist": "local-echo",
                    "permission_mode": "read-only",
                    "effort": "high",
                    "validation_commands": [f"{sys.executable} -c \"print('ok')\""],
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = urlopen(request, timeout=2)
        payload = json.loads(response.read().decode("utf-8"))

        second_request = Request(
            f"http://{host}:{port}/api/run",
            data=json.dumps({"objective": "second desktop api"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urlopen(second_request, timeout=2).read()

        stream_request = Request(
            f"http://{host}:{port}/api/run/stream",
            data=json.dumps({"objective": "stream desktop api"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        stream_response = urlopen(stream_request, timeout=2)
        stream_events = [
            json.loads(line.decode("utf-8"))
            for line in stream_response.readlines()
            if line.strip()
        ]

        sessions = urlopen(f"http://{host}:{port}/api/sessions", timeout=2)
        sessions_data = json.loads(sessions.read().decode("utf-8"))

        detail = urlopen(f"http://{host}:{port}/api/sessions/{payload['score']['id']}", timeout=2)
        detail_data = json.loads(detail.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload["score"]["objective"] == "test desktop api"
    assert payload["trace"] == [
        "understand:local-echo",
        "plan:local-echo",
        "synthesize:local-echo",
    ]
    assert payload["statuses"]["synthesize"] == "completed"
    assert payload["events"][0]["type"] == "score_started"
    assert payload["events"][-1]["type"] == "score_completed"
    assert payload["artifacts"]["validation"]["output"][0]["passed"] is True
    assert payload["session"]["title"] == "test desktop api"
    assert payload["session"]["permission_mode"] == "read-only"
    assert payload["session"]["effort"] == "high"
    assert payload["score"]["metadata"]["permission_mode"] == "read-only"
    assert any(session["id"] == payload["score"]["id"] for session in sessions_data["sessions"])
    assert "run" not in sessions_data["sessions"][0]
    assert detail_data["session"]["run"]["score"]["id"] == payload["score"]["id"]
    assert stream_events[0]["event"]["type"] == "score_started"
    assert stream_events[-1]["event"]["type"] == "run_completed"
    assert stream_events[-1]["event"]["context"]["score"]["objective"] == "stream desktop api"
    assert soloists_data["soloists"][0]["id"] == "local-echo"
    assert soloists_data["soloists"][0]["status"] == "available"
    assert skills_data["skills"][0]["id"] == "analyze"
    assert skills_data["skills"][0]["status"] == "available"
    assert workspace_data["workspace"]["name"] == "Beethoven"
    assert "changes" in workspace_data["workspace"]
    assert files_data["workspace"]["name"] == "Beethoven"
    assert any(item["path"] == "README.md" for item in files_data["files"])
