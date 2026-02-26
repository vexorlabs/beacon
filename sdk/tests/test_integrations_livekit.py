"""Tests for the LiveKit Agents auto-instrumentation integration."""

from __future__ import annotations

import asyncio
import builtins
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch as mock_patch

import pytest

import beacon_sdk
from beacon_sdk.integrations import livekit as livekit_patch
from beacon_sdk.models import SpanStatus, SpanType
from tests.conftest import InMemoryExporter


@pytest.fixture(autouse=True)
def _setup_tracer(tracer: Any, exporter: InMemoryExporter) -> Any:
    beacon_sdk._tracer = tracer  # type: ignore[assignment]
    yield
    beacon_sdk._tracer = None
    from beacon_sdk.context import _trace_context

    _trace_context.set(None)


class FakeAgent:
    def __init__(
        self, label: str = "SupportAgent", instructions: str = "Be helpful."
    ) -> None:
        self.label = label
        self.instructions = instructions


class FakeFunctionCall:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeAgentSession:
    should_error_start: bool = False
    should_error_run: bool = False
    should_error_say: bool = False
    should_error_generate_reply: bool = False
    should_error_interrupt: bool = False

    def __init__(self) -> None:
        self.emitted_events: list[tuple[Any, Any]] = []

    async def start(self, agent: Any, **kwargs: Any) -> Any:
        if self.should_error_start:
            raise RuntimeError("LiveKit start failed")
        return SimpleNamespace(started=True, agent=agent, kwargs=kwargs)

    def run(
        self,
        *,
        user_input: str,
        input_modality: str = "text",
        output_type: Any = None,
    ) -> Any:
        if self.should_error_run:
            raise RuntimeError("LiveKit run failed")
        return SimpleNamespace(
            user_input=user_input,
            input_modality=input_modality,
            output_type=output_type,
        )

    def say(
        self,
        text: str,
        *,
        allow_interruptions: bool | None = None,
        add_to_chat_ctx: bool = True,
    ) -> Any:
        if self.should_error_say:
            raise RuntimeError("LiveKit say failed")
        return SimpleNamespace(text=text, allow_interruptions=allow_interruptions)

    def generate_reply(
        self,
        *,
        user_input: str | None = None,
        instructions: str | None = None,
        tool_choice: Any = None,
        allow_interruptions: bool | None = None,
        input_modality: str = "text",
    ) -> Any:
        if self.should_error_generate_reply:
            raise RuntimeError("LiveKit generate_reply failed")
        return SimpleNamespace(
            user_input=user_input,
            instructions=instructions,
            tool_choice=tool_choice,
            allow_interruptions=allow_interruptions,
            input_modality=input_modality,
        )

    def interrupt(self, *, force: bool = False) -> Any:
        if self.should_error_interrupt:
            raise RuntimeError("LiveKit interrupt failed")
        return SimpleNamespace(force=force)

    def emit(self, event: Any, arg: Any) -> None:
        self.emitted_events.append((event, arg))


@pytest.fixture()
def _mock_livekit() -> Any:
    livekit_agents_mod = SimpleNamespace(AgentSession=FakeAgentSession)
    livekit_mod = SimpleNamespace(agents=livekit_agents_mod)
    with mock_patch.dict(
        "sys.modules",
        {"livekit": livekit_mod, "livekit.agents": livekit_agents_mod},
    ):
        livekit_patch._patched = False
        livekit_patch._original_start = None
        livekit_patch._original_run = None
        livekit_patch._original_say = None
        livekit_patch._original_generate_reply = None
        livekit_patch._original_interrupt = None
        livekit_patch._original_emit = None
        yield livekit_mod
        livekit_patch.unpatch()
        livekit_patch._patched = False


