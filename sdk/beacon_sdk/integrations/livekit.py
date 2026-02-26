"""LiveKit Agents auto-instrumentation for voice workflows."""

from __future__ import annotations

import json
import logging
from typing import Any

from beacon_sdk.models import SpanStatus, SpanType

logger = logging.getLogger("beacon_sdk")

_patched: bool = False
_original_start: Any = None
_original_run: Any = None
_original_say: Any = None
_original_generate_reply: Any = None
_original_interrupt: Any = None
_original_emit: Any = None

_MAX_ATTR_LEN: int = 50_000


def _truncate(value: str) -> str:
    """Truncate large string attributes to prevent oversized payloads."""
    return value[:_MAX_ATTR_LEN]


def _safe_json(value: Any) -> str:
    """Serialize objects safely for span attributes."""
    try:
        return _truncate(json.dumps(value, default=str))
    except Exception:
        return _truncate(str(value))


def _safe_text(value: Any) -> str:
    """Coerce to text safely with truncation."""
    if isinstance(value, str):
        return _truncate(value)
    return _safe_json(value)


def _resolve_agent_label(agent: Any) -> str | None:
    """Resolve a human-friendly agent label when possible."""
    label = getattr(agent, "label", None)
    if isinstance(label, str) and label:
        return _truncate(label)
    agent_id = getattr(agent, "id", None)
    if isinstance(agent_id, str) and agent_id:
        return _truncate(agent_id)
    return None


