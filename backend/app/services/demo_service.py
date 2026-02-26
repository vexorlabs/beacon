"""Demo agent service — runs pre-defined agent scenarios with real LLM calls.

Each scenario defines a system prompt, user message, tool definitions, and
a tool simulator. The agent loop makes real API calls, letting the LLM
decide which tools to invoke. Tool results are simulated.

Spans are created using the same two-phase pattern as playground_service.py:
UNSET → OK/ERROR, broadcast via WebSocket so the frontend updates live.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.schemas import (
    DemoRunResponse,
    DemoScenarioResponse,
    SpanCreate,
    SpanStatus,
    SpanType,
)
from app.services import settings_service, span_service
from app.services.llm_client import (
    LlmToolResponse,
    call_anthropic_with_tools,
    call_openai_with_tools,
    estimate_cost,
    provider_for_model,
)
from app.ws.manager import ws_manager

logger = logging.getLogger(__name__)

MAX_AGENT_STEPS = 5


# ---------------------------------------------------------------------------
# Broadcast helpers (same pattern as playground_service.py)
# ---------------------------------------------------------------------------


async def _broadcast_span(db: Session, span_data: SpanCreate) -> None:
    span_service.ingest_spans(db, [span_data])
    orm_span = span_service.get_span_by_id(db, span_data.span_id)
    if orm_span is not None:
        span_dict = span_service.span_to_response(orm_span).model_dump()
        await ws_manager.broadcast_span(span_dict)


async def _broadcast_trace_created(trace_id: str, name: str, start: float) -> None:
    await ws_manager.broadcast_trace_created(
        {
            "trace_id": trace_id,
            "name": name,
            "start_time": start,
            "status": "unset",
        }
    )


# ---------------------------------------------------------------------------
# Simulated tool results
# ---------------------------------------------------------------------------


def _simulate_web_search(arguments: str) -> str:
    return json.dumps(
        [
            {
                "title": "REST vs GraphQL: A Detailed Comparison",
                "url": "https://www.example.com/rest-vs-graphql",
                "snippet": (
                    "REST uses fixed endpoints returning predetermined data structures, "
                    "while GraphQL provides a single endpoint where clients specify exactly "
                    "what data they need. REST is simpler for basic CRUD, but GraphQL "
                    "excels when clients need flexible data fetching."
                ),
            },
            {
                "title": "When to Use GraphQL vs REST APIs",
                "url": "https://www.example.com/when-graphql",
                "snippet": (
                    "GraphQL reduces over-fetching and under-fetching common in REST. "
                    "However, REST benefits from HTTP caching, simpler error handling, "
                    "and better tooling maturity. Choose based on your data requirements."
                ),
            },
        ],
        indent=2,
    )


def _simulate_run_linter(arguments: str) -> str:
    return json.dumps(
        {
            "warnings": [
                {
                    "line": 3,
                    "severity": "warning",
                    "code": "W0612",
                    "message": "Unused variable 'temp'",
                },
                {
                    "line": 7,
                    "severity": "error",
                    "code": "E0602",
                    "message": "Undefined variable 'resutl' (likely typo for 'result')",
                },
                {
                    "line": 12,
                    "severity": "warning",
                    "code": "W0104",
                    "message": "Statement seems to have no effect",
                },
            ],
            "summary": "Found 1 error and 2 warnings",
        },
        indent=2,
    )


def _simulate_search_flights(arguments: str) -> str:
    return json.dumps(
        [
            {
                "airline": "ANA",
                "flight": "NH105",
                "departure": "SFO 11:30 PM",
                "arrival": "NRT 4:30 AM+1",
                "duration": "11h 00m",
                "price_usd": 850,
                "class": "Economy",
            },
            {
                "airline": "JAL",
                "flight": "JL1",
                "departure": "SFO 1:05 PM",
                "arrival": "HND 5:25 PM+1",
                "duration": "11h 20m",
                "price_usd": 920,
                "class": "Economy",
            },
            {
                "airline": "United",
                "flight": "UA837",
                "departure": "SFO 2:35 PM",
                "arrival": "NRT 5:55 PM+1",
                "duration": "11h 20m",
                "price_usd": 780,
                "class": "Economy",
            },
        ],
        indent=2,
    )


def _simulate_search_hotels(arguments: str) -> str:
    return json.dumps(
        [
            {
                "name": "Hotel Gracery Shinjuku",
                "location": "Shinjuku, Tokyo",
                "rating": 4.3,
                "price_per_night_usd": 120,
                "amenities": ["Free WiFi", "Restaurant", "Godzilla terrace"],
            },
            {
                "name": "The Prince Park Tower",
                "location": "Minato, near Tokyo Tower",
                "rating": 4.5,
                "price_per_night_usd": 195,
                "amenities": ["Spa", "Pool", "Multiple restaurants", "City views"],
            },
            {
                "name": "MUJI Hotel Ginza",
                "location": "Ginza, Tokyo",
                "rating": 4.4,
                "price_per_night_usd": 165,
                "amenities": ["Minimalist design", "Restaurant", "MUJI store"],
            },
        ],
        indent=2,
    )


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------


TOOL_SIMULATORS: dict[str, Callable[[str], str]] = {
    "web_search": _simulate_web_search,
    "run_linter": _simulate_run_linter,
    "search_flights": _simulate_search_flights,
    "search_hotels": _simulate_search_hotels,
}


@dataclass
class ScenarioDef:
    key: str
    name: str
    description: str
    provider: str
    model: str
    system_prompt: str
    user_message: str
    tools_openai: list[dict[str, Any]] = field(default_factory=list)
    tools_anthropic: list[dict[str, Any]] = field(default_factory=list)


SCENARIOS: dict[str, ScenarioDef] = {}

# --- Research Assistant (OpenAI) ---
SCENARIOS["research_assistant"] = ScenarioDef(
    key="research_assistant",
    name="Research Assistant",
    description="Multi-step research with web search tool",
    provider="openai",
    model="gpt-4o-mini",
    system_prompt=(
        "You are a research assistant. When the user asks a question, use the "
        "web_search tool to find information, then synthesize a clear answer "
        "based on the search results. Always use the tool before answering."
    ),
    user_message="What are the key differences between REST and GraphQL APIs?",
    tools_openai=[
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for information on a topic.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                        }
                    },
                    "required": ["query"],
                },
            },
        }
    ],
)

# --- Code Reviewer (Anthropic) ---
SCENARIOS["code_reviewer"] = ScenarioDef(
    key="code_reviewer",
    name="Code Reviewer",
    description="Code analysis with linting tool",
    provider="anthropic",
    model="claude-haiku-4-5-20251001",
    system_prompt=(
        "You are a code reviewer. When given code to review, first run the "
        "run_linter tool to check for issues, then provide a thorough review "
        "covering bugs, style, and improvements. Always use the tool first."
    ),
    user_message=(
        "Review this Python function for bugs and improvements:\n\n"
        "```python\n"
        "def calculate_average(numbers):\n"
        "    temp = 0\n"
        "    total = 0\n"
        "    for n in numbers:\n"
        "        total += n\n"
        "    avg = total / len(numbers)\n"
        "    resutl = round(avg, 2)\n"
        "    return result\n"
        "```"
    ),
    tools_anthropic=[
        {
            "name": "run_linter",
            "description": "Run a Python linter on the provided code and return warnings/errors.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to lint",
                    }
                },
                "required": ["code"],
            },
        }
    ],
)

# --- Trip Planner (OpenAI) ---
SCENARIOS["trip_planner"] = ScenarioDef(
    key="trip_planner",
    name="Trip Planner",
    description="Travel planning with flight and hotel search",
    provider="openai",
    model="gpt-4o-mini",
    system_prompt=(
        "You are a travel planner. Use the search_flights and search_hotels "
        "tools to find options, then build a detailed itinerary. Always search "
        "for both flights and hotels before making recommendations."
    ),
    user_message="Plan a weekend trip to Tokyo in April. I'm flying from San Francisco.",
    tools_openai=[
        {
            "type": "function",
            "function": {
                "name": "search_flights",
                "description": "Search for available flights between cities.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "from_city": {
                            "type": "string",
                            "description": "Departure city",
                        },
                        "to_city": {
                            "type": "string",
                            "description": "Destination city",
                        },
                        "dates": {"type": "string", "description": "Travel dates"},
                    },
                    "required": ["from_city", "to_city", "dates"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_hotels",
                "description": "Search for hotels in a city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City to search in"},
                        "dates": {
                            "type": "string",
                            "description": "Check-in/check-out dates",
                        },
                        "budget": {
                            "type": "string",
                            "description": "Budget range (e.g. 'moderate')",
                        },
                    },
                    "required": ["city", "dates"],
                },
            },
        },
    ],
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_scenarios() -> list[DemoScenarioResponse]:
    """Return all available demo scenarios with API key status."""
    result: list[DemoScenarioResponse] = []
    for scenario in SCENARIOS.values():
        api_key = settings_service.get_api_key(scenario.provider)
        result.append(
            DemoScenarioResponse(
                key=scenario.key,
                name=scenario.name,
                description=scenario.description,
                provider=scenario.provider,
                model=scenario.model,
                api_key_configured=bool(api_key),
            )
        )
    return result


async def run_agent(db: Session, scenario_key: str) -> DemoRunResponse:
    """Start a demo agent. Creates the trace immediately, runs the loop in background."""
    scenario = SCENARIOS.get(scenario_key)
    if scenario is None:
        raise ValueError(f"Unknown scenario: {scenario_key}")

    api_key = settings_service.get_api_key(scenario.provider)
    if not api_key:
        raise ValueError(
            f"No API key configured for {scenario.provider}. " "Add one in Settings."
        )

    trace_id = str(uuid4())
    now = time.time()
    root_span_id = str(uuid4())

    # Create root span immediately so frontend can navigate to it
    root_span = SpanCreate(
        span_id=root_span_id,
        trace_id=trace_id,
        parent_span_id=None,
        span_type=SpanType.AGENT_STEP,
        name=scenario.name,
        status=SpanStatus.UNSET,
        start_time=now,
        attributes={"demo": True, "demo.scenario": scenario_key},
    )
    await _broadcast_trace_created(trace_id, scenario.name, now)
    await _broadcast_span(db, root_span)

    # Fire off the agent loop in background
    asyncio.create_task(_run_agent_loop(trace_id, root_span_id, now, scenario, api_key))

    return DemoRunResponse(trace_id=trace_id)


# ---------------------------------------------------------------------------
# Agent loop (runs as background task)
# ---------------------------------------------------------------------------


async def _call_llm(
    scenario: ScenarioDef,
    api_key: str,
    messages: list[dict[str, Any]],
) -> LlmToolResponse:
    """Call the appropriate LLM based on the scenario's provider."""
    if scenario.provider == "openai":
        return await call_openai_with_tools(
            api_key,
            scenario.model,
            messages,
            tools=scenario.tools_openai or None,
            temperature=0.7,
        )
    elif scenario.provider == "anthropic":
        return await call_anthropic_with_tools(
            api_key,
            scenario.model,
            messages,
            tools=scenario.tools_anthropic or None,
            temperature=0.7,
        )
    else:
        raise ValueError(f"Unsupported provider: {scenario.provider}")


