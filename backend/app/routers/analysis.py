"""Analysis router — AI-powered trace debugging endpoints.

All endpoints live under ``/v1/analysis/``.  Provides root-cause analysis,
cost optimization, prompt suggestions, anomaly detection, error patterns,
trace comparison, and trace summarization.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    AnalysisRequest,
    CompareAnalysisRequest,
    CompareAnalysisResponse,
    CostOptimizationResponse,
    AnomalyDetectionResponse,
    ErrorPatternsResponse,
    MultiTraceAnalysisRequest,
    PromptSuggestionsResponse,
    RootCauseAnalysisResponse,
    SpanAnalysisRequest,
    TraceSummaryAnalysisResponse,
)
from app.services import analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/root-cause", response_model=RootCauseAnalysisResponse)
async def root_cause_analysis(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
) -> RootCauseAnalysisResponse:
    """Analyze a trace to identify the root cause of failures."""
    try:
        spans = analysis_service.get_trace_spans(db, request.trace_id)
        context = analysis_service.build_trace_context(spans)

        system_prompt = (
            "You are an AI debugging assistant analyzing execution traces of AI agents. "
            "Given a trace of spans (each representing a unit of work like an LLM call, "
            "tool use, or agent step), identify the root cause of any failures or errors.\n\n"
            "Respond with a JSON object with these exact fields:\n"
            '- "root_cause": string describing the root cause\n'
            '- "affected_spans": array of span_id strings that are affected\n'
            '- "confidence": float between 0.0 and 1.0\n'
            '- "suggested_fix": string with a suggested fix\n\n'
            "Respond ONLY with the JSON object, no other text."
        )
        user_prompt = f"Analyze this trace for root cause of failures:\n\n{context}"

        raw = await analysis_service.call_analysis_llm(system_prompt, user_prompt)
        result = analysis_service.parse_structured_response(
            raw, RootCauseAnalysisResponse
        )
        # Override trace_id to ensure it matches the request
        result.trace_id = request.trace_id
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")


@router.post("/cost-optimization", response_model=CostOptimizationResponse)
async def cost_optimization_analysis(
    request: MultiTraceAnalysisRequest,
    db: Session = Depends(get_db),
) -> CostOptimizationResponse:
    """Analyze LLM call patterns for cost-saving opportunities."""
    try:
        all_context_parts: list[str] = []
        for trace_id in request.trace_ids:
            spans = analysis_service.get_trace_spans(db, trace_id)
            all_context_parts.append(
                f"=== Trace {trace_id} ===\n{analysis_service.build_trace_context(spans)}"
            )
        context = "\n\n".join(all_context_parts)

        system_prompt = (
            "You are an AI cost optimization assistant. Analyze the LLM call patterns "
            "in the provided traces and identify cost-saving opportunities.\n\n"
            "Look for:\n"
            "- Redundant calls (same prompt repeated)\n"
            "- Expensive models used for simple tasks (could use a cheaper model)\n"
            "- Cacheable calls (identical inputs that could be cached)\n"
            "- Token waste from overly long prompts\n\n"
            "Respond with a JSON object with these exact fields:\n"
            '- "suggestions": array of objects, each with:\n'
            '  - "type": string (one of "redundant_call", "model_downgrade", "cacheable", "token_waste")\n'
            '  - "description": string explaining the issue\n'
            '  - "estimated_savings_usd": float\n'
            '  - "affected_spans": array of span_id strings\n\n'
            "Respond ONLY with the JSON object, no other text."
        )
        user_prompt = f"Analyze these traces for cost optimization:\n\n{context}"

        raw = await analysis_service.call_analysis_llm(system_prompt, user_prompt)
        result = analysis_service.parse_structured_response(
            raw, CostOptimizationResponse
        )
        result.trace_ids = request.trace_ids
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")


@router.post("/prompt-suggestions", response_model=PromptSuggestionsResponse)
async def prompt_suggestions(
    request: SpanAnalysisRequest,
    db: Session = Depends(get_db),
) -> PromptSuggestionsResponse:
    """Analyze an LLM call's prompt and suggest improvements."""
    try:
        span = analysis_service.get_span(db, request.span_id)
        attrs: dict[str, Any] = {}
        if span.attributes:
            try:
                attrs = json.loads(span.attributes)
            except (ValueError, TypeError):
                pass

        original_prompt = str(attrs.get("llm.prompt", ""))

        system_prompt = (
            "You are an AI prompt engineering assistant. Analyze the given LLM prompt "
            "and suggest improvements for clarity, specificity, and effectiveness.\n\n"
            "Respond with a JSON object with these exact fields:\n"
            '- "original_prompt": the original prompt text\n'
            '- "suggestions": array of objects, each with:\n'
            '  - "category": string (one of "clarity", "specificity", "formatting", '
            '"few_shot", "instruction", "context")\n'
            '  - "description": string explaining the improvement\n'
            '  - "improved_prompt_snippet": string with the improved text\n\n'
            "Respond ONLY with the JSON object, no other text."
        )
        user_prompt = f"Analyze and improve this prompt:\n\n{original_prompt}"

        raw = await analysis_service.call_analysis_llm(system_prompt, user_prompt)
        result = analysis_service.parse_structured_response(
            raw, PromptSuggestionsResponse
        )
        result.span_id = request.span_id
        result.original_prompt = original_prompt
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")


