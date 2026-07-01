from __future__ import annotations

from beethoven.workspace import list_workspace_files, read_workspace_attachments


def test_workspace_attachment_includes_metadata_and_snippet(tmp_path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n\nUseful context for Beethoven.\n", encoding="utf-8")

    attachments = read_workspace_attachments("Review @README.md", path=tmp_path)

    assert attachments[0]["status"] == "attached"
    assert attachments[0]["media_type"] == "text/markdown"
    assert attachments[0]["extension"] == "md"
    assert attachments[0]["snippet"] == "# Title Useful context for Beethoven."
    assert attachments[0]["content"].startswith("# Title")


def test_workspace_attachment_blocks_binary_files(tmp_path) -> None:
    binary = tmp_path / "sample.bin"
    binary.write_bytes(b"\x00\x01\x02\x03")

    attachments = read_workspace_attachments("Review @sample.bin", path=tmp_path)

    assert attachments[0]["status"] == "blocked"
    assert attachments[0]["reason"] == "binary file"
    assert "content" not in attachments[0]


def test_workspace_attachment_enforces_total_budget(tmp_path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("a" * 20, encoding="utf-8")
    second.write_text("b" * 20, encoding="utf-8")

    attachments = read_workspace_attachments(
        "Review @first.txt @second.txt",
        path=tmp_path,
        max_bytes=20,
        max_total_bytes=20,
    )

    assert attachments[0]["status"] == "attached"
    assert attachments[0]["bytes"] == 20
    assert attachments[1]["status"] == "blocked"
    assert attachments[1]["reason"] == "attachment budget exhausted"


def test_workspace_directory_attachment_expands_bounded_files(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("alpha", encoding="utf-8")
    (docs / "b.md").write_text("bravo", encoding="utf-8")
    (docs / "c.md").write_text("charlie", encoding="utf-8")

    attachments = read_workspace_attachments(
        "Review @docs",
        path=tmp_path,
        max_directory_files=2,
    )

    assert [item["path"] for item in attachments] == ["docs/a.md", "docs/b.md"]
    assert all(item["status"] == "attached" for item in attachments)
    assert all(item["source_directory"] == "docs" for item in attachments)


def test_workspace_file_listing_exposes_size_and_media_type(tmp_path) -> None:
    (tmp_path / "app.py").write_text("print('ok')", encoding="utf-8")

    payload = list_workspace_files(tmp_path)

    file_info = payload["files"][0]
    assert file_info["path"] == "app.py"
    assert file_info["bytes"] > 0
    assert file_info["media_type"] == "text/x-python"