class TestPatchMechanics:
    def test_patch_is_idempotent(self, _mock_livekit: Any) -> None:
        livekit_patch.patch()
        first_start = FakeAgentSession.start
        livekit_patch.patch()
        assert FakeAgentSession.start is first_start

    def test_unpatch_restores_original(self, _mock_livekit: Any) -> None:
        original_start = FakeAgentSession.start
        original_emit = FakeAgentSession.emit
        livekit_patch.patch()
        assert FakeAgentSession.start is not original_start
        assert FakeAgentSession.emit is not original_emit
        livekit_patch.unpatch()
        assert FakeAgentSession.start is original_start
        assert FakeAgentSession.emit is original_emit

    def test_patch_skips_when_not_installed(self) -> None:
        livekit_patch._patched = False
        original_import = builtins.__import__

        def _import_without_livekit(
            name: str,
            globals_: Any = None,
            locals_: Any = None,
            fromlist: Any = (),
            level: int = 0,
        ) -> Any:
            if name == "livekit.agents":
                raise ImportError("No module named 'livekit.agents'")
            return original_import(name, globals_, locals_, fromlist, level)

        with mock_patch("builtins.__import__", side_effect=_import_without_livekit):
            livekit_patch.patch()
        assert livekit_patch._patched is False


class TestSessionMethods:
    def test_start_creates_agent_step_span(
        self, _mock_livekit: Any, exporter: InMemoryExporter
    ) -> None:
        livekit_patch.patch()
        session = FakeAgentSession()
        agent = FakeAgent(label="PhoneAgent", instructions="You are a phone assistant.")

        result = asyncio.run(session.start(agent, capture_run=True))

        assert result.started is True
        spans = [s for s in exporter.spans if s.name == "livekit.session.start"]
        assert len(spans) == 1
        span = spans[0]
        assert span.span_type == SpanType.AGENT_STEP
        assert span.attributes["agent.framework"] == "livekit"
        assert span.attributes["livekit.capture_run"] is True
        assert span.attributes["livekit.agent.label"] == "PhoneAgent"
        assert span.status == SpanStatus.OK

    def test_start_error_creates_error_span(
        self, _mock_livekit: Any, exporter: InMemoryExporter
    ) -> None:
        livekit_patch.patch()
        session = FakeAgentSession()
        session.should_error_start = True

        with pytest.raises(RuntimeError, match="LiveKit start failed"):
            asyncio.run(session.start(FakeAgent()))

        error_spans = [s for s in exporter.spans if s.name == "livekit.session.start"]
        assert len(error_spans) == 1
        assert error_spans[0].status == SpanStatus.ERROR
        assert "LiveKit start failed" in (error_spans[0].error_message or "")

    def test_run_creates_span_with_input(
        self, _mock_livekit: Any, exporter: InMemoryExporter
    ) -> None:
        livekit_patch.patch()
        session = FakeAgentSession()

        session.run(user_input="hello there", input_modality="audio")

        spans = [s for s in exporter.spans if s.name == "livekit.session.run"]
        assert len(spans) == 1
        span = spans[0]
        assert span.attributes["agent.input"] == "hello there"
        assert span.attributes["livekit.input_modality"] == "audio"
        assert span.status == SpanStatus.OK

    def test_say_creates_span_with_output(
        self, _mock_livekit: Any, exporter: InMemoryExporter
    ) -> None:
        livekit_patch.patch()
        session = FakeAgentSession()

        session.say("Let me check that for you.", allow_interruptions=True)

        spans = [s for s in exporter.spans if s.name == "livekit.session.say"]
        assert len(spans) == 1
        span = spans[0]
        assert span.attributes["agent.output"] == "Let me check that for you."
        assert span.attributes["livekit.allow_interruptions"] is True

    def test_generate_reply_creates_span(
        self, _mock_livekit: Any, exporter: InMemoryExporter
    ) -> None:
        livekit_patch.patch()
        session = FakeAgentSession()

        session.generate_reply(
            user_input="book a table",
            instructions="Use the booking tool",
            tool_choice="auto",
            input_modality="text",
        )

        spans = [
            s for s in exporter.spans if s.name == "livekit.session.generate_reply"
        ]
        assert len(spans) == 1
        span = spans[0]
        assert span.attributes["agent.input"] == "book a table"
        assert span.attributes["livekit.instructions"] == "Use the booking tool"
        assert span.attributes["llm.tool_choice"] == "auto"
        assert span.attributes["livekit.input_modality"] == "text"

    def test_interrupt_creates_span(
        self, _mock_livekit: Any, exporter: InMemoryExporter
    ) -> None:
        livekit_patch.patch()
        session = FakeAgentSession()

        session.interrupt(force=True)

        spans = [s for s in exporter.spans if s.name == "livekit.session.interrupt"]
        assert len(spans) == 1
        span = spans[0]
        assert span.attributes["livekit.force"] is True
        assert span.status == SpanStatus.OK

    def test_without_tracer_calls_original(
        self, _mock_livekit: Any, exporter: InMemoryExporter
    ) -> None:
        livekit_patch.patch()
        beacon_sdk._tracer = None
        session = FakeAgentSession()
        result = session.say("hello")

        assert result.text == "hello"
        assert len(exporter.spans) == 0


