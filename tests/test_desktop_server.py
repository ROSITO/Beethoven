from __future__ import annotations

import json
import sys
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from beethoven.packaging import write_recursivemas_bridge
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

        orchestrator = urlopen(f"http://{host}:{port}/api/orchestrator", timeout=2)
        orchestrator_data = json.loads(orchestrator.read().decode("utf-8"))

        solomlx = urlopen(f"http://{host}:{port}/api/solomlx", timeout=2)
        solomlx_data = json.loads(solomlx.read().decode("utf-8"))

        try:
            urlopen(f"http://{host}:{port}/api/soloists/recursivemas/check", timeout=2)
        except HTTPError as error:
            soloist_check_status = error.code
            soloist_check_data = json.loads(error.read().decode("utf-8"))

        bridge = tmp_path / "recursivemas_bridge.py"
        write_recursivemas_bridge(bridge)
        config_request = Request(
            f"http://{host}:{port}/api/soloists/recursivemas/config",
            data=json.dumps({"command": f"{sys.executable} {bridge}"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        config_payload = json.loads(urlopen(config_request, timeout=2).read().decode("utf-8"))
        configured_check = urlopen(f"http://{host}:{port}/api/soloists/recursivemas/check", timeout=2)
        configured_check_data = json.loads(configured_check.read().decode("utf-8"))
        delete_request = Request(
            f"http://{host}:{port}/api/soloists/recursivemas/config",
            method="DELETE",
        )
        clear_payload = json.loads(urlopen(delete_request, timeout=2).read().decode("utf-8"))

        openai_config_request = Request(
            f"http://{host}:{port}/api/soloists/openai-compatible/config",
            data=json.dumps(
                {
                    "base_url": "http://127.0.0.1:8080/v1",
                    "model": "local-model",
                    "api_key": "secret",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        openai_config_payload = json.loads(urlopen(openai_config_request, timeout=2).read().decode("utf-8"))
        openai_show_payload = json.loads(
            urlopen(f"http://{host}:{port}/api/soloists/openai-compatible/config", timeout=2)
            .read()
            .decode("utf-8")
        )
        openai_delete_request = Request(
            f"http://{host}:{port}/api/soloists/openai-compatible/config",
            method="DELETE",
        )
        openai_clear_payload = json.loads(urlopen(openai_delete_request, timeout=2).read().decode("utf-8"))

        skills = urlopen(f"http://{host}:{port}/api/skills", timeout=2)
        skills_data = json.loads(skills.read().decode("utf-8"))

        validation_profiles = urlopen(f"http://{host}:{port}/api/validation-profiles", timeout=2)
        validation_profiles_data = json.loads(validation_profiles.read().decode("utf-8"))

        workspace = urlopen(f"http://{host}:{port}/api/workspace", timeout=2)
        workspace_data = json.loads(workspace.read().decode("utf-8"))

        files = urlopen(f"http://{host}:{port}/api/files", timeout=2)
        files_data = json.loads(files.read().decode("utf-8"))

        diff = urlopen(f"http://{host}:{port}/api/diff", timeout=2)
        diff_data = json.loads(diff.read().decode("utf-8"))

        request = Request(
            f"http://{host}:{port}/api/run",
            data=json.dumps(
                {
                    "objective": "test desktop api",
                    "soloist": "local-echo",
                    "permission_mode": "read-only",
                    "effort": "high",
                    "validation_commands": [f"{sys.executable} -c \"print('ok')\""],
                    "validation_profiles": ["desktop"],
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = urlopen(request, timeout=2)
        payload = json.loads(response.read().decode("utf-8"))

        score_request = Request(
            f"http://{host}:{port}/api/score",
            data=json.dumps(
                {
                    "objective": "recursive desktop preview",
                    "strategy": "recursive",
                    "recursive_style": "sequential",
                    "recursive_rounds": 1,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        score_payload = json.loads(urlopen(score_request, timeout=2).read().decode("utf-8"))

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

        blocked_stream_request = Request(
            f"http://{host}:{port}/api/run/stream",
            data=json.dumps(
                {
                    "objective": "blocked validation desktop api",
                    "validation_commands": ["rm -rf build"],
                    "permission_mode": "ask",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        blocked_stream_response = urlopen(blocked_stream_request, timeout=2)
        blocked_stream_events = [
            json.loads(line.decode("utf-8"))
            for line in blocked_stream_response.readlines()
            if line.strip()
        ]

        approved_validation_request = Request(
            f"http://{host}:{port}/api/run",
            data=json.dumps(
                {
                    "objective": "approved validation desktop api",
                    "validation_commands": ["printf ok"],
                    "approved_validation_commands": ["printf ok"],
                    "permission_mode": "ask",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        approved_validation_payload = json.loads(
            urlopen(approved_validation_request, timeout=2).read().decode("utf-8")
        )

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
        "validation:validation-runner",
    ]
    assert payload["statuses"]["synthesize"] == "completed"
    assert payload["statuses"]["validation"] == "completed"
    assert payload["events"][0]["type"] == "score_started"
    assert payload["events"][-1]["type"] == "score_completed"
    assert payload["artifacts"]["validation"]["output"][0]["passed"] is True
    assert payload["artifacts"]["validation"]["metadata"]["profiles"][0]["id"] == "desktop"
    assert any(item["command"] == "node --check desktop/app.js" for item in payload["artifacts"]["validation"]["output"])
    assert payload["session"]["title"] == "test desktop api"
    assert payload["session"]["permission_mode"] == "read-only"
    assert payload["session"]["effort"] == "high"
    assert payload["score"]["metadata"]["permission_mode"] == "read-only"
    assert score_payload["metadata"]["strategy"] == "recursive"
    assert score_payload["metadata"]["recursive_style"] == "sequential"
    assert [task["id"] for task in score_payload["tasks"]] == [
        "decompose",
        "execute_round_1",
        "synthesize",
    ]
    assert any(session["id"] == payload["score"]["id"] for session in sessions_data["sessions"])
    assert "run" not in sessions_data["sessions"][0]
    assert detail_data["session"]["run"]["score"]["id"] == payload["score"]["id"]
    assert stream_events[0]["event"]["type"] == "score_started"
    assert stream_events[-1]["event"]["type"] == "run_completed"
    assert stream_events[-1]["event"]["context"]["score"]["objective"] == "stream desktop api"
    assert any(event["event"]["type"] == "validation_blocked" for event in blocked_stream_events)
    blocked_context = blocked_stream_events[-1]["event"]["context"]
    assert blocked_context["artifacts"]["validation"]["output"][0]["blocked"] is True
    assert approved_validation_payload["artifacts"]["validation"]["output"][0]["passed"] is True
    assert approved_validation_payload["artifacts"]["validation"]["metadata"]["approved_commands"] == ["printf ok"]
    assert soloists_data["soloists"][0]["id"] == "local-echo"
    assert soloists_data["soloists"][0]["status"] == "available"
    assert orchestrator_data["orchestrator"]["id"] == "beethoven-orchestrator"
    assert "available" in orchestrator_data["orchestrator"]
    assert solomlx_data["solomlx"]["id"] == "solomlx"
    assert "installed" in solomlx_data["solomlx"]
    assert soloist_check_status == 503
    assert soloist_check_data["check"]["status"] == "not_configured"
    assert config_payload["config"]["configured"] is True
    assert configured_check_data["check"]["status"] == "available"
    assert clear_payload["config"]["configured"] is False
    assert openai_config_payload["config"]["configured"] is True
    assert openai_config_payload["config"]["api_key_configured"] is True
    assert "secret" not in json.dumps(openai_config_payload)
    assert openai_show_payload["config"]["base_url"] == "http://127.0.0.1:8080/v1"
    assert openai_show_payload["config"]["model"] == "local-model"
    assert openai_clear_payload["config"]["configured"] is False
    assert skills_data["skills"][0]["id"] == "analyze"
    assert skills_data["skills"][0]["status"] == "available"
    assert validation_profiles_data["profiles"][0]["id"] == "desktop"
    assert validation_profiles_data["profiles"][-1]["id"] == "full"
    assert workspace_data["workspace"]["name"] == "Beethoven"
    assert "changes" in workspace_data["workspace"]
    assert files_data["workspace"]["name"] == "Beethoven"
    assert any(item["path"] == "README.md" for item in files_data["files"])
    assert diff_data["diff"]["workspace"]["name"] == "Beethoven"
    assert "status" in diff_data["diff"]


def test_desktop_api_can_trigger_solomlx_install(tmp_path, monkeypatch) -> None:
    class TestHandler(BeethovenDesktopHandler):
        store = DesktopSessionStore(tmp_path / "sessions.json")

    install_calls: list[dict[str, object]] = []

    def fake_install(*, upgrade: bool = False, with_mlx: bool = True) -> dict[str, object]:
        install_calls.append({"upgrade": upgrade, "with_mlx": with_mlx})
        return {
            "id": "solomlx",
            "installed": True,
            "path": "/tmp/SoloMLX-server",
            "with_mlx": with_mlx,
        }

    monkeypatch.setattr("beethoven.desktop_server.solomlx_install", fake_install)

    server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/solomlx/install",
            data=json.dumps({"upgrade": True, "with_mlx": False}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        payload = json.loads(urlopen(request, timeout=2).read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert install_calls == [{"upgrade": True, "with_mlx": False}]
    assert payload["solomlx"]["installed"] is True
    assert payload["solomlx"]["with_mlx"] is False


def test_desktop_api_can_ensure_solomlx_runtime(tmp_path, monkeypatch) -> None:
    class TestHandler(BeethovenDesktopHandler):
        store = DesktopSessionStore(tmp_path / "sessions.json")

    ensure_calls: list[dict[str, object]] = []

    def fake_ensure(**kwargs) -> dict[str, object]:
        ensure_calls.append(kwargs)
        return {
            "id": "solomlx",
            "status": "available",
            "ensured": True,
            "actions": [{"action": "start"}],
        }

    monkeypatch.setattr("beethoven.desktop_server.ensure_solomlx_orchestrator", fake_ensure)

    server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/solomlx/ensure",
            data=json.dumps(
                {
                    "install": False,
                    "prepare": True,
                    "start": True,
                    "with_mlx": False,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        payload = json.loads(urlopen(request, timeout=2).read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert ensure_calls == [
        {
            "auto_install": False,
            "auto_prepare": True,
            "auto_start": True,
            "with_mlx": False,
        }
    ]
    assert payload["solomlx"]["ensured"] is True
    assert payload["solomlx"]["actions"][0]["action"] == "start"
