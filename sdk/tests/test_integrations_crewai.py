"""Tests for the CrewAI auto-instrumentation integration."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch as mock_patch

import pytest

import beacon_sdk
from beacon_sdk.integrations import crewai as crewai_patch
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
# Fake CrewAI classes
# ---------------------------------------------------------------------------


class FakeAgent:
    def __init__(
        self,
        role: str = "Researcher",
        step_callback: Any = None,
    ) -> None:
        self.role = role
        self.goal = f"Goal for {role}"
        self.backstory = f"Backstory for {role}"
        self.step_callback = step_callback


class FakeTask:
    def __init__(
        self,
        description: str = "Research task",
        agent: FakeAgent | None = None,
        callback: Any = None,
    ) -> None:
        self.description = description
        self.expected_output = "A report"
        self.agent = agent
        self.callback = callback


class FakeCrewOutput:
    def __init__(
        self,
        raw: str = "Final crew output",
        token_usage: dict[str, int] | None = None,
        tasks_output: list[Any] | None = None,
    ) -> None:
        self.raw = raw
        self.token_usage = token_usage or {
            "total_tokens": 100,
            "prompt_tokens": 80,
            "completion_tokens": 20,
        }
        self.tasks_output = tasks_output or [SimpleNamespace(raw="task1 output")]


class FakeCrew:
    def __init__(
        self,
        agents: list[Any] | None = None,
        tasks: list[Any] | None = None,
        process: str = "sequential",
        name: str = "TestCrew",
        should_error: bool = False,
    ) -> None:
        self.agents = agents or []
        self.tasks = tasks or []
        self.process = process
        self.name = name
        self.should_error = should_error

    def kickoff(
        self, inputs: dict[str, Any] | None = None, **kwargs: Any
    ) -> FakeCrewOutput:
        if self.should_error:
            raise RuntimeError("Crew execution failed")
        # Simulate: fire task callbacks
        for task in self.tasks:
            cb = getattr(task, "callback", None)
            if cb:
                cb(SimpleNamespace(raw="task output", summary="task summary"))
        # Simulate: fire agent step callbacks
        for agent in self.agents:
            cb = getattr(agent, "step_callback", None)
            if cb:
                cb(
                    SimpleNamespace(
                        log="I need to research AI",
                        tool="web_search",
                        tool_input="AI agents 2025",
                        return_values=None,
                    )
                )
        return FakeCrewOutput()

    async def kickoff_async(
        self, inputs: dict[str, Any] | None = None, **kwargs: Any
    ) -> FakeCrewOutput:
        if self.should_error:
            raise RuntimeError("Crew execution failed")
        return FakeCrewOutput()


@pytest.fixture()
def _mock_crewai() -> Any:
    crewai_mod = SimpleNamespace(Crew=FakeCrew)
    with mock_patch.dict("sys.modules", {"crewai": crewai_mod}):
        crewai_patch._patched = False
        crewai_patch._original_kickoff = None
        crewai_patch._original_kickoff_async = None
        yield crewai_mod
        crewai_patch.unpatch()
        crewai_patch._patched = False


# ---------------------------------------------------------------------------
# Patch / unpatch mechanics
# ---------------------------------------------------------------------------


class TestPatchMechanics:
    def test_patch_is_idempotent(self, _mock_crewai: Any) -> None:
        crewai_patch.patch()
        first_kickoff = FakeCrew.kickoff
        crewai_patch.patch()
        assert FakeCrew.kickoff is first_kickoff

    def test_unpatch_restores_original(self, _mock_crewai: Any) -> None:
        original = FakeCrew.kickoff
        crewai_patch.patch()
        assert FakeCrew.kickoff is not original
        crewai_patch.unpatch()
        assert FakeCrew.kickoff is original

    def test_patch_skips_when_not_installed(self) -> None:
        crewai_patch._patched = False
        with mock_patch.dict("sys.modules", {}, clear=False):
            import sys

            sys.modules.pop("crewai", None)
            crewai_patch.patch()
            assert crewai_patch._patched is False


# ---------------------------------------------------------------------------
# Root span creation
# ---------------------------------------------------------------------------


class TestRootSpan:
    def test_kickoff_creates_root_span(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        crew = FakeCrew(name="MyCrew")
        crew.kickoff(inputs={"topic": "AI"})

        root_spans = [
            s for s in exporter.spans if s.name == "crew.kickoff"
        ]
        assert len(root_spans) == 1
        span = root_spans[0]
        assert span.span_type == SpanType.AGENT_STEP
        assert span.attributes["agent.framework"] == "crewai"
        assert span.attributes["agent.step_name"] == "MyCrew"
        assert span.status == SpanStatus.OK

    def test_kickoff_records_input_attributes(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        agent = FakeAgent(role="Researcher")
        task = FakeTask(description="Research AI", agent=agent)
        crew = FakeCrew(
            agents=[agent], tasks=[task], process="hierarchical", name="TestCrew"
        )
        crew.kickoff(inputs={"topic": "AI"})

        span = next(s for s in exporter.spans if s.name == "crew.kickoff")
        assert json.loads(span.attributes["agent.input"]) == {"topic": "AI"}
        assert span.attributes["crewai.process"] == "hierarchical"
        assert span.attributes["crewai.num_agents"] == 1
        assert span.attributes["crewai.num_tasks"] == 1

    def test_kickoff_records_output(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        crew = FakeCrew()
        crew.kickoff()

        span = next(s for s in exporter.spans if s.name == "crew.kickoff")
        assert span.attributes["agent.output"] == "Final crew output"
        assert span.attributes["llm.tokens.total"] == 100
        assert span.attributes["llm.tokens.input"] == 80
        assert span.attributes["llm.tokens.output"] == 20
        assert span.attributes["crewai.tasks_completed"] == 1

    def test_kickoff_error_creates_error_span(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        crew = FakeCrew(should_error=True)

        with pytest.raises(RuntimeError, match="Crew execution failed"):
            crew.kickoff()

        error_spans = [
            s
            for s in exporter.spans
            if s.name == "crew.kickoff" and s.status == SpanStatus.ERROR
        ]
        assert len(error_spans) == 1
        assert "Crew execution failed" in (error_spans[0].error_message or "")

    def test_kickoff_without_tracer_calls_original(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        beacon_sdk._tracer = None
        crew = FakeCrew()
        result = crew.kickoff(inputs={"topic": "AI"})
        assert result.raw == "Final crew output"
        assert len(exporter.spans) == 0


# ---------------------------------------------------------------------------
# Task callback spans
# ---------------------------------------------------------------------------


class TestTaskCallbacks:
    def test_task_callback_creates_chain_span(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        agent = FakeAgent(role="Writer")
        task = FakeTask(description="Write a blog post about AI", agent=agent)
        crew = FakeCrew(agents=[agent], tasks=[task])
        crew.kickoff()

        task_spans = [s for s in exporter.spans if s.span_type == SpanType.CHAIN]
        assert len(task_spans) == 1
        span = task_spans[0]
        assert span.name == "Task: Write a blog post about AI"
        assert span.attributes["agent.framework"] == "crewai"
        assert span.attributes["chain.type"] == "crewai_task"
        assert span.attributes["chain.output"] == "task output"
        assert span.attributes["crewai.agent_role"] == "Writer"
        assert span.attributes["crewai.task_summary"] == "task summary"

    def test_multiple_tasks_create_multiple_spans(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        a1 = FakeAgent(role="Researcher")
        a2 = FakeAgent(role="Writer")
        t1 = FakeTask(description="Research AI", agent=a1)
        t2 = FakeTask(description="Write report", agent=a2)
        crew = FakeCrew(agents=[a1, a2], tasks=[t1, t2])
        crew.kickoff()

        task_spans = [s for s in exporter.spans if s.span_type == SpanType.CHAIN]
        assert len(task_spans) == 2

        root_spans = [s for s in exporter.spans if s.name == "crew.kickoff"]
        assert len(root_spans) == 1

    def test_task_without_agent(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        task = FakeTask(description="Standalone task", agent=None)
        crew = FakeCrew(tasks=[task])
        crew.kickoff()

        task_spans = [s for s in exporter.spans if s.span_type == SpanType.CHAIN]
        assert len(task_spans) == 1
        assert "crewai.agent_role" not in task_spans[0].attributes


# ---------------------------------------------------------------------------
# Agent step callback spans
# ---------------------------------------------------------------------------


class TestAgentStepCallbacks:
    def test_step_callback_creates_agent_step_span(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        agent = FakeAgent(role="Researcher")
        crew = FakeCrew(agents=[agent])
        crew.kickoff()

        step_spans = [
            s
            for s in exporter.spans
            if s.span_type == SpanType.AGENT_STEP and s.name.startswith("Step:")
        ]
        assert len(step_spans) == 1
        span = step_spans[0]
        assert span.name == "Step: Researcher"
        assert span.attributes["agent.framework"] == "crewai"
        assert span.attributes["agent.thought"] == "I need to research AI"

    def test_step_callback_records_tool_info(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        agent = FakeAgent(role="Researcher")
        crew = FakeCrew(agents=[agent])
        crew.kickoff()

        step_spans = [
            s
            for s in exporter.spans
            if s.span_type == SpanType.AGENT_STEP and s.name.startswith("Step:")
        ]
        assert len(step_spans) == 1
        assert step_spans[0].attributes["tool.name"] == "web_search"
        assert step_spans[0].attributes["tool.input"] == '"AI agents 2025"'


# ---------------------------------------------------------------------------
# User callback preservation
# ---------------------------------------------------------------------------


class TestCallbackPreservation:
    def test_user_step_callback_is_preserved(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        calls: list[Any] = []
        agent = FakeAgent(role="Researcher", step_callback=lambda x: calls.append(x))
        crew = FakeCrew(agents=[agent])
        crew.kickoff()

        assert len(calls) == 1

    def test_user_task_callback_is_preserved(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        calls: list[Any] = []
        agent = FakeAgent(role="Writer")
        task = FakeTask(
            description="Write", agent=agent, callback=lambda x: calls.append(x)
        )
        crew = FakeCrew(agents=[agent], tasks=[task])
        crew.kickoff()

        assert len(calls) == 1

    def test_callbacks_restored_after_kickoff(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        original_step_cb = lambda x: None  # noqa: E731
        original_task_cb = lambda x: None  # noqa: E731
        agent = FakeAgent(role="Researcher", step_callback=original_step_cb)
        task = FakeTask(description="Research", agent=agent, callback=original_task_cb)
        crew = FakeCrew(agents=[agent], tasks=[task])
        crew.kickoff()

        assert agent.step_callback is original_step_cb
        assert task.callback is original_task_cb

    def test_callbacks_restored_on_error(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        original_step_cb = lambda x: None  # noqa: E731
        agent = FakeAgent(role="Researcher", step_callback=original_step_cb)
        crew = FakeCrew(agents=[agent], should_error=True)

        with pytest.raises(RuntimeError):
            crew.kickoff()

        assert agent.step_callback is original_step_cb


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------


class TestAsync:
    def test_kickoff_async_creates_root_span(
        self, _mock_crewai: Any, exporter: InMemoryExporter
    ) -> None:
        crewai_patch.patch()
        crew = FakeCrew(name="AsyncCrew")

        asyncio.run(crew.kickoff_async(inputs={"topic": "AI"}))

        root_spans = [s for s in exporter.spans if s.name == "crew.kickoff"]
        assert len(root_spans) == 1
        assert root_spans[0].attributes["agent.step_name"] == "AsyncCrew"
        assert root_spans[0].status == SpanStatus.OK
