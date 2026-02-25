"""AutoGen auto-instrumentation. Patches ConversableAgent and GroupChat for tracing."""

from __future__ import annotations

import json
import logging
from typing import Any

from beacon_sdk.models import SpanStatus, SpanType

logger = logging.getLogger("beacon_sdk")

_patched: bool = False
_original_generate_reply: Any = None
_original_a_generate_reply: Any = None
_original_run_chat: Any = None
_original_a_run_chat: Any = None


# ---------------------------------------------------------------------------
# Response attribute extraction
# ---------------------------------------------------------------------------


def _safe_str(obj: Any, max_len: int = 50_000) -> str:
    """Convert an object to a truncated string."""
    try:
        if isinstance(obj, str):
            return obj[:max_len]
        return json.dumps(obj, default=str)[:max_len]
    except Exception:
        return str(obj)[:max_len]


# ---------------------------------------------------------------------------
# Patched function factories
# ---------------------------------------------------------------------------


def _make_generate_reply_wrapper(original: Any) -> Any:
    """Create a sync wrapper around ConversableAgent.generate_reply."""

    def wrapper(self: Any, messages: Any = None, sender: Any = None, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, messages=messages, sender=sender, **kwargs)

        agent_name = getattr(self, "name", "unknown")
        sender_name = getattr(sender, "name", None) if sender else None

        attrs: dict[str, Any] = {
            "agent.framework": "autogen",
            "agent.step_name": agent_name,
        }
        if sender_name:
            attrs["autogen.sender"] = sender_name
        if messages:
            try:
                last_msg = messages[-1] if isinstance(messages, list) else messages
                attrs["agent.input"] = _safe_str(last_msg)
            except Exception:
                pass

        span, token = tracer.start_span(
            name=f"agent.generate_reply: {agent_name}",
            span_type=SpanType.AGENT_STEP,
            attributes=attrs,
        )
        try:
            result = original(self, messages=messages, sender=sender, **kwargs)
            if result is not None:
                span.set_attribute("agent.output", _safe_str(result))
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(span, token, status=SpanStatus.ERROR, error_message=str(exc))
            raise

    return wrapper


def _make_async_generate_reply_wrapper(original: Any) -> Any:
    """Create an async wrapper around ConversableAgent.a_generate_reply."""

    async def wrapper(self: Any, messages: Any = None, sender: Any = None, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return await original(self, messages=messages, sender=sender, **kwargs)

        agent_name = getattr(self, "name", "unknown")
        sender_name = getattr(sender, "name", None) if sender else None

        attrs: dict[str, Any] = {
            "agent.framework": "autogen",
            "agent.step_name": agent_name,
        }
        if sender_name:
            attrs["autogen.sender"] = sender_name
        if messages:
            try:
                last_msg = messages[-1] if isinstance(messages, list) else messages
                attrs["agent.input"] = _safe_str(last_msg)
            except Exception:
                pass

        span, token = tracer.start_span(
            name=f"agent.generate_reply: {agent_name}",
            span_type=SpanType.AGENT_STEP,
            attributes=attrs,
        )
        try:
            result = await original(self, messages=messages, sender=sender, **kwargs)
            if result is not None:
                span.set_attribute("agent.output", _safe_str(result))
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(span, token, status=SpanStatus.ERROR, error_message=str(exc))
            raise

    return wrapper


def _make_run_chat_wrapper(original: Any) -> Any:
    """Create a sync wrapper around GroupChat.run."""

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, *args, **kwargs)

        agent_names = [getattr(a, "name", "?") for a in getattr(self, "agents", [])]
        max_round = getattr(self, "max_round", None)

        attrs: dict[str, Any] = {
            "agent.framework": "autogen",
            "agent.step_name": "GroupChat",
            "autogen.num_agents": len(agent_names),
            "autogen.agent_names": json.dumps(agent_names),
        }
        if max_round is not None:
            attrs["autogen.max_round"] = max_round

        span, token = tracer.start_span(
            name="groupchat.run",
            span_type=SpanType.AGENT_STEP,
            attributes=attrs,
        )
        try:
            result = original(self, *args, **kwargs)
            if result is not None:
                span.set_attribute("agent.output", _safe_str(result))
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(span, token, status=SpanStatus.ERROR, error_message=str(exc))
            raise

    return wrapper


def _make_async_run_chat_wrapper(original: Any) -> Any:
    """Create an async wrapper around GroupChat.a_run."""

    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return await original(self, *args, **kwargs)

        agent_names = [getattr(a, "name", "?") for a in getattr(self, "agents", [])]
        max_round = getattr(self, "max_round", None)

        attrs: dict[str, Any] = {
            "agent.framework": "autogen",
            "agent.step_name": "GroupChat",
            "autogen.num_agents": len(agent_names),
            "autogen.agent_names": json.dumps(agent_names),
        }
        if max_round is not None:
            attrs["autogen.max_round"] = max_round

        span, token = tracer.start_span(
            name="groupchat.run",
            span_type=SpanType.AGENT_STEP,
            attributes=attrs,
        )
        try:
            result = await original(self, *args, **kwargs)
            if result is not None:
                span.set_attribute("agent.output", _safe_str(result))
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(span, token, status=SpanStatus.ERROR, error_message=str(exc))
            raise

    return wrapper


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def patch() -> None:
    """Monkey-patch AutoGen classes to auto-instrument agent interactions."""
    global _patched, _original_generate_reply, _original_a_generate_reply
    global _original_run_chat, _original_a_run_chat

    if _patched:
        return

    try:
        from autogen import ConversableAgent, GroupChat
    except ImportError:
        return

    _original_generate_reply = ConversableAgent.generate_reply
    ConversableAgent.generate_reply = _make_generate_reply_wrapper(_original_generate_reply)

    if hasattr(ConversableAgent, "a_generate_reply"):
        _original_a_generate_reply = ConversableAgent.a_generate_reply
        ConversableAgent.a_generate_reply = _make_async_generate_reply_wrapper(
            _original_a_generate_reply
        )

    _original_run_chat = GroupChat.run
    GroupChat.run = _make_run_chat_wrapper(_original_run_chat)

    if hasattr(GroupChat, "a_run"):
        _original_a_run_chat = GroupChat.a_run
        GroupChat.a_run = _make_async_run_chat_wrapper(_original_a_run_chat)

    _patched = True
    logger.debug("Beacon: AutoGen auto-patch applied")


def unpatch() -> None:
    """Restore original AutoGen methods."""
    global _patched, _original_generate_reply, _original_a_generate_reply
    global _original_run_chat, _original_a_run_chat

    if not _patched:
        return

    try:
        from autogen import ConversableAgent, GroupChat
    except ImportError:
        return

    if _original_generate_reply is not None:
        ConversableAgent.generate_reply = _original_generate_reply
    if _original_a_generate_reply is not None and hasattr(ConversableAgent, "a_generate_reply"):
        ConversableAgent.a_generate_reply = _original_a_generate_reply
    if _original_run_chat is not None:
        GroupChat.run = _original_run_chat
    if _original_a_run_chat is not None and hasattr(GroupChat, "a_run"):
        GroupChat.a_run = _original_a_run_chat

    _original_generate_reply = None
    _original_a_generate_reply = None
    _original_run_chat = None
    _original_a_run_chat = None
    _patched = False
    logger.debug("Beacon: AutoGen auto-patch removed")
