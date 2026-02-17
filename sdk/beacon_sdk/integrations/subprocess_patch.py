"""Subprocess auto-instrumentation. Patches subprocess.run and check_output to create shell spans."""

from __future__ import annotations

import logging
import subprocess
from typing import Any

from beacon_sdk.models import SpanStatus, SpanType

logger = logging.getLogger("beacon_sdk")

_patched: bool = False
_original_run: Any = None
_original_check_output: Any = None


def _extract_command(args: Any) -> str:
    """Convert subprocess args to a command string."""
    if isinstance(args, (list, tuple)):
        return " ".join(str(a) for a in args)
    return str(args)


def _decode_output(data: bytes | str | None) -> str | None:
    """Decode subprocess output bytes to string."""
    if data is None:
        return None
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return str(data)


def _patched_run_fn(original: Any) -> Any:
    """Create a wrapper around subprocess.run."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(*args, **kwargs)

        cmd_args = args[0] if args else kwargs.get("args", "")
        command_str = _extract_command(cmd_args)

        span, token = tracer.start_span(
            name="subprocess.run",
            span_type=SpanType.SHELL_COMMAND,
            attributes={"shell.command": command_str},
        )

        try:
            result = original(*args, **kwargs)
            span.set_attribute("shell.returncode", result.returncode)

            stdout = _decode_output(result.stdout)
            if stdout is not None:
                span.set_attribute("shell.stdout", stdout)

            stderr = _decode_output(result.stderr)
            if stderr is not None:
                span.set_attribute("shell.stderr", stderr)

            status = SpanStatus.ERROR if result.returncode != 0 else SpanStatus.OK
            tracer.end_span(span, token, status=status)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def _patched_check_output_fn(original: Any) -> Any:
    """Create a wrapper around subprocess.check_output."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(*args, **kwargs)

        cmd_args = args[0] if args else kwargs.get("args", "")
        command_str = _extract_command(cmd_args)

        span, token = tracer.start_span(
            name="subprocess.check_output",
            span_type=SpanType.SHELL_COMMAND,
            attributes={"shell.command": command_str},
        )

        try:
            result = original(*args, **kwargs)
            stdout = _decode_output(result)
            if stdout is not None:
                span.set_attribute("shell.stdout", stdout)
            span.set_attribute("shell.returncode", 0)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except subprocess.CalledProcessError as exc:
            span.set_attribute("shell.returncode", exc.returncode)
            stdout = _decode_output(exc.output)
            if stdout is not None:
                span.set_attribute("shell.stdout", stdout)
            stderr = _decode_output(exc.stderr)
            if stderr is not None:
                span.set_attribute("shell.stderr", stderr)
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def patch() -> None:
    """Monkey-patch subprocess.run and subprocess.check_output."""
    global _patched, _original_run, _original_check_output

    if _patched:
        return

    _original_run = subprocess.run
    subprocess.run = _patched_run_fn(_original_run)

    _original_check_output = subprocess.check_output
    subprocess.check_output = _patched_check_output_fn(_original_check_output)

    _patched = True
    logger.debug("Beacon: subprocess auto-patch applied")


def unpatch() -> None:
    """Restore original subprocess functions."""
    global _patched, _original_run, _original_check_output

    if not _patched:
        return

    if _original_run is not None:
        subprocess.run = _original_run
    if _original_check_output is not None:
        subprocess.check_output = _original_check_output

    _original_run = None
    _original_check_output = None
    _patched = False
    logger.debug("Beacon: subprocess auto-patch removed")