@router.post("/anomalies", response_model=AnomalyDetectionResponse)
async def anomaly_detection(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
) -> AnomalyDetectionResponse:
    """Compare a trace against historical baselines and flag anomalies."""
    try:
        spans = analysis_service.get_trace_spans(db, request.trace_id)
        context = analysis_service.build_trace_context(spans)
        baseline_text = analysis_service.get_baseline_stats(db, request.trace_id)

        system_prompt = (
            "You are an anomaly detection assistant for AI agent traces. "
            "Compare the given trace against historical baselines and flag anomalies.\n\n"
            "Look for:\n"
            "- Cost spikes (>2x the historical mean)\n"
            "- Latency spikes\n"
            "- Unusual error patterns\n"
            "- Missing expected spans\n\n"
            "Respond with a JSON object with these exact fields:\n"
            '- "anomalies": array of objects, each with:\n'
            '  - "type": string (one of "cost_spike", "latency_spike", "error_pattern", "missing_span")\n'
            '  - "severity": string (one of "low", "medium", "high")\n'
            '  - "description": string explaining the anomaly\n'
            '  - "trace_id": string\n'
            '  - "span_id": string or null\n\n'
            "If no anomalies are found, return an empty anomalies array.\n"
            "Respond ONLY with the JSON object, no other text."
        )
        user_prompt = (
            f"Current trace:\n{context}\n\n"
            f"Historical baselines:\n{baseline_text}"
        )

        raw = await analysis_service.call_analysis_llm(system_prompt, user_prompt)
        result = analysis_service.parse_structured_response(
            raw, AnomalyDetectionResponse
        )
        result.trace_id = request.trace_id
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")