class TestEventInstrumentation:
    def test_user_input_transcribed_event_creates_span(
        self, _mock_livekit: Any, exporter: InMemoryExporter
    ) -> None:
        livekit_patch.patch()
        session = FakeAgentSession()
        event = SimpleNamespace(
            transcript="I need a taxi", is_final=True, speaker_id="user-1"
        )

        session.emit("user_input_transcribed", event)

        spans = [
            s
            for s in exporter.spans
            if s.name == "livekit.event.user_input_transcribed"
        ]
        assert len(spans) == 1
        span = spans[0]
        assert span.span_type == SpanType.AGENT_STEP
        assert span.attributes["agent.input"] == "I need a taxi"
        assert span.attributes["livekit.transcript.is_final"] is True
        assert span.attributes["livekit.speaker_id"] == "user-1"

    def test_function_tools_event_creates_tool_use_span(
        self, _mock_livekit: Any, exporter: InMemoryExporter
    ) -> None:
        livekit_patch.patch()
        session = FakeAgentSession()
        event = SimpleNamespace(function_calls=[FakeFunctionCall("lookup_weather")])

        session.emit("function_tools_executed", event)

        spans = [
            s
            for s in exporter.spans
            if s.name == "livekit.event.function_tools_executed"
        ]
        assert len(spans) == 1
        span = spans[0]
        assert span.span_type == SpanType.TOOL_USE
        assert span.attributes["tool.name"] == "lookup_weather"
        assert span.attributes["livekit.tool_call_count"] == 1

    def test_speech_created_event_creates_agent_step_span(
        self, _mock_livekit: Any, exporter: InMemoryExporter
    ) -> None:
        livekit_patch.patch()
        session = FakeAgentSession()
        event = SimpleNamespace(source="agent", user_initiated=False)

        session.emit("speech_created", event)

        spans = [s for s in exporter.spans if s.name == "livekit.event.speech_created"]
        assert len(spans) == 1
        span = spans[0]
        assert span.span_type == SpanType.AGENT_STEP
        assert span.attributes["livekit.speech.source"] == "agent"
        assert span.attributes["livekit.speech.user_initiated"] is False

    def test_error_event_creates_error_span(
        self, _mock_livekit: Any, exporter: InMemoryExporter
    ) -> None:
        livekit_patch.patch()
        session = FakeAgentSession()
        event = SimpleNamespace(
            error=RuntimeError("voice backend down"), source=object()
        )

        session.emit("error", event)

        spans = [s for s in exporter.spans if s.name == "livekit.event.error"]
        assert len(spans) == 1
        span = spans[0]
        assert span.status == SpanStatus.ERROR
        assert "voice backend down" in (span.error_message or "")

    def test_close_event_with_error_reason_creates_error_span(
        self, _mock_livekit: Any, exporter: InMemoryExporter
    ) -> None:
        livekit_patch.patch()
        session = FakeAgentSession()
        event = SimpleNamespace(
            reason=SimpleNamespace(value="error"),
            error=RuntimeError("session closed unexpectedly"),
        )

        session.emit("close", event)

        spans = [s for s in exporter.spans if s.name == "livekit.event.close"]
        assert len(spans) == 1
        span = spans[0]
        assert span.status == SpanStatus.ERROR
        assert span.attributes["livekit.close.reason"] == "error"
        assert "session closed unexpectedly" in (span.error_message or "")
