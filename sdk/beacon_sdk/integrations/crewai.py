"""CrewAI auto-instrumentation. Patches Crew.kickoff to create agent framework spans."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from beacon_sdk.models import SpanStatus, SpanType

logger = logging.getLogger("beacon_sdk")

_patched: bool = False
_original_kickoff: Any = None
_original_kickoff_async: Any = None


# ---------------------------------------------------------------------------
# Callback helpers
# ---------------------------------------------------------------------------


@dataclass
class _InjectedState:
    """Tracks original callbacks so we can restore them after kickoff."""

    agent_original_callbacks: dict[int, Any] = field(default_factory=dict)
    task_original_callbacks: dict[int, Any] = field(default_factory=dict)


def _make_agent_step_callback(
    agent_role: str,
    tracer: Any,
    original_callback: Any | None,
) -> Any:
    """Create a step_callback that records a span and chains to the original."""

    def callback(step_output: Any) -> None:
        try:
            thought = str(getattr(step_output, "log", "") or "")
            tool_name = getattr(step_output, "tool", None)
            tool_input = getattr(step_output, "tool_input", None)
            return_values = getattr(step_output, "return_values", None)

            attrs: dict[str, Any] = {
                "agent.framework": "crewai",
                "agent.step_name": agent_role,
                "agent.thought": thought[:50_000],
            }
            if tool_name is not None:
                attrs["tool.name"] = str(tool_name)
            if tool_input is not None:
                attrs["tool.input"] = json.dumps(tool_input, default=str)[:50_000]
            if return_values is not None:
                attrs["agent.output"] = json.dumps(return_values, default=str)[:50_000]

            span, token = tracer.start_span(
                name=f"Step: {agent_role}",
                span_type=SpanType.AGENT_STEP,
                attributes=attrs,
            )
            tracer.end_span(span, token, status=SpanStatus.OK)
        except Exception:
            logger.debug("Beacon: CrewAI step callback error", exc_info=True)

        if original_callback is not None:
            original_callback(step_output)

    return callback


def _make_task_callback(
    task_description: str,
    agent_role: str | None,
    tracer: Any,
    original_callback: Any | None,
) -> Any:
    """Create a task callback that records a CHAIN span on task completion."""

    def callback(task_output: Any) -> None:
        try:
            raw_output = str(getattr(task_output, "raw", "") or "")
            summary = getattr(task_output, "summary", None)

            attrs: dict[str, Any] = {
                "agent.framework": "crewai",
                "chain.type": "crewai_task",
                "chain.input": task_description[:50_000],
                "chain.output": raw_output[:50_000],
            }
            if agent_role:
                attrs["crewai.agent_role"] = agent_role
            if summary:
                attrs["crewai.task_summary"] = str(summary)[:50_000]

            span, token = tracer.start_span(
                name=f"Task: {task_description[:80]}",
                span_type=SpanType.CHAIN,
                attributes=attrs,
            )
            tracer.end_span(span, token, status=SpanStatus.OK)
        except Exception:
            logger.debug("Beacon: CrewAI task callback error", exc_info=True)

        if original_callback is not None:
            original_callback(task_output)

    return callback


def _inject_callbacks(crew: Any, tracer: Any) -> _InjectedState:
    """Inject Beacon callbacks into the crew's agents and tasks."""
    state = _InjectedState()

    for agent in getattr(crew, "agents", []):
        agent_id = id(agent)
        original_cb = getattr(agent, "step_callback", None)
        state.agent_original_callbacks[agent_id] = original_cb

        role = getattr(agent, "role", "unknown")
        agent.step_callback = _make_agent_step_callback(role, tracer, original_cb)

    for task in getattr(crew, "tasks", []):
        task_id = id(task)
        original_cb = getattr(task, "callback", None)
        state.task_original_callbacks[task_id] = original_cb

        description = getattr(task, "description", "unknown task")
        task_agent = getattr(task, "agent", None)
        agent_role = getattr(task_agent, "role", None) if task_agent else None

        task.callback = _make_task_callback(
            description, agent_role, tracer, original_cb
        )

    return state


def _restore_callbacks(crew: Any, state: _InjectedState) -> None:
    """Restore original callbacks after kickoff completes."""
    for agent in getattr(crew, "agents", []):
        agent_id = id(agent)
        if agent_id in state.agent_original_callbacks:
            agent.step_callback = state.agent_original_callbacks[agent_id]

    for task in getattr(crew, "tasks", []):
        task_id = id(task)
        if task_id in state.task_original_callbacks:
            task.callback = state.task_original_callbacks[task_id]


