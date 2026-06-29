from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_beethoven_home(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BEETHOVEN_HOME", str(tmp_path / "beethoven-home"))
    monkeypatch.setenv("BEETHOVEN_DYNAMIC_PLANNING", "0")