def _make_start_wrapper(original: Any) -> Any:
    """Create an async wrapper around AgentSession.start."""

    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return await original(self, *args, **kwargs)

        agent = kwargs.get("agent")
        if agent is None and args:
            agent = args[0]

        attrs: dict[str, Any] = {
            "agent.framework": "livekit",
            "agent.step_name": "AgentSession.start",
            "livekit.capture_run": bool(kwargs.get("capture_run", False)),
        }

        agent_label = _resolve_agent_label(agent)
        if agent_label is not None:
            attrs["livekit.agent.label"] = agent_label
        if agent is not None:
            instructions = getattr(agent, "instructions", None)
            if instructions is not None:
                attrs["livekit.agent.instructions"] = _safe_text(instructions)

        if "record" in kwargs:
            attrs["livekit.record"] = _safe_text(kwargs.get("record"))

        span, token = tracer.start_span(
            name="livekit.session.start",
            span_type=SpanType.AGENT_STEP,
            attributes=attrs,
        )
        try:
            result = await original(self, *args, **kwargs)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def _make_run_wrapper(original: Any) -> Any:
    """Create a sync wrapper around AgentSession.run."""

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, *args, **kwargs)

        user_input = kwargs.get("user_input")
        if user_input is None and args:
            user_input = args[0]

        attrs: dict[str, Any] = {
            "agent.framework": "livekit",
            "agent.step_name": "AgentSession.run",
            "livekit.input_modality": kwargs.get("input_modality", "text"),
        }
        if user_input is not None:
            attrs["agent.input"] = _safe_text(user_input)
        if kwargs.get("output_type") is not None:
            attrs["livekit.output_type"] = _safe_text(kwargs["output_type"])

        span, token = tracer.start_span(
            name="livekit.session.run",
            span_type=SpanType.AGENT_STEP,
            attributes=attrs,
        )
        try:
            result = original(self, *args, **kwargs)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def _make_say_wrapper(original: Any) -> Any:
    """Create a sync wrapper around AgentSession.say."""

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, *args, **kwargs)

        text = kwargs.get("text")
        if text is None and args:
            text = args[0]

        attrs: dict[str, Any] = {
            "agent.framework": "livekit",
            "agent.step_name": "AgentSession.say",
            "livekit.source": "say",
            "livekit.add_to_chat_ctx": kwargs.get("add_to_chat_ctx", True),
        }
        if "allow_interruptions" in kwargs:
            attrs["livekit.allow_interruptions"] = kwargs.get("allow_interruptions")
        if text is not None:
            if isinstance(text, str):
                attrs["agent.output"] = _truncate(text)
            else:
                attrs["agent.output"] = "<async_iterable>"

        span, token = tracer.start_span(
            name="livekit.session.say",
            span_type=SpanType.AGENT_STEP,
            attributes=attrs,
        )
        try:
            result = original(self, *args, **kwargs)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def _make_generate_reply_wrapper(original: Any) -> Any:
    """Create a sync wrapper around AgentSession.generate_reply."""

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, *args, **kwargs)

        user_input = kwargs.get("user_input")
        instructions = kwargs.get("instructions")
        tool_choice = kwargs.get("tool_choice")
        input_modality = kwargs.get("input_modality", "text")

        attrs: dict[str, Any] = {
            "agent.framework": "livekit",
            "agent.step_name": "AgentSession.generate_reply",
            "livekit.source": "generate_reply",
            "livekit.input_modality": input_modality,
        }
        if user_input is not None:
            attrs["agent.input"] = _safe_text(user_input)
        if instructions is not None:
            attrs["livekit.instructions"] = _safe_text(instructions)
        if tool_choice is not None:
            attrs["llm.tool_choice"] = _safe_text(tool_choice)
        if "allow_interruptions" in kwargs:
            attrs["livekit.allow_interruptions"] = kwargs.get("allow_interruptions")

        span, token = tracer.start_span(
            name="livekit.session.generate_reply",
            span_type=SpanType.AGENT_STEP,
            attributes=attrs,
        )
        try:
            result = original(self, *args, **kwargs)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def _make_interrupt_wrapper(original: Any) -> Any:
    """Create a sync wrapper around AgentSession.interrupt."""

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, *args, **kwargs)

        force = bool(kwargs.get("force", False))
        attrs = {
            "agent.framework": "livekit",
            "agent.step_name": "AgentSession.interrupt",
            "livekit.force": force,
        }
        span, token = tracer.start_span(
            name="livekit.session.interrupt",
            span_type=SpanType.AGENT_STEP,
            attributes=attrs,
        )
        try:
            result = original(self, *args, **kwargs)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def _event_span_data(
    event: Any, arg: Any
) -> tuple[str, SpanType, dict[str, Any], SpanStatus, str | None] | None:
    """Convert selected LiveKit events into Beacon span metadata."""
    if not isinstance(event, str):
        return None

    attrs: dict[str, Any] = {
        "agent.framework": "livekit",
        "livekit.event": event,
    }
    status = SpanStatus.OK
    error_message: str | None = None
    span_type = SpanType.CUSTOM
    name = f"livekit.event.{event}"

    if event == "user_input_transcribed":
        span_type = SpanType.AGENT_STEP
        transcript = getattr(arg, "transcript", None)
        if transcript is not None:
            attrs["agent.input"] = _safe_text(transcript)
        is_final = getattr(arg, "is_final", None)
        if is_final is not None:
            attrs["livekit.transcript.is_final"] = bool(is_final)
        speaker_id = getattr(arg, "speaker_id", None)
        if speaker_id is not None:
            attrs["livekit.speaker_id"] = _safe_text(speaker_id)
    elif event == "speech_created":
        span_type = SpanType.AGENT_STEP
        source = getattr(arg, "source", None)
        if source is not None:
            attrs["livekit.speech.source"] = _safe_text(source)
        user_initiated = getattr(arg, "user_initiated", None)
        if user_initiated is not None:
            attrs["livekit.speech.user_initiated"] = bool(user_initiated)
    elif event == "function_tools_executed":
        span_type = SpanType.TOOL_USE
        function_calls = getattr(arg, "function_calls", None)
        if isinstance(function_calls, list):
            tool_names = []
            for fn_call in function_calls:
                name_candidate = getattr(fn_call, "name", None)
                if name_candidate is not None:
                    tool_names.append(str(name_candidate))
            attrs["livekit.tool_call_count"] = len(function_calls)
            if len(tool_names) == 1:
                attrs["tool.name"] = _truncate(tool_names[0])
            elif len(tool_names) > 1:
                attrs["tool.names"] = _safe_json(tool_names)
    elif event == "error":
        error_obj = getattr(arg, "error", None)
        source = getattr(arg, "source", None)
        if error_obj is not None:
            error_message = _safe_text(error_obj)
            attrs["error.message"] = error_message
            attrs["livekit.error.type"] = type(error_obj).__name__
        if source is not None:
            attrs["livekit.error.source"] = _safe_text(type(source).__name__)
        status = SpanStatus.ERROR
    elif event == "close":
        reason = getattr(arg, "reason", None)
        reason_text = getattr(reason, "value", reason)
        if reason_text is not None:
            attrs["livekit.close.reason"] = _safe_text(reason_text)
        error_obj = getattr(arg, "error", None)
        if error_obj is not None:
            attrs["error.message"] = _safe_text(error_obj)
        if reason_text == "error":
            status = SpanStatus.ERROR
            error_message = (
                _safe_text(error_obj)
                if error_obj is not None
                else "Session closed with error"
            )
    else:
        return None

    return name, span_type, attrs, status, error_message


