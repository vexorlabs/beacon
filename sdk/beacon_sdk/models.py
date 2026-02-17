from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpanType(str, Enum):
    LLM_CALL = "llm_call"
    TOOL_USE = "tool_use"
    AGENT_STEP = "agent_step"
    BROWSER_ACTION = "browser_action"
    FILE_OPERATION = "file_operation"
    SHELL_COMMAND = "shell_command"
    CHAIN = "chain"
    CUSTOM = "custom"


class SpanStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


TRUNCATION_LIMITS: dict[str, int] = {
    "llm.prompt": 50_000,
    "llm.completion": 50_000,
    "file.content": 2_000,
    "shell.stdout": 4_000,
    "shell.stderr": 4_000,
}

SCREENSHOT_MAX_BYTES: int = 500_000


@dataclass
class Span:
    """A single unit of work in a trace."""

    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = ""
    parent_span_id: str | None = None

    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    span_type: SpanType = SpanType.CUSTOM
    name: str = ""
    status: SpanStatus = SpanStatus.UNSET

    error_message: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute, applying truncation limits."""
        if isinstance(value, str) and key in TRUNCATION_LIMITS:
            limit = TRUNCATION_LIMITS[key]
            if len(value) > limit:
                value = value[:limit] + "[TRUNCATED]"
        if key == "browser.screenshot" and isinstance(value, str):
            if len(value) > SCREENSHOT_MAX_BYTES:
                value = None
        self.attributes[key] = value

    def end(
        self,
        status: SpanStatus = SpanStatus.OK,
        error_message: str | None = None,
    ) -> None:
        """Mark span as completed."""
        self.end_time = time.time()
        self.status = status
        if error_message is not None:
            self.error_message = error_message

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict matching POST /v1/spans format."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "span_type": self.span_type.value,
            "name": self.name,
            "status": self.status.value,
            "error_message": self.error_message,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "attributes": self.attributes,
        }
