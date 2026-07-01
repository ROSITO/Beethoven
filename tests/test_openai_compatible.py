from __future__ import annotations

import json
from io import BytesIO
from urllib.request import Request

from beethoven.core import Capability, ExecutionContext, Score, SoloistResult, Task
from beethoven.runtime import create_default_registry, list_soloists, run_objective
from beethoven.soloists import OpenAICompatibleSoloist, check_openai_compatible


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_openai_compatible_check_uses_models_endpoint(monkeypatch) -> None:
    requests: list[Request] = []
    monkeypatch.setenv("BEETHOVEN_OPENAI_COMPAT_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setenv("BEETHOVEN_OPENAI_COMPAT_MODEL", "local-model")
    monkeypatch.setenv("BEETHOVEN_OPENAI_COMPAT_API_KEY", "secret")

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        requests.append(request)
        assert timeout == 1.5
        return FakeResponse({"data": [{"id": "local-model"}]})

    monkeypatch.setattr("beethoven.soloists.urlopen", fake_urlopen)

    report = check_openai_compatible()

    assert report["available"] is True
    assert report["status"] == "available"
    assert report["model"] == "local-model"
    assert requests[0].full_url == "http://127.0.0.1:9999/v1/models"
    assert requests[0].headers["Authorization"] == "Bearer secret"


def test_openai_compatible_soloist_posts_chat_completion(monkeypatch) -> None:
    requests: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setenv("BEETHOVEN_OPENAI_COMPAT_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setenv("BEETHOVEN_OPENAI_COMPAT_MODEL", "local-model")

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        body = json.loads(BytesIO(request.data or b"{}").read().decode("utf-8"))
        requests.append((request.full_url, body))
        assert timeout == 120.0
        return FakeResponse(
            {
                "choices": [{"message": {"content": "adapter answer"}}],
                "usage": {"total_tokens": 42},
            }
        )

    monkeypatch.setattr("beethoven.soloists.urlopen", fake_urlopen)
    task = Task(id="answer", instruction="Answer with context.", capability=Capability.SYNTHESIZE)
    score = Score(id="score-test", objective="Use adapter", tasks=(task,), metadata={})

    result = OpenAICompatibleSoloist().perform(task, ExecutionContext(score=score))

    assert result.output == "adapter answer"
    assert result.tokens == 42
    assert result.metadata["mode"] == "openai-compatible"
    assert requests[0][0] == "http://127.0.0.1:9999/v1/chat/completions"
    assert requests[0][1]["model"] == "local-model"


def test_openai_compatible_can_be_routed_when_available(monkeypatch) -> None:
    monkeypatch.setenv("BEETHOVEN_OPENAI_COMPAT_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setattr("beethoven.runtime.openai_compatible_is_available", lambda: True)
    monkeypatch.setattr("beethoven.runtime.check_openai_compatible", lambda: {"available": True, "status": "available"})
    monkeypatch.setattr(
        "beethoven.soloists.OpenAICompatibleSoloist.perform",
        lambda self, task, context: SoloistResult(output="ok", metadata={"mode": "openai-compatible"}),
    )

    soloists = list_soloists()
    registry = create_default_registry()
    context = run_objective("use configured adapter", soloist="openai-compatible")

    assert next(item for item in soloists if item["id"] == "openai-compatible")["status"] == "available"
    assert any(soloist.name == "openai-compatible" for soloist in registry.all())
    assert context.trace == [
        "understand:openai-compatible",
        "plan:openai-compatible",
        "synthesize:openai-compatible",
    ]
