"""LangChain integration for Beacon SDK.

Provides BeaconCallbackHandler that auto-instruments LangChain agents,
capturing chain, LLM, tool, and agent events as Beacon spans.

Usage:
    from beacon_sdk.integrations.langchain import BeaconCallbackHandler

    handler = BeaconCallbackHandler()
    agent.invoke({"input": "..."}, config={"callbacks": [handler]})
"""

from __future__ import annotations

import json
import logging
from contextvars import Token
from typing import Any
from uuid import UUID

from beacon_sdk import get_tracer
from beacon_sdk.context import TraceContext
from beacon_sdk.models import Span, SpanStatus, SpanType

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:

    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Stub for when langchain_core is not installed."""


logger = logging.getLogger(__name__)


class BeaconCallbackHandler(BaseCallbackHandler):  # type: ignore[misc]
    """LangChain callback handler that creates Beacon spans for each event.

    Parent-child relationships are maintained automatically via the tracer's
    context system — LangChain fires callbacks in nested order, so the
    contextvars-based span nesting works correctly.
    """

    def __init__(self) -> None:
        super().__init__()
        self._tracer = get_tracer()
        # Maps LangChain run_id (str) -> (Span, context Token)
        self._run_to_span: dict[str, tuple[Span, Token[TraceContext | None]]] = {}

    # --- Chain callbacks ---

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            name = serialized.get("name") or serialized.get("id", ["chain"])[-1]
            span, token = self._tracer.start_span(
                name=str(name),
                span_type=SpanType.CHAIN,
                attributes={
                    "chain.type": str(name),
                    "chain.input": json.dumps(inputs, default=str)[:50000],
                },
            )
            self._run_to_span[str(run_id)] = (span, token)
        except Exception:
            logger.debug(
                "BeaconCallbackHandler: error in on_chain_start", exc_info=True
            )

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        try:
            entry = self._run_to_span.pop(str(run_id), None)
            if entry is not None:
                span, token = entry
                span.set_attribute(
                    "chain.output", json.dumps(outputs, default=str)[:50000]
                )
                self._tracer.end_span(span, token, status=SpanStatus.OK)
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_chain_end", exc_info=True)

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        try:
            entry = self._run_to_span.pop(str(run_id), None)
            if entry is not None:
                span, token = entry
                self._tracer.end_span(
                    span, token, status=SpanStatus.ERROR, error_message=str(error)
                )
        except Exception:
            logger.debug(
                "BeaconCallbackHandler: error in on_chain_error", exc_info=True
            )

    # --- LLM callbacks ---

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            invocation_params = kwargs.get("invocation_params", {})
            model = invocation_params.get("model_name") or invocation_params.get(
                "model", serialized.get("name", "unknown")
            )
            span, token = self._tracer.start_span(
                name=str(model),
                span_type=SpanType.LLM_CALL,
                attributes={
                    "llm.provider": (
                        serialized.get("id", ["unknown"])[0]
                        if serialized.get("id")
                        else "unknown"
                    ),
                    "llm.model": str(model),
                    "llm.prompt": json.dumps(prompts, default=str)[:50000],
                },
            )
            self._run_to_span[str(run_id)] = (span, token)
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_llm_start", exc_info=True)

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        try:
            entry = self._run_to_span.pop(str(run_id), None)
            if entry is None:
                return

            span, token = entry

            # Extract completion text
            if (
                hasattr(response, "generations")
                and response.generations
                and response.generations[0]
            ):
                gen = response.generations[0][0]
                span.set_attribute("llm.completion", gen.text[:50000])

                # Extract finish reason from generation_info
                generation_info = getattr(gen, "generation_info", None) or {}
                finish_reason = generation_info.get("finish_reason")
                if finish_reason:
                    span.set_attribute("llm.finish_reason", finish_reason)

            # Extract token usage
            llm_output = getattr(response, "llm_output", None) or {}
            token_usage = llm_output.get("token_usage", {})
            if token_usage:
                span.set_attribute(
                    "llm.tokens.input", token_usage.get("prompt_tokens", 0)
                )
                span.set_attribute(
                    "llm.tokens.output", token_usage.get("completion_tokens", 0)
                )
                span.set_attribute(
                    "llm.tokens.total", token_usage.get("total_tokens", 0)
                )

            self._tracer.end_span(span, token, status=SpanStatus.OK)
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_llm_end", exc_info=True)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        try:
            entry = self._run_to_span.pop(str(run_id), None)
            if entry is not None:
                span, token = entry
                self._tracer.end_span(
                    span, token, status=SpanStatus.ERROR, error_message=str(error)
                )
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_llm_error", exc_info=True)

    # --- Tool callbacks ---

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            tool_name = serialized.get("name", "unknown_tool")
            span, token = self._tracer.start_span(
                name=str(tool_name),
                span_type=SpanType.TOOL_USE,
                attributes={
                    "tool.name": str(tool_name),
                    "tool.input": input_str[:50000],
                    "tool.framework": "langchain",
                },
            )
            self._run_to_span[str(run_id)] = (span, token)
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_tool_start", exc_info=True)

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        try:
            entry = self._run_to_span.pop(str(run_id), None)
            if entry is not None:
                span, token = entry
                span.set_attribute("tool.output", str(output)[:50000])
                self._tracer.end_span(span, token, status=SpanStatus.OK)
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_tool_end", exc_info=True)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        try:
            entry = self._run_to_span.pop(str(run_id), None)
            if entry is not None:
                span, token = entry
                self._tracer.end_span(
                    span, token, status=SpanStatus.ERROR, error_message=str(error)
                )
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_tool_error", exc_info=True)

    # --- Agent callbacks ---

    def on_agent_action(
        self,
        action: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            span, token = self._tracer.start_span(
                name=f"Action: {action.tool}",
                span_type=SpanType.AGENT_STEP,
                attributes={
                    "agent.framework": "langchain",
                    "agent.step_name": action.tool,
                    "agent.input": json.dumps(action.tool_input, default=str)[:50000],
                    "agent.thought": action.log[:50000] if action.log else "",
                },
            )
            self._run_to_span[str(run_id)] = (span, token)
        except Exception:
            logger.debug(
                "BeaconCallbackHandler: error in on_agent_action", exc_info=True
            )

    def on_agent_finish(
        self,
        finish: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        try:
            entry = self._run_to_span.pop(str(run_id), None)
            if entry is not None:
                span, token = entry
                span.set_attribute(
                    "agent.output",
                    json.dumps(finish.return_values, default=str)[:50000],
                )
                self._tracer.end_span(span, token, status=SpanStatus.OK)
        except Exception:
            logger.debug(
                "BeaconCallbackHandler: error in on_agent_finish", exc_info=True
            )