def _build_tool_calls_json(
    scenario: ScenarioDef, tool_calls: list[dict[str, Any]]
) -> str:
    """Serialize tool calls to JSON for the llm.tool_calls span attribute."""
    return json.dumps(tool_calls)


def _simulate_tool(tool_name: str, arguments: str) -> str:
    """Run a simulated tool and return its output."""
    simulator = TOOL_SIMULATORS.get(tool_name)
    if simulator is not None:
        return simulator(arguments)
    return json.dumps({"result": f"Simulated result for {tool_name}"})


async def _run_agent_loop(
    trace_id: str,
    root_span_id: str,
    start_time: float,
    scenario: ScenarioDef,
    api_key: str,
) -> None:
    """Execute the agent's tool-calling loop. Runs as a background asyncio task."""
    db = SessionLocal()
    try:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": scenario.system_prompt},
            {"role": "user", "content": scenario.user_message},
        ]

        for step in range(MAX_AGENT_STEPS):
            llm_span_id = str(uuid4())
            llm_start = time.time()

            # Broadcast LLM span as UNSET (in-flight)
            llm_span_unset = SpanCreate(
                span_id=llm_span_id,
                trace_id=trace_id,
                parent_span_id=root_span_id,
                span_type=SpanType.LLM_CALL,
                name=scenario.model,
                status=SpanStatus.UNSET,
                start_time=llm_start,
                attributes={
                    "llm.provider": scenario.provider,
                    "llm.model": scenario.model,
                    "llm.prompt": json.dumps(messages),
                    "llm.temperature": 0.7,
                },
            )
            await _broadcast_span(db, llm_span_unset)

            # Make real LLM call
            try:
                response = await _call_llm(scenario, api_key, messages)
            except Exception as exc:
                llm_end = time.time()
                error_span = SpanCreate(
                    span_id=llm_span_id,
                    trace_id=trace_id,
                    parent_span_id=root_span_id,
                    span_type=SpanType.LLM_CALL,
                    name=scenario.model,
                    status=SpanStatus.ERROR,
                    error_message=str(exc)[:200],
                    start_time=llm_start,
                    end_time=llm_end,
                    attributes={
                        "llm.provider": scenario.provider,
                        "llm.model": scenario.model,
                        "llm.prompt": json.dumps(messages),
                    },
                )
                await _broadcast_span(db, error_span)
                raise

            llm_end = time.time()
            cost = estimate_cost(
                scenario.model, response.input_tokens, response.output_tokens
            )

            # Build attributes for the completed LLM span
            llm_attrs: dict[str, Any] = {
                "llm.provider": scenario.provider,
                "llm.model": scenario.model,
                "llm.prompt": json.dumps(messages),
                "llm.completion": response.completion,
                "llm.tokens.input": response.input_tokens,
                "llm.tokens.output": response.output_tokens,
                "llm.tokens.total": response.input_tokens + response.output_tokens,
                "llm.cost_usd": cost,
                "llm.temperature": 0.7,
                "llm.finish_reason": response.finish_reason,
            }
            if response.tool_calls:
                llm_attrs["llm.tool_calls"] = _build_tool_calls_json(
                    scenario, response.tool_calls
                )

            llm_span_ok = SpanCreate(
                span_id=llm_span_id,
                trace_id=trace_id,
                parent_span_id=root_span_id,
                span_type=SpanType.LLM_CALL,
                name=scenario.model,
                status=SpanStatus.OK,
                start_time=llm_start,
                end_time=llm_end,
                attributes=llm_attrs,
            )
            await _broadcast_span(db, llm_span_ok)

            # If no tool calls, the agent is done
            if not response.tool_calls:
                break

            # Process tool calls
            if scenario.provider == "openai":
                # OpenAI: append assistant message with tool_calls, then tool results
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.completion or None,
                        "tool_calls": response.tool_calls,
                    }
                )
                for tc in response.tool_calls:
                    tool_name = tc["function"]["name"]
                    tool_args = tc["function"]["arguments"]
                    tool_start = time.time()

                    tool_result = _simulate_tool(tool_name, tool_args)

                    tool_span_id = str(uuid4())
                    tool_end = time.time()
                    tool_span = SpanCreate(
                        span_id=tool_span_id,
                        trace_id=trace_id,
                        parent_span_id=root_span_id,
                        span_type=SpanType.TOOL_USE,
                        name=tool_name,
                        status=SpanStatus.OK,
                        start_time=tool_start,
                        end_time=tool_end,
                        attributes={
                            "tool.name": tool_name,
                            "tool.input": tool_args,
                            "tool.output": tool_result,
                        },
                    )
                    await _broadcast_span(db, tool_span)

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": tool_result,
                        }
                    )

            elif scenario.provider == "anthropic":
                # Anthropic: append assistant content blocks, then user with tool_result blocks
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.raw_message.get("content", []),
                    }
                )
                tool_result_blocks: list[dict[str, Any]] = []
                for tc in response.tool_calls:
                    tool_name = tc["name"]
                    tool_args = json.dumps(tc.get("input", {}))
                    tool_start = time.time()

                    tool_result = _simulate_tool(tool_name, tool_args)

                    tool_span_id = str(uuid4())
                    tool_end = time.time()
                    tool_span = SpanCreate(
                        span_id=tool_span_id,
                        trace_id=trace_id,
                        parent_span_id=root_span_id,
                        span_type=SpanType.TOOL_USE,
                        name=tool_name,
                        status=SpanStatus.OK,
                        start_time=tool_start,
                        end_time=tool_end,
                        attributes={
                            "tool.name": tool_name,
                            "tool.input": tool_args,
                            "tool.output": tool_result,
                        },
                    )
                    await _broadcast_span(db, tool_span)

                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tc["id"],
                            "content": tool_result,
                        }
                    )

                messages.append(
                    {
                        "role": "user",
                        "content": tool_result_blocks,
                    }
                )

        # Close root span as OK
        root_end = SpanCreate(
            span_id=root_span_id,
            trace_id=trace_id,
            parent_span_id=None,
            span_type=SpanType.AGENT_STEP,
            name=scenario.name,
            status=SpanStatus.OK,
            start_time=start_time,
            end_time=time.time(),
            attributes={"demo": True, "demo.scenario": scenario.key},
        )
        await _broadcast_span(db, root_end)

    except Exception as exc:
        logger.exception("Demo agent %s failed", scenario.key)
        # Close root span as ERROR
        try:
            root_err = SpanCreate(
                span_id=root_span_id,
                trace_id=trace_id,
                parent_span_id=None,
                span_type=SpanType.AGENT_STEP,
                name=scenario.name,
                status=SpanStatus.ERROR,
                error_message=str(exc)[:200],
                start_time=start_time,
                end_time=time.time(),
                attributes={"demo": True, "demo.scenario": scenario.key},
            )
            await _broadcast_span(db, root_err)
        except Exception:
            logger.exception("Failed to close root span on error")
    finally:
        db.close()
