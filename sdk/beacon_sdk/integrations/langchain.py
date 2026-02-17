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
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.outputs import LLMResult

from beacon_sdk import get_tracer

logger = logging.getLogger(__name__)


class BeaconCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that creates Beacon spans for each event.

    Maps LangChain's run_id/parent_run_id to Beacon span_id/parent_span_id,
    maintaining proper parent-child relationships in the trace graph.
    """

    def __init__(self) -> None:
        super().__init__()
        self._tracer = get_tracer()
        # Maps LangChain run_id -> beacon span_id
        self._run_to_span: dict[str, str] = {}

    def _get_parent_span_id(self, parent_run_id: UUID | None) -> str | None:
        if parent_run_id is None:
            return None
        return self._run_to_span.get(str(parent_run_id))

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
            parent_span_id = self._get_parent_span_id(parent_run_id)
            span = self._tracer.start_span(
                name=str(name),
                span_type="chain",
                parent_span_id=parent_span_id,
                attributes={
                    "chain.type": str(name),
                    "chain.input": json.dumps(inputs, default=str)[:50000],
                },
            )
            self._run_to_span[str(run_id)] = span.span_id
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_chain_start", exc_info=True)

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        try:
            span_id = self._run_to_span.pop(str(run_id), None)
            if span_id:
                self._tracer.end_span(
                    span_id=span_id,
                    status="ok",
                    attributes={
                        "chain.output": json.dumps(outputs, default=str)[:50000],
                    },
                )
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
            span_id = self._run_to_span.pop(str(run_id), None)
            if span_id:
                self._tracer.end_span(
                    span_id=span_id,
                    status="error",
                    error_message=str(error),
                )
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_chain_error", exc_info=True)

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
            parent_span_id = self._get_parent_span_id(parent_run_id)
            span = self._tracer.start_span(
                name=str(model),
                span_type="llm_call",
                parent_span_id=parent_span_id,
                attributes={
                    "llm.provider": serialized.get("id", ["unknown"])[0] if serialized.get("id") else "unknown",
                    "llm.model": str(model),
                    "llm.prompt": json.dumps(prompts, default=str)[:50000],
                },
            )
            self._run_to_span[str(run_id)] = span.span_id
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_llm_start", exc_info=True)

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        try:
            span_id = self._run_to_span.pop(str(run_id), None)
            if not span_id:
                return

            attrs: dict[str, Any] = {}

            # Extract completion text
            if response.generations and response.generations[0]:
                gen = response.generations[0][0]
                attrs["llm.completion"] = gen.text[:50000]

            # Extract token usage
            llm_output = response.llm_output or {}
            token_usage = llm_output.get("token_usage", {})
            if token_usage:
                attrs["llm.tokens.input"] = token_usage.get("prompt_tokens", 0)
                attrs["llm.tokens.output"] = token_usage.get("completion_tokens", 0)
                attrs["llm.tokens.total"] = token_usage.get("total_tokens", 0)

            self._tracer.end_span(
                span_id=span_id,
                status="ok",
                attributes=attrs,
            )
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
            span_id = self._run_to_span.pop(str(run_id), None)
            if span_id:
                self._tracer.end_span(
                    span_id=span_id,
                    status="error",
                    error_message=str(error),
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
            parent_span_id = self._get_parent_span_id(parent_run_id)
            span = self._tracer.start_span(
                name=str(tool_name),
                span_type="tool_use",
                parent_span_id=parent_span_id,
                attributes={
                    "tool.name": str(tool_name),
                    "tool.input": input_str[:50000],
                },
            )
            self._run_to_span[str(run_id)] = span.span_id
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
            span_id = self._run_to_span.pop(str(run_id), None)
            if span_id:
                self._tracer.end_span(
                    span_id=span_id,
                    status="ok",
                    attributes={"tool.output": str(output)[:50000]},
                )
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
            span_id = self._run_to_span.pop(str(run_id), None)
            if span_id:
                self._tracer.end_span(
                    span_id=span_id,
                    status="error",
                    error_message=str(error),
                )
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_tool_error", exc_info=True)

    # --- Agent callbacks ---

    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            parent_span_id = self._get_parent_span_id(parent_run_id)
            span = self._tracer.start_span(
                name=f"Action: {action.tool}",
                span_type="agent_step",
                parent_span_id=parent_span_id,
                attributes={
                    "agent.framework": "langchain",
                    "agent.step_name": action.tool,
                    "agent.input": json.dumps(action.tool_input, default=str)[:50000],
                    "agent.thought": action.log[:50000] if action.log else "",
                },
            )
            self._run_to_span[str(run_id)] = span.span_id
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_agent_action", exc_info=True)

    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        try:
            span_id = self._run_to_span.pop(str(run_id), None)
            if span_id:
                self._tracer.end_span(
                    span_id=span_id,
                    status="ok",
                    attributes={
                        "agent.output": json.dumps(
                            finish.return_values, default=str
                        )[:50000],
                    },
                )
        except Exception:
            logger.debug("BeaconCallbackHandler: error in on_agent_finish", exc_info=True)
