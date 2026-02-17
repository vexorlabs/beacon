"""Tests for the subprocess auto-instrumentation integration."""

from __future__ import annotations

import subprocess
from typing import Any

import pytest

import beacon_sdk
from beacon_sdk.integrations import subprocess_patch
from beacon_sdk.models import SpanStatus, SpanType
from tests.conftest import InMemoryExporter


@pytest.fixture(autouse=True)
def _setup_tracer(tracer: Any, exporter: InMemoryExporter) -> Any:
    beacon_sdk._tracer = tracer  # type: ignore[assignment]
    yield
    beacon_sdk._tracer = None


@pytest.fixture(autouse=True)
def _patch_subprocess() -> Any:
    """Apply and clean up subprocess patches for each test."""
    subprocess_patch.patch()
    yield
    subprocess_patch.unpatch()


def test_subprocess_run_creates_shell_command_span(
    exporter: InMemoryExporter,
) -> None:
    subprocess.run(["echo", "hello"], capture_output=True)

    assert len(exporter.spans) >= 1
    span = exporter.spans[0]
    assert span.span_type == SpanType.SHELL_COMMAND
    assert span.name == "subprocess.run"
    assert span.attributes["shell.command"] == "echo hello"
    assert span.status == SpanStatus.OK


def test_subprocess_run_captures_stdout_when_piped(
    exporter: InMemoryExporter,
) -> None:
    subprocess.run(["echo", "hello world"], capture_output=True)

    span = exporter.spans[0]
    assert "hello world" in span.attributes["shell.stdout"]


def test_subprocess_run_records_returncode(
    exporter: InMemoryExporter,
) -> None:
    subprocess.run(["echo", "test"], capture_output=True)

    span = exporter.spans[0]
    assert span.attributes["shell.returncode"] == 0


def test_subprocess_run_error_on_nonzero_returncode(
    exporter: InMemoryExporter,
) -> None:
    subprocess.run(["false"], capture_output=True)

    span = exporter.spans[0]
    assert span.attributes["shell.returncode"] != 0
    assert span.status == SpanStatus.ERROR


def test_subprocess_run_captures_stderr(
    exporter: InMemoryExporter,
) -> None:
    result = subprocess.run(
        ["python3", "-c", "import sys; sys.stderr.write('error msg')"],
        capture_output=True,
    )

    span = exporter.spans[0]
    if result.stderr:
        assert "error msg" in span.attributes.get("shell.stderr", "")


def test_subprocess_check_output_creates_span(
    exporter: InMemoryExporter,
) -> None:
    subprocess.check_output(["echo", "test output"])

    # check_output internally calls run, so we get 2 spans.
    # Find the check_output span.
    check_spans = [s for s in exporter.spans if s.name == "subprocess.check_output"]
    assert len(check_spans) == 1
    span = check_spans[0]
    assert span.span_type == SpanType.SHELL_COMMAND
    assert span.attributes["shell.returncode"] == 0
    assert "test output" in span.attributes["shell.stdout"]


def test_subprocess_check_output_error_creates_error_span(
    exporter: InMemoryExporter,
) -> None:
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_output(["false"])

    check_spans = [s for s in exporter.spans if s.name == "subprocess.check_output"]
    assert len(check_spans) == 1
    span = check_spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.attributes["shell.returncode"] != 0


def test_subprocess_run_with_string_command(
    exporter: InMemoryExporter,
) -> None:
    subprocess.run("echo hello", shell=True, capture_output=True)

    span = exporter.spans[0]
    assert span.attributes["shell.command"] == "echo hello"


def test_subprocess_patch_is_idempotent() -> None:
    subprocess_patch.patch()
    first_run = subprocess.run
    subprocess_patch.patch()
    assert subprocess.run is first_run


def test_subprocess_unpatch_restores_original() -> None:
    subprocess_patch.unpatch()
    original_run = subprocess.run
    subprocess_patch.patch()
    assert subprocess.run is not original_run
    subprocess_patch.unpatch()
    assert subprocess.run is original_run