@router.post("/error-patterns", response_model=ErrorPatternsResponse)
async def error_patterns(
    request: MultiTraceAnalysisRequest,
    db: Session = Depends(get_db),
) -> ErrorPatternsResponse:
    """Cluster similar failures and detect common anti-patterns."""
    try:
        all_context_parts: list[str] = []
        for trace_id in request.trace_ids:
            spans = analysis_service.get_trace_spans(db, trace_id)
            all_context_parts.append(
                f"=== Trace {trace_id} ===\n{analysis_service.build_trace_context(spans)}"
            )
        context = "\n\n".join(all_context_parts)

        system_prompt = (
            "You are an error pattern recognition assistant. Analyze the provided traces "
            "and cluster similar failures.\n\n"
            "Look for:\n"
            "- Infinite loops (repeated identical spans)\n"
            "- Repeated tool failures (same tool failing 3+ times)\n"
            "- Context window overflow (token count approaching model limits)\n"
            "- Common error categories: timeout, rate_limit, context_overflow, tool_failure, hallucination\n\n"
            "Respond with a JSON object with these exact fields:\n"
            '- "patterns": array of objects, each with:\n'
            '  - "pattern_name": short descriptive name\n'
            '  - "count": number of occurrences\n'
            '  - "example_trace_ids": array of trace_id strings\n'
            '  - "common_root_cause": string\n'
            '  - "category": string (e.g. "timeout", "rate_limit", etc.)\n\n'
            "If no patterns found, return an empty patterns array.\n"
            "Respond ONLY with the JSON object, no other text."
        )
        user_prompt = f"Analyze these traces for error patterns:\n\n{context}"

        raw = await analysis_service.call_analysis_llm(system_prompt, user_prompt)
        result = analysis_service.parse_structured_response(
            raw, ErrorPatternsResponse
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")


@router.post("/compare", response_model=CompareAnalysisResponse)
async def compare_traces(
    request: CompareAnalysisRequest,
    db: Session = Depends(get_db),
) -> CompareAnalysisResponse:
    """Use AI to identify structural divergence between two traces."""
    try:
        spans_a = analysis_service.get_trace_spans(db, request.trace_id_a)
        spans_b = analysis_service.get_trace_spans(db, request.trace_id_b)
        context_a = analysis_service.build_trace_context(spans_a)
        context_b = analysis_service.build_trace_context(spans_b)

        system_prompt = (
            "You are a trace comparison assistant. Compare two AI agent execution traces "
            "and identify where they diverge.\n\n"
            "Respond with a JSON object with these exact fields:\n"
            '- "divergence_points": array of objects, each with:\n'
            '  - "span_a": span_id from trace A or null\n'
            '  - "span_b": span_id from trace B or null\n'
            '  - "description": string explaining the divergence\n'
            '- "metric_diff": object with:\n'
            '  - "cost_diff_usd": float\n'
            '  - "duration_diff_ms": float\n'
            '  - "token_diff": int\n'
            '  - "span_count_diff": int\n'
            '- "summary": string summarizing the key differences\n\n'
            "Respond ONLY with the JSON object, no other text."
        )
        user_prompt = (
            f"=== Trace A ({request.trace_id_a}) ===\n{context_a}\n\n"
            f"=== Trace B ({request.trace_id_b}) ===\n{context_b}"
        )

        raw = await analysis_service.call_analysis_llm(system_prompt, user_prompt)
        result = analysis_service.parse_structured_response(
            raw, CompareAnalysisResponse
        )
        result.trace_id_a = request.trace_id_a
        result.trace_id_b = request.trace_id_b
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")


@router.post("/summarize", response_model=TraceSummaryAnalysisResponse)
async def summarize_trace(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
) -> TraceSummaryAnalysisResponse:
    """Generate a natural language summary of what the agent did."""
    try:
        spans = analysis_service.get_trace_spans(db, request.trace_id)
        context = analysis_service.build_trace_context(spans)

        system_prompt = (
            "You are a trace summarization assistant. Given an AI agent execution trace, "
            "generate a concise natural language summary of what the agent did.\n\n"
            "Respond with a JSON object with these exact fields:\n"
            '- "summary": a 1-3 sentence natural language summary\n'
            '- "key_events": array of objects, each with:\n'
            '  - "span_id": string\n'
            '  - "description": short description of what happened\n\n'
            "Focus on the most important actions, errors, and outcomes.\n"
            "Respond ONLY with the JSON object, no other text."
        )
        user_prompt = f"Summarize this trace:\n\n{context}"

        raw = await analysis_service.call_analysis_llm(system_prompt, user_prompt)
        result = analysis_service.parse_structured_response(
            raw, TraceSummaryAnalysisResponse
        )
        result.trace_id = request.trace_id
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")
