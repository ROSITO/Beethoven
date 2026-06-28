from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from beethoven.desktop_server import BeethovenDesktopHandler


def test_desktop_api_runs_objective() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), BeethovenDesktopHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        host, port = server.server_address
        health = urlopen(f"http://{host}:{port}/api/health", timeout=2)
        health_data = json.loads(health.read().decode("utf-8"))
        assert health_data == {"status": "ok", "surface": "desktop"}

        request = Request(
            f"http://{host}:{port}/api/run",
            data=json.dumps({"objective": "test desktop api"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = urlopen(request, timeout=2)
        payload = json.loads(response.read().decode("utf-8"))
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
