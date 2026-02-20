from __future__ import annotations

import json
import os
import time
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app import models
from app.schemas import ReplayDiff, ReplayResponse
from app.services import settings_service
from app.services.llm_client import call_anthropic, call_google, call_openai, estimate_cost
from app.services import prompt_version_service


async def replay_llm_call(
    db: Session,
    span_id: str,
    modified_attributes: dict[str, Any],
) -> ReplayResponse:
    """Replay an LLM call span with modified attributes."""
    span = db.get(models.Span, span_id)
    if span is None:
        raise ValueError("Span not found")

    if span.span_type != "llm_call":
        raise ValueError("Replay only supported for llm_call spans")

    original_attrs: dict[str, Any] = json.loads(span.attributes or "{}")
    merged_attrs = {**original_attrs, **modified_attributes}

    provider: str = merged_attrs.get("llm.provider", "")
    prompt_raw = merged_attrs.get("llm.prompt", "[]")
    messages: list[dict[str, str]] = (
        json.loads(prompt_raw) if isinstance(prompt_raw, str) else prompt_raw
    )
    model: str = merged_attrs.get("llm.model", "")
    temperature: float = float(merged_attrs.get("llm.temperature", 1.0))
    max_tokens_raw = merged_attrs.get("llm.max_tokens")
    max_tokens: int | None = (
        int(max_tokens_raw) if max_tokens_raw is not None else None
    )

    # Use env-var keys first, fall back to config.json keys
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "") or settings_service.get_api_key("openai") or ""
        new_completion, input_tokens, output_tokens = await call_openai(
            api_key, model, messages, temperature, max_tokens
        )
    elif provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "") or settings_service.get_api_key("anthropic") or ""
        new_completion, input_tokens, output_tokens = await call_anthropic(
            api_key, model, messages, temperature, max_tokens
        )
    elif provider == "google":
        api_key = (
            os.environ.get("GOOGLE_API_KEY", "")
            or os.environ.get("GEMINI_API_KEY", "")
            or settings_service.get_api_key("google")
            or ""
        )
        new_completion, input_tokens, output_tokens = await call_google(
            api_key, model, messages, temperature, max_tokens
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    original_completion: str = original_attrs.get("llm.completion", "")
    diff = ReplayDiff(
        old_completion=original_completion,
        new_completion=new_completion,
        changed=original_completion != new_completion,
    )

    cost_usd = estimate_cost(model, input_tokens, output_tokens)
    new_output: dict[str, Any] = {
        "llm.completion": new_completion,
        "llm.tokens.input": input_tokens,
        "llm.tokens.output": output_tokens,
        "llm.cost_usd": cost_usd,
    }

    replay_id = str(uuid4())
    replay_run = models.ReplayRun(
        replay_id=replay_id,
        original_span_id=span_id,
        trace_id=span.trace_id,
        modified_input=json.dumps(modified_attributes),
        new_output=json.dumps(new_output),
        diff=json.dumps(diff.model_dump()),
        created_at=time.time(),
    )
    db.add(replay_run)
    db.commit()

    # Auto-save the modified prompt as a prompt version
    modified_prompt = modified_attributes.get("llm.prompt")
    if modified_prompt is not None:
        if isinstance(modified_prompt, str):
            prompt_text = modified_prompt
        else:
            prompt_text = json.dumps(modified_prompt)
        prompt_version_service.create_version(
            db, span_id, prompt_text, label="Replay"
        )

    return ReplayResponse(
        replay_id=replay_id,
        original_span_id=span_id,
        new_output=new_output,
        diff=diff,
    )
