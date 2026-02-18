"""Tests for the file operation auto-instrumentation integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import beacon_sdk
from beacon_sdk.integrations import file_patch
from beacon_sdk.models import SpanStatus, SpanType
from tests.conftest import InMemoryExporter


@pytest.fixture(autouse=True)
def _setup_tracer(tracer: Any, exporter: InMemoryExporter) -> Any:
    beacon_sdk._tracer = tracer  # type: ignore[assignment]
    yield
    beacon_sdk._tracer = None


@pytest.fixture(autouse=True)
def _patch_file() -> Any:
    """Apply and clean up file patches for each test."""
    file_patch.patch()
    yield
    file_patch.unpatch()


def test_file_read_creates_span(
    tmp_path: Path,
    exporter: InMemoryExporter,
) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    with open(str(test_file), "r") as f:
        f.read()

    assert len(exporter.spans) >= 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.FILE_OPERATION
    assert span.name == "open"
    assert span.attributes["file.operation"] == "read"
    assert span.attributes["file.path"] == str(test_file)
    assert span.attributes["file.size_bytes"] == 11
    assert span.status == SpanStatus.OK


def test_file_read_captures_content(
    tmp_path: Path,
    exporter: InMemoryExporter,
) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("captured content")

    with open(str(test_file), "r") as f:
        f.read()

    span = exporter.spans[0]
    assert span.attributes["file.content"] == "captured content"


def test_file_write_creates_span(
    tmp_path: Path,
    exporter: InMemoryExporter,
) -> None:
    test_file = tmp_path / "output.txt"

    with open(str(test_file), "w") as f:
        f.write("written data")

    assert len(exporter.spans) >= 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.FILE_OPERATION
    assert span.attributes["file.operation"] == "write"
    assert span.attributes["file.content"] == "written data"
    assert span.status == SpanStatus.OK


def test_file_append_creates_span(
    tmp_path: Path,
    exporter: InMemoryExporter,
) -> None:
    test_file = tmp_path / "append.txt"
    test_file.write_text("existing ")

    with open(str(test_file), "a") as f:
        f.write("appended")

    span = exporter.spans[0]
    assert span.attributes["file.operation"] == "append"
    assert span.attributes["file.content"] == "appended"


def test_file_content_truncated_at_2000(
    tmp_path: Path,
    exporter: InMemoryExporter,
) -> None:
    test_file = tmp_path / "large.txt"
    large_content = "x" * 3000
    test_file.write_text(large_content)

    with open(str(test_file), "r") as f:
        f.read()

    span = exporter.spans[0]
    content = span.attributes["file.content"]
    assert content.endswith("[TRUNCATED]")
    assert len(content) < 3000


def test_binary_mode_skips_content(
    tmp_path: Path,
    exporter: InMemoryExporter,
) -> None:
    test_file = tmp_path / "binary.bin"
    test_file.write_bytes(b"\x00\x01\x02\x03")

    with open(str(test_file), "rb") as f:
        f.read()

    span = exporter.spans[0]
    assert span.attributes["file.operation"] == "read"
    assert "file.content" not in span.attributes


def test_file_error_creates_error_span(
    exporter: InMemoryExporter,
) -> None:
    with pytest.raises(FileNotFoundError):
        open("/nonexistent/path/file.txt", "r")

    assert len(exporter.spans) >= 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.error_message is not None


def test_file_readline_captures_content(
    tmp_path: Path,
    exporter: InMemoryExporter,
) -> None:
    test_file = tmp_path / "lines.txt"
    test_file.write_text("line1\nline2\n")

    with open(str(test_file), "r") as f:
        f.readline()
        f.readline()

    span = exporter.spans[0]
    assert span.attributes["file.content"] == "line1\nline2\n"


def test_file_iteration_captures_content(
    tmp_path: Path,
    exporter: InMemoryExporter,
) -> None:
    test_file = tmp_path / "iter.txt"
    test_file.write_text("a\nb\nc\n")

    with open(str(test_file), "r") as f:
        for _ in f:
            pass

    span = exporter.spans[0]
    assert span.attributes["file.content"] == "a\nb\nc\n"


def test_file_writelines_captures_content(
    tmp_path: Path,
    exporter: InMemoryExporter,
) -> None:
    test_file = tmp_path / "writelines.txt"

    with open(str(test_file), "w") as f:
        f.writelines(["hello ", "world\n"])

    span = exporter.spans[0]
    assert span.attributes["file.content"] == "hello world\n"


def test_file_writelines_handles_generator(
    tmp_path: Path,
    exporter: InMemoryExporter,
) -> None:
    test_file = tmp_path / "gen.txt"

    def line_gen() -> Any:
        yield "line1\n"
        yield "line2\n"

    with open(str(test_file), "w") as f:
        f.writelines(line_gen())

    span = exporter.spans[0]
    assert span.attributes["file.content"] == "line1\nline2\n"


def test_file_readlines_captures_content(
    tmp_path: Path,
    exporter: InMemoryExporter,
) -> None:
    test_file = tmp_path / "readlines.txt"
    test_file.write_text("a\nb\nc\n")

    with open(str(test_file), "r") as f:
        f.readlines()

    span = exporter.spans[0]
    assert span.attributes["file.content"] == "a\nb\nc\n"


def test_file_patch_is_idempotent() -> None:
    file_patch.patch()
    first_open = open
    file_patch.patch()
    assert open is first_open


def test_file_unpatch_restores_original() -> None:
    file_patch.unpatch()
    original_open = open
    file_patch.patch()
    assert open is not original_open
    file_patch.unpatch()
    assert open is original_open
