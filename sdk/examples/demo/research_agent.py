"""Beacon Demo — Research Agent

Simulates a multi-step research agent that plans, searches, reads articles,
and synthesizes findings into a report. No API keys needed.

Span tree produced:
    Research Agent (agent_step)
      ├── plan_research (llm_call, openai/gpt-4o)
      ├── web_search (tool_use)
      ├── read_article (tool_use)
      ├── synthesize_findings (llm_call, openai/gpt-4o)  ← has llm.tool_calls
      ├── write_report (llm_call, openai/gpt-4o)
      └── save_report (tool_use)

SDK patterns demonstrated:
    - @observe decorator for automatic span nesting
    - get_current_span().set_attribute() for setting LLM attributes
    - tool_use spans with tool.name / tool.input / tool.output
    - llm.tool_calls attribute on an LLM call span
"""

from __future__ import annotations

import json
import time

import beacon_sdk
from beacon_sdk import observe

from . import _fixtures as F


def _set_llm_attrs(
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    completion: str,
    input_tokens: int,
    output_tokens: int,
    *,
    temperature: float = 0.3,
    finish_reason: str = "stop",
    tool_calls: str | None = None,
    cost_usd: float | None = None,
) -> None:
    """Helper to set standard LLM attributes on the current span."""
    span = beacon_sdk.get_current_span()
    if span is None:
        return
    span.set_attribute("llm.provider", provider)
    span.set_attribute("llm.model", model)
    span.set_attribute("llm.prompt", json.dumps(messages))
    span.set_attribute("llm.completion", completion)
    span.set_attribute("llm.tokens.input", input_tokens)
    span.set_attribute("llm.tokens.output", output_tokens)
    span.set_attribute("llm.tokens.total", input_tokens + output_tokens)
    span.set_attribute("llm.temperature", temperature)
    span.set_attribute("llm.finish_reason", finish_reason)
    if tool_calls is not None:
        span.set_attribute("llm.tool_calls", tool_calls)
    if cost_usd is not None:
        span.set_attribute("llm.cost_usd", cost_usd)
    else:
        # Rough estimate: $5/M input, $15/M output for gpt-4o
        span.set_attribute(
            "llm.cost_usd",
            round(input_tokens * 5 / 1_000_000 + output_tokens * 15 / 1_000_000, 6),
        )


def _set_tool_attrs(name: str, tool_input: str, tool_output: str) -> None:
    """Helper to set tool_use attributes on the current span."""
    span = beacon_sdk.get_current_span()
    if span is None:
        return
    span.set_attribute("tool.name", name)
    span.set_attribute("tool.input", tool_input)
    span.set_attribute("tool.output", tool_output)


# --- Span functions ---


@observe(name="plan_research", span_type="llm_call")
def plan_research(question: str) -> str:
    time.sleep(1.5)
    _set_llm_attrs(
        provider="openai",
        model="gpt-4o",
        messages=[
            {"role": "system", "content": F.RESEARCH_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        completion=F.RESEARCH_PLAN_COMPLETION,
        input_tokens=312,
        output_tokens=87,
    )
    return F.RESEARCH_PLAN_COMPLETION


@observe(name="web_search", span_type="tool_use")
def web_search(query: str) -> str:
    time.sleep(0.8)
    _set_tool_attrs(
        name="web_search",
        tool_input=json.dumps({"query": query}),
        tool_output=F.RESEARCH_SEARCH_RESULTS,
    )
    return F.RESEARCH_SEARCH_RESULTS


@observe(name="read_article", span_type="tool_use")
def read_article(url: str) -> str:
    time.sleep(0.6)
    _set_tool_attrs(
        name="read_article",
        tool_input=json.dumps({"url": url}),
        tool_output=F.RESEARCH_ARTICLE_CONTENT,
    )
    return F.RESEARCH_ARTICLE_CONTENT


@observe(name="synthesize_findings", span_type="llm_call")
def synthesize_findings(question: str, context: str) -> str:
    time.sleep(2.0)
    _set_llm_attrs(
        provider="openai",
        model="gpt-4o",
        messages=[
            {"role": "system", "content": F.RESEARCH_SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": "I found relevant information. Let me search for more details on the regulatory response."},
            {"role": "user", "content": f"Here is the research context:\n\n{context[:500]}"},
        ],
        completion=F.RESEARCH_SYNTHESIS_COMPLETION,
        input_tokens=1245,
        output_tokens=342,
        tool_calls=F.RESEARCH_SYNTHESIS_TOOL_CALLS,
        finish_reason="tool_calls",
    )
    return F.RESEARCH_SYNTHESIS_COMPLETION


@observe(name="write_report", span_type="llm_call")
def write_report(synthesis: str) -> str:
    time.sleep(1.5)
    _set_llm_attrs(
        provider="openai",
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Write a structured report based on the research findings."},
            {"role": "user", "content": f"Write a report based on:\n\n{synthesis}"},
        ],
        completion=F.RESEARCH_REPORT_COMPLETION,
        input_tokens=856,
        output_tokens=278,
    )
    return F.RESEARCH_REPORT_COMPLETION


@observe(name="save_report", span_type="tool_use")
def save_report(report: str) -> str:
    time.sleep(0.3)
    output = f"Saved report ({len(report)} chars) to research_report.md"
    _set_tool_attrs(
        name="save_to_file",
        tool_input=json.dumps({"path": "research_report.md", "content_length": len(report)}),
        tool_output=output,
    )
    return output


@observe(name="Research Agent", span_type="agent_step")
def _research_agent() -> str:
    question = F.RESEARCH_USER_QUERY
    plan = plan_research(question)
    results = web_search("2008 financial crisis causes timeline")
    article = read_article("https://www.britannica.com/topic/financial-crisis-of-2008")
    synthesis = synthesize_findings(question, article)
    report = write_report(synthesis)
    save_report(report)
    return report


def run() -> None:
    """Entry point for the orchestrator."""
    beacon_sdk.init(backend_url="http://localhost:7474", auto_patch=False)
    _research_agent()


if __name__ == "__main__":
    run()
    print("Research Agent demo complete.")
