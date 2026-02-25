"""Tests for the AutoGen auto-instrumentation integration."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch as mock_patch

import pytest

import beacon_sdk
from beacon_sdk.integrations import autogen as autogen_patch
from beacon_sdk.models import SpanStatus, SpanType
from tests.conftest import InMemoryExporter


@pytest.fixture(autouse=True)
def _setup_tracer(tracer: Any, exporter: InMemoryExporter) -> Any:
    beacon_sdk._tracer = tracer  # type: ignore[assignment]
    yield
    beacon_sdk._tracer = None
    from beacon_sdk.context import _trace_context

    _trace_context.set(None)


# ---------------------------------------------------------------------------
# Fake AutoGen classes
# ---------------------------------------------------------------------------


class FakeConversableAgent:
    def __init__(
        self,
        name: str = "assistant",
        should_error: bool = False,
    ) -> None:
        self.name = name
        self.should_error = should_error

    def generate_reply(
        self,
        messages: Any = None,
        sender: Any = None,
        **kwargs: Any,
    ) -> str | None:
        if self.should_error:
            raise RuntimeError("Agent failed to generate reply")
        return "I can help with that."

    async def a_generate_reply(
        self,
        messages: Any = None,
        sender: Any = None,
        **kwargs: Any,
    ) -> str | None:
        if self.should_error:
            raise RuntimeError("Agent failed to generate reply")
        return "Async reply here."


class FakeGroupChat:
    def __init__(
        self,
        agents: list[Any] | None = None,
        max_round: int = 10,
        should_error: bool = False,
    ) -> None:
        self.agents = agents or []
        self.max_round = max_round
        self.should_error = should_error

    def run(self, *args: Any, **kwargs: Any) -> str:
        if self.should_error:
            raise RuntimeError("GroupChat run failed")
        return "Chat completed successfully"

    async def a_run(self, *args: Any, **kwargs: Any) -> str:
        if self.should_error:
            raise RuntimeError("GroupChat async run failed")
        return "Async chat completed"


@pytest.fixture()
def _mock_autogen() -> Any:
    autogen_mod = SimpleNamespace(
        ConversableAgent=FakeConversableAgent,
        GroupChat=FakeGroupChat,
    )
    with mock_patch.dict("sys.modules", {"autogen": autogen_mod}):
        autogen_patch._patched = False
        autogen_patch._original_generate_reply = None
        autogen_patch._original_a_generate_reply = None
        autogen_patch._original_run_chat = None
        autogen_patch._original_a_run_chat = None
        yield autogen_mod
        autogen_patch.unpatch()
        autogen_patch._patched = False


# ---------------------------------------------------------------------------
# Patch / unpatch mechanics
# ---------------------------------------------------------------------------


class TestPatchMechanics:
    def test_patch_is_idempotent(self, _mock_autogen: Any) -> None:
        autogen_patch.patch()
        first_fn = FakeConversableAgent.generate_reply
        autogen_patch.patch()
        assert FakeConversableAgent.generate_reply is first_fn

    def test_unpatch_restores_original(self, _mock_autogen: Any) -> None:
        original = FakeConversableAgent.generate_reply
        autogen_patch.patch()
        assert FakeConversableAgent.generate_reply is not original
        autogen_patch.unpatch()
        assert FakeConversableAgent.generate_reply is original

    def test_patch_skips_when_not_installed(self) -> None:
        autogen_patch._patched = False
        with mock_patch.dict("sys.modules", {}, clear=False):
            import sys

            sys.modules.pop("autogen", None)
            autogen_patch.patch()
            assert autogen_patch._patched is False


# ---------------------------------------------------------------------------
# ConversableAgent.generate_reply spans
# ---------------------------------------------------------------------------


class TestGenerateReply:
    def test_creates_agent_step_span(
        self, _mock_autogen: Any, exporter: InMemoryExporter
    ) -> None:
        autogen_patch.patch()
        agent = FakeConversableAgent(name="researcher")
        result = agent.generate_reply(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert result == "I can help with that."
        spans = [s for s in exporter.spans if s.name.startswith("agent.generate_reply")]
        assert len(spans) == 1
        span = spans[0]
        assert span.span_type == SpanType.AGENT_STEP
        assert span.attributes["agent.framework"] == "autogen"
        assert span.attributes["agent.step_name"] == "researcher"
        assert span.status == SpanStatus.OK
        assert span.attributes["agent.output"] == "I can help with that."

    def test_records_sender(
        self, _mock_autogen: Any, exporter: InMemoryExporter
    ) -> None:
        autogen_patch.patch()
        agent = FakeConversableAgent(name="assistant")
        sender = FakeConversableAgent(name="user_proxy")
        agent.generate_reply(
            messages=[{"role": "user", "content": "Hi"}],
            sender=sender,
        )

        span = next(s for s in exporter.spans if s.name.startswith("agent.generate_reply"))
        assert span.attributes["autogen.sender"] == "user_proxy"

    def test_records_input_message(
        self, _mock_autogen: Any, exporter: InMemoryExporter
    ) -> None:
        autogen_patch.patch()
        agent = FakeConversableAgent(name="assistant")
        messages = [{"role": "user", "content": "What is AI?"}]
        agent.generate_reply(messages=messages)

        span = next(s for s in exporter.spans if s.name.startswith("agent.generate_reply"))
        parsed = json.loads(span.attributes["agent.input"])
        assert parsed["content"] == "What is AI?"

    def test_error_creates_error_span(
        self, _mock_autogen: Any, exporter: InMemoryExporter
    ) -> None:
        autogen_patch.patch()
        agent = FakeConversableAgent(name="broken", should_error=True)

        with pytest.raises(RuntimeError, match="Agent failed to generate reply"):
            agent.generate_reply()

        error_spans = [
            s
            for s in exporter.spans
            if s.name.startswith("agent.generate_reply") and s.status == SpanStatus.ERROR
        ]
        assert len(error_spans) == 1
        assert "Agent failed to generate reply" in (error_spans[0].error_message or "")

    def test_without_tracer_calls_original(
        self, _mock_autogen: Any, exporter: InMemoryExporter
    ) -> None:
        autogen_patch.patch()
        beacon_sdk._tracer = None
        agent = FakeConversableAgent(name="assistant")
        result = agent.generate_reply()
        assert result == "I can help with that."
        assert len(exporter.spans) == 0


# ---------------------------------------------------------------------------
# GroupChat.run spans
# ---------------------------------------------------------------------------


class TestGroupChat:
    def test_run_creates_agent_step_span(
        self, _mock_autogen: Any, exporter: InMemoryExporter
    ) -> None:
        autogen_patch.patch()
        agents = [
            FakeConversableAgent(name="alice"),
            FakeConversableAgent(name="bob"),
        ]
        chat = FakeGroupChat(agents=agents, max_round=5)
        result = chat.run()

        assert result == "Chat completed successfully"
        spans = [s for s in exporter.spans if s.name == "groupchat.run"]
        assert len(spans) == 1
        span = spans[0]
        assert span.span_type == SpanType.AGENT_STEP
        assert span.attributes["agent.framework"] == "autogen"
        assert span.attributes["autogen.num_agents"] == 2
        assert json.loads(span.attributes["autogen.agent_names"]) == ["alice", "bob"]
        assert span.attributes["autogen.max_round"] == 5
        assert span.status == SpanStatus.OK

    def test_run_error_creates_error_span(
        self, _mock_autogen: Any, exporter: InMemoryExporter
    ) -> None:
        autogen_patch.patch()
        chat = FakeGroupChat(should_error=True)

        with pytest.raises(RuntimeError, match="GroupChat run failed"):
            chat.run()

        error_spans = [
            s
            for s in exporter.spans
            if s.name == "groupchat.run" and s.status == SpanStatus.ERROR
        ]
        assert len(error_spans) == 1


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------


class TestAsync:
    def test_async_generate_reply_creates_span(
        self, _mock_autogen: Any, exporter: InMemoryExporter
    ) -> None:
        autogen_patch.patch()
        agent = FakeConversableAgent(name="async_agent")

        result = asyncio.run(agent.a_generate_reply(messages=[{"role": "user", "content": "Hi"}]))

        assert result == "Async reply here."
        spans = [s for s in exporter.spans if s.name.startswith("agent.generate_reply")]
        assert len(spans) == 1
        assert spans[0].attributes["agent.step_name"] == "async_agent"
        assert spans[0].status == SpanStatus.OK

    def test_async_run_creates_span(
        self, _mock_autogen: Any, exporter: InMemoryExporter
    ) -> None:
        autogen_patch.patch()
        agents = [FakeConversableAgent(name="agent1")]
        chat = FakeGroupChat(agents=agents)

        result = asyncio.run(chat.a_run())

        assert result == "Async chat completed"
        spans = [s for s in exporter.spans if s.name == "groupchat.run"]
        assert len(spans) == 1
        assert spans[0].status == SpanStatus.OK
