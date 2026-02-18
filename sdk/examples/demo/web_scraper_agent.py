"""Beacon Demo — Web Scraper Agent

Simulates a browser automation agent that scrapes Hacker News headlines.
Navigates pages, takes screenshots, and handles a connection timeout
gracefully. No API keys or real browser needed.

Span tree produced:
    Web Scraper Agent (agent_step)
      ├── plan_scraping (llm_call, openai/gpt-4o-mini)
      ├── navigate_to_site (browser_action, navigate)
      ├── wait_for_content (browser_action, wait_for_selector)
      ├── take_screenshot (browser_action, screenshot)       ← has base64 PNG
      ├── parse_headlines (llm_call, openai/gpt-4o-mini)     ← has llm.tool_calls
      ├── visit_article_1 (browser_action, navigate)
      ├── visit_article_2 (browser_action, navigate)          ← ERROR (timeout)
      └── compile_results (llm_call, openai/gpt-4o-mini)

SDK patterns demonstrated:
    - @observe for LLM calls
    - tracer.start_span() / end_span() for browser_action spans
    - browser.action, browser.url, browser.selector, browser.screenshot attributes
    - Controlled error on a single span without killing the parent
"""

from __future__ import annotations

import json
import time

import beacon_sdk
from beacon_sdk import observe
from beacon_sdk.models import SpanStatus, SpanType

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
        # gpt-4o-mini: $0.15/M input, $0.60/M output
        span.set_attribute(
            "llm.cost_usd",
            round(input_tokens * 0.15 / 1_000_000 + output_tokens * 0.60 / 1_000_000, 6),
        )


def _browser_action(
    name: str,
    action: str,
    url: str | None = None,
    selector: str | None = None,
    value: str | None = None,
    screenshot: str | None = None,
    duration: float = 0.8,
    error: str | None = None,
) -> None:
    """Create a browser_action span with the given attributes.

    Uses tracer.start_span()/end_span() directly for controlled error status.
    """
    tracer = beacon_sdk.get_tracer()
    if tracer is None:
        return

    span, token = tracer.start_span(name, span_type=SpanType.BROWSER_ACTION)
    time.sleep(duration)

    span.set_attribute("browser.action", action)
    if url is not None:
        span.set_attribute("browser.url", url)
    if selector is not None:
        span.set_attribute("browser.selector", selector)
    if value is not None:
        span.set_attribute("browser.value", value)
    if screenshot is not None:
        span.set_attribute("browser.screenshot", screenshot)

    if error is not None:
        tracer.end_span(span, token, status=SpanStatus.ERROR, error_message=error)
    else:
        tracer.end_span(span, token, status=SpanStatus.OK)


# --- LLM span functions ---


@observe(name="plan_scraping", span_type="llm_call")
def plan_scraping(query: str) -> str:
    time.sleep(1.0)
    _set_llm_attrs(
        provider="openai",
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": F.SCRAPER_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        completion=F.SCRAPER_PLAN_COMPLETION,
        input_tokens=89,
        output_tokens=102,
    )
    return F.SCRAPER_PLAN_COMPLETION


@observe(name="parse_headlines", span_type="llm_call")
def parse_headlines(screenshot_context: str) -> str:
    time.sleep(2.0)
    _set_llm_attrs(
        provider="openai",
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": F.SCRAPER_SYSTEM_PROMPT},
            {"role": "user", "content": "Extract the top 3 headlines from this page content."},
        ],
        completion=F.SCRAPER_PARSE_COMPLETION,
        input_tokens=234,
        output_tokens=156,
        tool_calls=F.SCRAPER_PARSE_TOOL_CALLS,
        finish_reason="tool_calls",
    )
    return F.SCRAPER_HEADLINES_JSON


@observe(name="compile_results", span_type="llm_call")
def compile_results(headlines: str) -> str:
    time.sleep(1.5)
    _set_llm_attrs(
        provider="openai",
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": F.SCRAPER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Compile these headlines into a report:\n{headlines}"},
        ],
        completion=F.SCRAPER_RESULTS_COMPLETION,
        input_tokens=312,
        output_tokens=198,
    )
    return F.SCRAPER_RESULTS_COMPLETION


@observe(name="Web Scraper Agent", span_type="agent_step")
def _web_scraper_agent() -> str:
    plan_scraping(F.SCRAPER_USER_QUERY)

    # Navigate and capture page
    _browser_action(
        name="navigate_to_site",
        action="navigate",
        url="https://news.ycombinator.com",
        duration=1.2,
    )
    _browser_action(
        name="wait_for_content",
        action="wait_for_selector",
        selector="#hnmain .titleline",
        duration=0.5,
    )
    _browser_action(
        name="take_screenshot",
        action="screenshot",
        url="https://news.ycombinator.com",
        screenshot=F.TINY_PNG_BASE64,
        duration=0.8,
    )

    # Parse what we found
    headlines = parse_headlines("screenshot of HN front page")

    # Visit individual articles
    _browser_action(
        name="visit_article_1",
        action="navigate",
        url="https://github.com/example/beacon",
        duration=1.0,
    )
    _browser_action(
        name="visit_article_2",
        action="navigate",
        url="https://antonz.org/sqlite-is-not-a-toy-database/",
        duration=0.5,
        error="TimeoutError: Navigation timeout of 30000ms exceeded",
    )

    # Compile results even with partial data
    report = compile_results(headlines)
    return report


def run() -> None:
    """Entry point for the orchestrator."""
    beacon_sdk.init(backend_url="http://localhost:7474", auto_patch=False)
    _web_scraper_agent()


if __name__ == "__main__":
    run()
    print("Web Scraper Agent demo complete.")