def _make_emit_wrapper(original: Any) -> Any:
    """Create a sync wrapper around AgentSession.emit for key voice events."""

    def wrapper(self: Any, event: Any, arg: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, event, arg, *args, **kwargs)

        event_data = _event_span_data(event, arg)
        if event_data is None:
            return original(self, event, arg, *args, **kwargs)

        name, span_type, attrs, status, error_message = event_data
        span, token = tracer.start_span(
            name=name, span_type=span_type, attributes=attrs
        )
        try:
            result = original(self, event, arg, *args, **kwargs)
            tracer.end_span(span, token, status=status, error_message=error_message)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise

    return wrapper


def patch() -> None:
    """Monkey-patch LiveKit AgentSession methods."""
    global _patched, _original_start, _original_run, _original_say
    global _original_generate_reply, _original_interrupt, _original_emit

    if _patched:
        return

    try:
        from livekit.agents import AgentSession
    except ImportError:
        return

    _original_start = AgentSession.start
    AgentSession.start = _make_start_wrapper(_original_start)

    if hasattr(AgentSession, "run"):
        _original_run = AgentSession.run
        AgentSession.run = _make_run_wrapper(_original_run)

    if hasattr(AgentSession, "say"):
        _original_say = AgentSession.say
        AgentSession.say = _make_say_wrapper(_original_say)

    if hasattr(AgentSession, "generate_reply"):
        _original_generate_reply = AgentSession.generate_reply
        AgentSession.generate_reply = _make_generate_reply_wrapper(
            _original_generate_reply
        )

    if hasattr(AgentSession, "interrupt"):
        _original_interrupt = AgentSession.interrupt
        AgentSession.interrupt = _make_interrupt_wrapper(_original_interrupt)

    if hasattr(AgentSession, "emit"):
        _original_emit = AgentSession.emit
        AgentSession.emit = _make_emit_wrapper(_original_emit)

    _patched = True
    logger.debug("Beacon: LiveKit auto-patch applied")


def unpatch() -> None:
    """Restore original LiveKit AgentSession methods."""
    global _patched, _original_start, _original_run, _original_say
    global _original_generate_reply, _original_interrupt, _original_emit

    if not _patched:
        return

    try:
        from livekit.agents import AgentSession
    except ImportError:
        return

    if _original_start is not None:
        AgentSession.start = _original_start
    if _original_run is not None and hasattr(AgentSession, "run"):
        AgentSession.run = _original_run
    if _original_say is not None and hasattr(AgentSession, "say"):
        AgentSession.say = _original_say
    if _original_generate_reply is not None and hasattr(AgentSession, "generate_reply"):
        AgentSession.generate_reply = _original_generate_reply
    if _original_interrupt is not None and hasattr(AgentSession, "interrupt"):
        AgentSession.interrupt = _original_interrupt
    if _original_emit is not None and hasattr(AgentSession, "emit"):
        AgentSession.emit = _original_emit

    _original_start = None
    _original_run = None
    _original_say = None
    _original_generate_reply = None
    _original_interrupt = None
    _original_emit = None

    _patched = False
    logger.debug("Beacon: LiveKit auto-patch removed")
