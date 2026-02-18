"""Tests for the LangChain callback handler integration."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

import beacon_sdk
from beacon_sdk.integrations.langchain import BeaconCallbackHandler
from beacon_sdk.models import SpanStatus, SpanType
from tests.conftest import InMemoryExporter


@pytest.fixture(autouse=True)
def _setup_tracer(tracer: Any, exporter: InMemoryExporter) -> Any:
    beacon_sdk._tracer = tracer  # type: ignore[assignment]
    yield
    beacon_sdk._tracer = None
    # Reset context to prevent leaks from tests that only call on_*_start
    from beacon_sdk.context import _trace_context

    _trace_context.set(None)


def _make_handler() -> BeaconCallbackHandler:
    """Create a fresh handler backed by the global test tracer."""
    return BeaconCallbackHandler()


def _make_llm_result(
    text: str = "Hello!",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    total_tokens: int = 15,
    finish_reason: str | None = "stop",
) -> SimpleNamespace:
    """Mock LangChain LLMResult."""
    generation_info: dict[str, Any] = {}
    if finish_reason is not None:
        generation_info["finish_reason"] = finish_reason
    return SimpleNamespace(
        generations=[
            [SimpleNamespace(text=text, generation_info=generation_info)]
        ],
        llm_output={
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }
        },
    )


def _make_agent_action(
    tool: str = "search",
    tool_input: str | dict[str, Any] = "query",
    log: str = "Thinking...",
) -> SimpleNamespace:
    """Mock LangChain AgentAction."""
    return SimpleNamespace(tool=tool, tool_input=tool_input, log=log)


def _make_agent_finish(
    return_values: dict[str, Any] | None = None,
) -> SimpleNamespace:
    """Mock LangChain AgentFinish."""
    return SimpleNamespace(return_values=return_values or {"output": "Done"})


# ---------------------------------------------------------------------------
# Chain callbacks
# ---------------------------------------------------------------------------


def test_chain_start_creates_chain_span(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    handler.on_chain_start(
        serialized={"name": "RunnableSequence"},
        inputs={"input": "hello"},
        run_id=run_id,
    )
    # Span created but not yet ended — still in _run_to_span
    assert str(run_id) in handler._run_to_span
    span, _token = handler._run_to_span[str(run_id)]
    assert span.span_type == SpanType.CHAIN
    assert span.name == "RunnableSequence"
    assert span.attributes["chain.type"] == "RunnableSequence"
    assert json.loads(span.attributes["chain.input"]) == {"input": "hello"}


def test_chain_end_completes_span_with_output(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    handler.on_chain_start(
        serialized={"name": "MyChain"},
        inputs={"input": "hi"},
        run_id=run_id,
    )
    handler.on_chain_end(outputs={"result": "bye"}, run_id=run_id)

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.OK
    assert json.loads(span.attributes["chain.output"]) == {"result": "bye"}


def test_chain_error_marks_span_as_error(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    handler.on_chain_start(
        serialized={"name": "FailChain"},
        inputs={},
        run_id=run_id,
    )
    handler.on_chain_error(error=ValueError("boom"), run_id=run_id)

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.error_message == "boom"


def test_chain_start_falls_back_to_id_list(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    handler.on_chain_start(
        serialized={"id": ["langchain", "chains", "LLMChain"]},
        inputs={},
        run_id=run_id,
    )
    span, _ = handler._run_to_span[str(run_id)]
    assert span.name == "LLMChain"


# ---------------------------------------------------------------------------
# LLM callbacks
# ---------------------------------------------------------------------------


def test_llm_start_creates_llm_call_span(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    handler.on_llm_start(
        serialized={"id": ["openai", "ChatOpenAI"], "name": "ChatOpenAI"},
        prompts=["What is 2+2?"],
        run_id=run_id,
        invocation_params={"model_name": "gpt-4o"},
    )
    span, _ = handler._run_to_span[str(run_id)]
    assert span.span_type == SpanType.LLM_CALL
    assert span.name == "gpt-4o"
    assert span.attributes["llm.provider"] == "openai"
    assert span.attributes["llm.model"] == "gpt-4o"
    assert json.loads(span.attributes["llm.prompt"]) == ["What is 2+2?"]


def test_llm_end_records_completion_and_tokens(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    handler.on_llm_start(
        serialized={"id": ["openai"], "name": "ChatOpenAI"},
        prompts=["Hi"],
        run_id=run_id,
        invocation_params={"model_name": "gpt-4o"},
    )
    handler.on_llm_end(
        response=_make_llm_result(
            text="4",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
        run_id=run_id,
    )

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.OK
    assert span.attributes["llm.completion"] == "4"
    assert span.attributes["llm.tokens.input"] == 10
    assert span.attributes["llm.tokens.output"] == 5
    assert span.attributes["llm.tokens.total"] == 15


def test_llm_end_records_finish_reason(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    handler.on_llm_start(
        serialized={"id": ["openai"], "name": "ChatOpenAI"},
        prompts=["Hi"],
        run_id=run_id,
        invocation_params={"model_name": "gpt-4o"},
    )
    handler.on_llm_end(
        response=_make_llm_result(finish_reason="stop"),
        run_id=run_id,
    )

    span = exporter.spans[0]
    assert span.attributes["llm.finish_reason"] == "stop"


def test_llm_end_no_finish_reason_when_absent(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    handler.on_llm_start(
        serialized={"id": ["openai"], "name": "ChatOpenAI"},
        prompts=["Hi"],
        run_id=run_id,
        invocation_params={"model_name": "gpt-4o"},
    )
    handler.on_llm_end(
        response=_make_llm_result(finish_reason=None),
        run_id=run_id,
    )

    span = exporter.spans[0]
    assert "llm.finish_reason" not in span.attributes


def test_llm_error_marks_span_as_error(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    handler.on_llm_start(
        serialized={"id": ["openai"], "name": "ChatOpenAI"},
        prompts=["Hi"],
        run_id=run_id,
        invocation_params={"model_name": "gpt-4o"},
    )
    handler.on_llm_error(error=RuntimeError("rate limit"), run_id=run_id)

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.error_message == "rate limit"


# ---------------------------------------------------------------------------
# Tool callbacks
# ---------------------------------------------------------------------------


def test_tool_start_creates_tool_use_span(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    handler.on_tool_start(
        serialized={"name": "calculator"},
        input_str="2+2",
        run_id=run_id,
    )
    span, _ = handler._run_to_span[str(run_id)]
    assert span.span_type == SpanType.TOOL_USE
    assert span.attributes["tool.name"] == "calculator"
    assert span.attributes["tool.input"] == "2+2"
    assert span.attributes["tool.framework"] == "langchain"


def test_tool_end_records_output(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    handler.on_tool_start(
        serialized={"name": "calculator"},
        input_str="2+2",
        run_id=run_id,
    )
    handler.on_tool_end(output="4", run_id=run_id)

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.OK
    assert span.attributes["tool.output"] == "4"


def test_tool_error_marks_span_as_error(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    handler.on_tool_start(
        serialized={"name": "calculator"},
        input_str="bad input",
        run_id=run_id,
    )
    handler.on_tool_error(error=ValueError("parse error"), run_id=run_id)

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.ERROR
    assert span.error_message == "parse error"


# ---------------------------------------------------------------------------
# Agent callbacks
# ---------------------------------------------------------------------------


def test_agent_action_creates_agent_step_span(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    action = _make_agent_action(tool="search", tool_input="python docs", log="Let me search")
    handler.on_agent_action(action=action, run_id=run_id)

    span, _ = handler._run_to_span[str(run_id)]
    assert span.span_type == SpanType.AGENT_STEP
    assert span.name == "Action: search"
    assert span.attributes["agent.framework"] == "langchain"
    assert span.attributes["agent.step_name"] == "search"
    assert json.loads(span.attributes["agent.input"]) == "python docs"
    assert span.attributes["agent.thought"] == "Let me search"


def test_agent_finish_completes_span_with_output(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    run_id = uuid4()
    action = _make_agent_action()
    handler.on_agent_action(action=action, run_id=run_id)

    finish = _make_agent_finish(return_values={"output": "42"})
    handler.on_agent_finish(finish=finish, run_id=run_id)

    assert len(exporter.spans) == 1
    span = exporter.spans[0]
    assert span.status == SpanStatus.OK
    assert json.loads(span.attributes["agent.output"]) == {"output": "42"}


# ---------------------------------------------------------------------------
# Parent-child relationships
# ---------------------------------------------------------------------------


def test_nested_chain_llm_parent_child(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    chain_id = uuid4()
    llm_id = uuid4()

    handler.on_chain_start(
        serialized={"name": "AgentExecutor"},
        inputs={"input": "hello"},
        run_id=chain_id,
    )
    handler.on_llm_start(
        serialized={"id": ["openai"], "name": "ChatOpenAI"},
        prompts=["hello"],
        run_id=llm_id,
        parent_run_id=chain_id,
        invocation_params={"model_name": "gpt-4o"},
    )
    handler.on_llm_end(response=_make_llm_result(), run_id=llm_id)
    handler.on_chain_end(outputs={"result": "done"}, run_id=chain_id)

    assert len(exporter.spans) == 2
    llm_span = exporter.spans[0]
    chain_span = exporter.spans[1]

    assert llm_span.span_type == SpanType.LLM_CALL
    assert chain_span.span_type == SpanType.CHAIN
    assert llm_span.parent_span_id == chain_span.span_id
    assert llm_span.trace_id == chain_span.trace_id


def test_nested_chain_tool_parent_child(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    chain_id = uuid4()
    tool_id = uuid4()

    handler.on_chain_start(
        serialized={"name": "AgentExecutor"},
        inputs={"input": "calc 2+2"},
        run_id=chain_id,
    )
    handler.on_tool_start(
        serialized={"name": "calculator"},
        input_str="2+2",
        run_id=tool_id,
        parent_run_id=chain_id,
    )
    handler.on_tool_end(output="4", run_id=tool_id)
    handler.on_chain_end(outputs={"result": "4"}, run_id=chain_id)

    assert len(exporter.spans) == 2
    tool_span = exporter.spans[0]
    chain_span = exporter.spans[1]

    assert tool_span.parent_span_id == chain_span.span_id
    assert tool_span.trace_id == chain_span.trace_id


def test_deeply_nested_chain_tool_llm(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    chain_id = uuid4()
    tool_id = uuid4()
    llm_id = uuid4()

    handler.on_chain_start(
        serialized={"name": "AgentExecutor"},
        inputs={},
        run_id=chain_id,
    )
    handler.on_tool_start(
        serialized={"name": "search"},
        input_str="query",
        run_id=tool_id,
        parent_run_id=chain_id,
    )
    handler.on_llm_start(
        serialized={"id": ["openai"], "name": "ChatOpenAI"},
        prompts=["synthesize"],
        run_id=llm_id,
        parent_run_id=tool_id,
        invocation_params={"model_name": "gpt-4o"},
    )
    handler.on_llm_end(response=_make_llm_result(), run_id=llm_id)
    handler.on_tool_end(output="result", run_id=tool_id)
    handler.on_chain_end(outputs={}, run_id=chain_id)

    assert len(exporter.spans) == 3
    llm_span = exporter.spans[0]
    tool_span = exporter.spans[1]
    chain_span = exporter.spans[2]

    # chain -> tool -> llm
    assert chain_span.parent_span_id is None
    assert tool_span.parent_span_id == chain_span.span_id
    assert llm_span.parent_span_id == tool_span.span_id
    assert llm_span.trace_id == tool_span.trace_id == chain_span.trace_id


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_end_without_start_is_noop(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    handler.on_chain_end(outputs={"result": "orphan"}, run_id=uuid4())
    assert len(exporter.spans) == 0


def test_error_without_start_is_noop(exporter: InMemoryExporter) -> None:
    handler = _make_handler()
    handler.on_chain_error(error=RuntimeError("orphan"), run_id=uuid4())
    assert len(exporter.spans) == 0
