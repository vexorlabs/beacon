"""Shared infrastructure for AI-powered trace analysis.

Provides helpers to build LLM prompts from trace data, call the LLM,
and parse structured JSON responses into Pydantic models.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app import models
from app.services import settings_service
from app.services.llm_client import (
    call_anthropic,
    call_google,
    call_openai,
    provider_for_model,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Default model used for analysis calls.  Override with BEACON_ANALYSIS_MODEL.
DEFAULT_ANALYSIS_MODEL = "gpt-4o-mini"


def _get_analysis_model() -> str:
    return os.environ.get("BEACON_ANALYSIS_MODEL", DEFAULT_ANALYSIS_MODEL)


def _get_api_key(provider: str) -> str:
    """Resolve API key from env vars then from stored settings."""
    if provider == "openai":
        return (
            os.environ.get("OPENAI_API_KEY", "")
            or settings_service.get_api_key("openai")
            or ""
        )
    if provider == "anthropic":
        return (
            os.environ.get("ANTHROPIC_API_KEY", "")
            or settings_service.get_api_key("anthropic")
            or ""
        )
    if provider == "google":
        return (
            os.environ.get("GOOGLE_API_KEY", "")
            or os.environ.get("GEMINI_API_KEY", "")
            or settings_service.get_api_key("google")
            or ""
        )
    raise ValueError(f"Unsupported provider: {provider}")


# ---------------------------------------------------------------------------
# Trace context builder
# ---------------------------------------------------------------------------


def build_trace_context(spans: list[models.Span]) -> str:
    """Format a list of ORM Span objects into a structured text block.

    The output is designed to be included in an LLM prompt so the model
    can reason about the trace.
    """
    if not spans:
        return "No spans in this trace."

    lines: list[str] = []
    for i, span in enumerate(spans, 1):
        attrs: dict[str, Any] = {}
        if span.attributes:
            try:
                attrs = json.loads(span.attributes)
            except (json.JSONDecodeError, TypeError):
                pass

        duration_ms: float | None = None
        if span.start_time is not None and span.end_time is not None:
            duration_ms = (span.end_time - span.start_time) * 1000

        lines.append(f"[{i}] span_id={span.span_id}")
        lines.append(f"    name: {span.name}")
        lines.append(f"    type: {span.span_type}")
        lines.append(f"    status: {span.status}")
        if span.parent_span_id:
            lines.append(f"    parent: {span.parent_span_id}")
        if duration_ms is not None:
            lines.append(f"    duration_ms: {duration_ms:.1f}")
        if span.error_message:
            lines.append(f"    error: {span.error_message}")

        # Include select attributes that are useful for analysis
        for key in (
            "llm.model",
            "llm.provider",
            "llm.tokens.input",
            "llm.tokens.output",
            "llm.cost_usd",
            "llm.completion",
            "llm.prompt",
            "llm.finish_reason",
            "llm.tool_calls",
            "tool.name",
            "tool.input",
            "tool.output",
        ):
            if key in attrs:
                val = attrs[key]
                # Truncate long values
                val_str = str(val)
                if len(val_str) > 500:
                    val_str = val_str[:500] + "..."
                lines.append(f"    {key}: {val_str}")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM call helper
# ---------------------------------------------------------------------------


async def call_analysis_llm(system_prompt: str, user_prompt: str) -> str:
    """Call the configured analysis LLM and return raw completion text."""
    model = _get_analysis_model()
    provider = provider_for_model(model)
    api_key = _get_api_key(provider)

    if not api_key:
        raise ValueError(
            f"No API key configured for {provider}. "
            f"Set the appropriate environment variable or configure it in Settings."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    if provider == "openai":
        completion, _, _ = await call_openai(api_key, model, messages, temperature=0.2)
    elif provider == "anthropic":
        completion, _, _ = await call_anthropic(
            api_key, model, messages, temperature=0.2
        )
    elif provider == "google":
        completion, _, _ = await call_google(api_key, model, messages, temperature=0.2)
    else:
        raise ValueError(f"Analysis does not support provider: {provider}")

    return completion


# ---------------------------------------------------------------------------
# Structured response parser
# ---------------------------------------------------------------------------


def parse_structured_response(raw_text: str, response_model: type[T]) -> T:
    """Parse LLM output as JSON and validate against a Pydantic model.

    Handles common LLM quirks: markdown code fences, leading text before JSON.
    """
    text = raw_text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        # Remove first line (```json or ```)
        first_newline = text.index("\n") if "\n" in text else len(text)
        text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[: -3]
        text = text.strip()

    # Try to find JSON object boundaries
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

    try:
        return response_model.model_validate(data)
    except ValidationError as exc:
        raise ValueError(
            f"LLM response does not match expected schema: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Trace/span data loaders
# ---------------------------------------------------------------------------


def get_trace_spans(db: Session, trace_id: str) -> list[models.Span]:
    """Load all spans for a trace, ordered by start_time."""
    trace = db.get(models.Trace, trace_id)
    if trace is None:
        raise ValueError(f"Trace not found: {trace_id}")

    spans: list[models.Span] = (
        db.query(models.Span)
        .filter(models.Span.trace_id == trace_id)
        .order_by(models.Span.start_time)
        .all()
    )
    return spans


def get_span(db: Session, span_id: str) -> models.Span:
    """Load a single span by ID."""
    span = db.get(models.Span, span_id)
    if span is None:
        raise ValueError(f"Span not found: {span_id}")
    return span


def get_baseline_stats(db: Session, trace_id: str, limit: int = 50) -> str:
    """Build a baseline summary from recent traces, excluding *trace_id*."""
    recent_traces: list[models.Trace] = (
        db.query(models.Trace)
        .order_by(models.Trace.start_time.desc())
        .limit(limit)
        .all()
    )
    stats: list[str] = []
    for t in recent_traces:
        if t.trace_id == trace_id:
            continue
        cost = t.total_cost_usd or 0.0
        duration_ms = (
            (t.end_time - t.start_time) * 1000
            if t.end_time is not None and t.start_time is not None
            else 0.0
        )
        stats.append(
            f"trace={t.trace_id} cost={cost:.4f} "
            f"duration={duration_ms:.0f}ms spans={t.span_count}"
        )
    return "\n".join(stats[:20]) if stats else "No historical data available."