def _apply_result_attributes(span: Any, result: Any) -> None:
    """Extract attributes from a CrewOutput result."""
    if result is None:
        return

    raw = getattr(result, "raw", None)
    if raw is not None:
        span.set_attribute("agent.output", str(raw)[:50_000])

    token_usage = getattr(result, "token_usage", None)
    if isinstance(token_usage, dict):
        total = token_usage.get("total_tokens", 0)
        prompt = token_usage.get("prompt_tokens", 0)
        completion = token_usage.get("completion_tokens", 0)
        if total:
            span.set_attribute("llm.tokens.total", total)
        if prompt:
            span.set_attribute("llm.tokens.input", prompt)
        if completion:
            span.set_attribute("llm.tokens.output", completion)

    tasks_output = getattr(result, "tasks_output", None)
    if tasks_output:
        span.set_attribute("crewai.tasks_completed", len(tasks_output))


# ---------------------------------------------------------------------------
# Patched function factories
# ---------------------------------------------------------------------------


def _make_kickoff_wrapper(original: Any) -> Any:
    """Create a sync wrapper around Crew.kickoff."""

    def wrapper(self: Any, inputs: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return original(self, inputs=inputs, **kwargs)

        crew_name = getattr(self, "name", None) or "CrewAI"
        process_type = str(getattr(self, "process", "sequential"))

        span, token = tracer.start_span(
            name="crew.kickoff",
            span_type=SpanType.AGENT_STEP,
            attributes={
                "agent.framework": "crewai",
                "agent.step_name": crew_name,
                "agent.input": json.dumps(inputs or {}, default=str)[:50_000],
                "crewai.process": process_type,
                "crewai.num_agents": len(getattr(self, "agents", [])),
                "crewai.num_tasks": len(getattr(self, "tasks", [])),
            },
        )

        injected = _inject_callbacks(self, tracer)
        try:
            result = original(self, inputs=inputs, **kwargs)
            _apply_result_attributes(span, result)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise
        finally:
            _restore_callbacks(self, injected)

    return wrapper


def _make_async_kickoff_wrapper(original: Any) -> Any:
    """Create an async wrapper around Crew.kickoff_async."""

    async def wrapper(
        self: Any, inputs: dict[str, Any] | None = None, **kwargs: Any
    ) -> Any:
        from beacon_sdk import _get_tracer

        tracer = _get_tracer()
        if tracer is None:
            return await original(self, inputs=inputs, **kwargs)

        crew_name = getattr(self, "name", None) or "CrewAI"
        process_type = str(getattr(self, "process", "sequential"))

        span, token = tracer.start_span(
            name="crew.kickoff",
            span_type=SpanType.AGENT_STEP,
            attributes={
                "agent.framework": "crewai",
                "agent.step_name": crew_name,
                "agent.input": json.dumps(inputs or {}, default=str)[:50_000],
                "crewai.process": process_type,
                "crewai.num_agents": len(getattr(self, "agents", [])),
                "crewai.num_tasks": len(getattr(self, "tasks", [])),
            },
        )

        injected = _inject_callbacks(self, tracer)
        try:
            result = await original(self, inputs=inputs, **kwargs)
            _apply_result_attributes(span, result)
            tracer.end_span(span, token, status=SpanStatus.OK)
            return result
        except Exception as exc:
            tracer.end_span(
                span, token, status=SpanStatus.ERROR, error_message=str(exc)
            )
            raise
        finally:
            _restore_callbacks(self, injected)

    return wrapper


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def patch() -> None:
    """Monkey-patch the CrewAI Crew class to auto-instrument kickoff."""
    global _patched, _original_kickoff, _original_kickoff_async

    if _patched:
        return

    try:
        import crewai
    except ImportError:
        return

    _original_kickoff = crewai.Crew.kickoff
    crewai.Crew.kickoff = _make_kickoff_wrapper(_original_kickoff)

    if hasattr(crewai.Crew, "kickoff_async"):
        _original_kickoff_async = crewai.Crew.kickoff_async
        crewai.Crew.kickoff_async = _make_async_kickoff_wrapper(_original_kickoff_async)

    _patched = True
    logger.debug("Beacon: CrewAI auto-patch applied")


def unpatch() -> None:
    """Restore original CrewAI methods."""
    global _patched, _original_kickoff, _original_kickoff_async

    if not _patched:
        return

    try:
        import crewai
    except ImportError:
        return

    if _original_kickoff is not None:
        crewai.Crew.kickoff = _original_kickoff
    if _original_kickoff_async is not None and hasattr(crewai.Crew, "kickoff_async"):
        crewai.Crew.kickoff_async = _original_kickoff_async

    _original_kickoff = None
    _original_kickoff_async = None
    _patched = False
    logger.debug("Beacon: CrewAI auto-patch removed")
