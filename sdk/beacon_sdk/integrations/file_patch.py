"""File operation auto-instrumentation. Patches builtins.open to create file_operation spans."""

from __future__ import annotations

import builtins
import logging
import os
from typing import Any

from beacon_sdk.models import SpanStatus, SpanType

logger = logging.getLogger("beacon_sdk")

_patched: bool = False
_original_open: Any = None

_SKIP_SUFFIXES = (".pyc", ".pyo")


def _mode_to_operation(mode: str) -> str:
    """Map a file mode string to a human-readable operation name."""
    base = mode.replace("b", "").replace("t", "")
    if base in ("r", ""):
        return "read"
    if base in ("w", "x"):
        return "write"
    if base == "a":
        return "append"
    if "+" in base:
        return "read_write"
    return "read"


def _should_skip(file_path: str) -> bool:
    """Return True if this file path should not be traced."""
    if file_path.endswith(_SKIP_SUFFIXES):
        return True
    if "site-packages" in file_path:
        return True
    return False


class _TrackedFile:
    """Wrapper around a file object that creates a span on close."""

    def __init__(
        self,
        file_obj: Any,
        tracer: Any,
        path: str,
        operation: str,
        is_binary: bool,
    ) -> None:
        self._file = file_obj
        self._tracer = tracer
        self._path = path
        self._operation = operation
        self._is_binary = is_binary
        self._content_parts: list[str] = []
        self._closed = False

        self._span, self._token = tracer.start_span(
            name="open",
            span_type=SpanType.FILE_OPERATION,
            attributes={
                "file.path": path,
                "file.operation": operation,
            },
        )

    # -- Read interception --

    def read(self, *args: Any, **kwargs: Any) -> Any:
        data = self._file.read(*args, **kwargs)
        if not self._is_binary and isinstance(data, str):
            self._content_parts.append(data)
        return data

    def readline(self, *args: Any, **kwargs: Any) -> Any:
        data = self._file.readline(*args, **kwargs)
        if not self._is_binary and isinstance(data, str):
            self._content_parts.append(data)
        return data

    def readlines(self, *args: Any, **kwargs: Any) -> Any:
        lines = self._file.readlines(*args, **kwargs)
        if not self._is_binary and isinstance(lines, list):
            for line in lines:
                if isinstance(line, str):
                    self._content_parts.append(line)
        return lines

    # -- Write interception --

    def write(self, data: Any) -> Any:
        result = self._file.write(data)
        if not self._is_binary and isinstance(data, str):
            self._content_parts.append(data)
        return result

    def writelines(self, lines: Any) -> Any:
        collected = list(lines)
        result = self._file.writelines(collected)
        if not self._is_binary:
            for line in collected:
                if isinstance(line, str):
                    self._content_parts.append(line)
        return result

    # -- Iteration --

    def __iter__(self) -> _TrackedFile:
        return self

    def __next__(self) -> Any:
        data = next(self._file)
        if not self._is_binary and isinstance(data, str):
            self._content_parts.append(data)
        return data

    # -- Context manager --

    def __enter__(self) -> _TrackedFile:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is not None:
            self._finalize(status=SpanStatus.ERROR, error_message=str(exc_val))
        else:
            self._finalize(status=SpanStatus.OK)
        self._file.close()
        return False

    # -- Close --

    def close(self) -> None:
        self._finalize(status=SpanStatus.OK)
        self._file.close()

    # -- Delegation --

    def __getattr__(self, name: str) -> Any:
        return getattr(self._file, name)

    # -- Finalization --

    def _finalize(
        self,
        status: SpanStatus = SpanStatus.OK,
        error_message: str | None = None,
    ) -> None:
        if self._closed:
            return
        self._closed = True

        content = "".join(self._content_parts)
        if content:
            self._span.set_attribute("file.content", content)

        try:
            size = os.path.getsize(self._path)
            self._span.set_attribute("file.size_bytes", size)
        except OSError:
            if content:
                self._span.set_attribute(
                    "file.size_bytes", len(content.encode("utf-8", errors="replace"))
                )

        self._tracer.end_span(
            self._span, self._token, status=status, error_message=error_message
        )


def _patched_open_fn(original: Any) -> Any:
    """Create a wrapper around builtins.open."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(*args, **kwargs)

        file_path = args[0] if args else kwargs.get("file", "")
        path_str = str(file_path)

        if _should_skip(path_str):
            return original(*args, **kwargs)

        mode = args[1] if len(args) > 1 else kwargs.get("mode", "r")
        mode_str = str(mode)
        operation = _mode_to_operation(mode_str)
        is_binary = "b" in mode_str

        try:
            file_obj = original(*args, **kwargs)
        except Exception as exc:
            span, token = tracer.start_span(
                name="open",
                span_type=SpanType.FILE_OPERATION,
                attributes={
                    "file.path": path_str,
                    "file.operation": operation,
                },
            )
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

        return _TrackedFile(file_obj, tracer, path_str, operation, is_binary)

    return wrapper


def patch() -> None:
    """Monkey-patch builtins.open to trace file operations."""
    global _patched, _original_open

    if _patched:
        return

    _original_open = builtins.open
    builtins.open = _patched_open_fn(_original_open)

    _patched = True
    logger.debug("Beacon: file operation auto-patch applied")


def unpatch() -> None:
    """Restore original builtins.open."""
    global _patched, _original_open

    if not _patched:
        return

    if _original_open is not None:
        builtins.open = _original_open

    _original_open = None
    _patched = False
    logger.debug("Beacon: file operation auto-patch removed")
