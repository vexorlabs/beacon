"""Beacon Demo — Code Writer Agent

Simulates a coding agent that writes a CSV parser, runs tests, encounters
a failure, debugs, fixes, and re-tests. Uses Anthropic provider. No API keys needed.

Span tree produced:
    Code Writer Agent (agent_step)
      ├── understand_requirements (llm_call, anthropic/claude-sonnet-4-6)
      ├── write_code (llm_call, anthropic/claude-sonnet-4-6)
      ├── save_file (tool_use)
      ├── run_tests (shell_command)                ← ERROR
      ├── debug_failure (llm_call, anthropic/claude-sonnet-4-6)
      ├── apply_fix (tool_use)
      ├── run_tests_again (shell_command)           ← OK
      └── write_docs (llm_call, anthropic/claude-sonnet-4-6)

SDK patterns demonstrated:
    - @observe decorator for most spans
    - tracer.start_span() / end_span() for controlled error status
    - shell_command spans with stdout/stderr/returncode
    - Anthropic provider attributes
    - Error recovery (red node in graph, agent continues)
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
    temperature: float = 0.0,
    finish_reason: str = "end_turn",
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
    if cost_usd is not None:
        span.set_attribute("llm.cost_usd", cost_usd)
    else:
        # Rough estimate: $3/M input, $15/M output for claude-sonnet-4-6
        span.set_attribute(
            "llm.cost_usd",
            round(input_tokens * 3 / 1_000_000 + output_tokens * 15 / 1_000_000, 6),
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


@observe(name="understand_requirements", span_type="llm_call")
def understand_requirements(request: str) -> str:
    time.sleep(1.2)
    _set_llm_attrs(
        provider="anthropic",
        model="claude-sonnet-4-6",
        messages=[
            {"role": "system", "content": F.CODE_WRITER_SYSTEM_PROMPT},
            {"role": "user", "content": request},
        ],
        completion=F.CODE_WRITER_REQUIREMENTS_COMPLETION,
        input_tokens=128,
        output_tokens=95,
    )
    return F.CODE_WRITER_REQUIREMENTS_COMPLETION


@observe(name="write_code", span_type="llm_call")
def write_code(requirements: str) -> str:
    time.sleep(2.5)
    _set_llm_attrs(
        provider="anthropic",
        model="claude-sonnet-4-6",
        messages=[
            {"role": "system", "content": F.CODE_WRITER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Implement this:\n{requirements}"},
        ],
        completion=F.CODE_WRITER_INITIAL_CODE,
        input_tokens=245,
        output_tokens=312,
    )
    return F.CODE_WRITER_INITIAL_CODE


@observe(name="save_file", span_type="tool_use")
def save_file(code: str) -> str:
    time.sleep(0.2)
    _set_tool_attrs(
        name="write_file",
        tool_input=json.dumps({"path": "csv_parser.py", "content_length": len(code)}),
        tool_output=F.CODE_WRITER_SAVE_OUTPUT,
    )
    return F.CODE_WRITER_SAVE_OUTPUT


def run_shell_command(
    name: str,
    command: str,
    stdout: str,
    returncode: int,
    stderr: str = "",
) -> bool:
    """Run a simulated shell command. Returns True if successful.

    Uses tracer.start_span()/end_span() directly instead of @observe
    so we can set ERROR status without raising an exception that would
    kill the parent span.
    """
    tracer = beacon_sdk.get_tracer()
    if tracer is None:
        return returncode == 0

    span, token = tracer.start_span(name, span_type=SpanType.SHELL_COMMAND)
    time.sleep(1.5 if returncode != 0 else 1.2)
    span.set_attribute("shell.command", command)
    span.set_attribute("shell.returncode", returncode)
    span.set_attribute("shell.stdout", stdout)
    if stderr:
        span.set_attribute("shell.stderr", stderr)

    if returncode != 0:
        tracer.end_span(
            span, token,
            status=SpanStatus.ERROR,
            error_message=f"Command failed with exit code {returncode}",
        )
    else:
        tracer.end_span(span, token, status=SpanStatus.OK)

    return returncode == 0


@observe(name="debug_failure", span_type="llm_call")
def debug_failure(test_output: str) -> str:
    time.sleep(2.0)
    _set_llm_attrs(
        provider="anthropic",
        model="claude-sonnet-4-6",
        messages=[
            {"role": "system", "content": F.CODE_WRITER_SYSTEM_PROMPT},
            {"role": "user", "content": f"These tests failed. Debug the issue:\n\n{test_output}"},
        ],
        completion=F.CODE_WRITER_DEBUG_COMPLETION,
        input_tokens=687,
        output_tokens=198,
    )
    return F.CODE_WRITER_DEBUG_COMPLETION


@observe(name="apply_fix", span_type="tool_use")
def apply_fix(fix_description: str) -> str:
    time.sleep(0.2)
    _set_tool_attrs(
        name="edit_file",
        tool_input=json.dumps({"path": "csv_parser.py", "operation": "replace_line", "line": 5}),
        tool_output=F.CODE_WRITER_FIX_OUTPUT,
    )
    return F.CODE_WRITER_FIX_OUTPUT


@observe(name="write_docs", span_type="llm_call")
def write_docs(code: str) -> str:
    time.sleep(1.5)
    _set_llm_attrs(
        provider="anthropic",
        model="claude-sonnet-4-6",
        messages=[
            {"role": "system", "content": "Write concise module documentation for this code."},
            {"role": "user", "content": code},
        ],
        completion=F.CODE_WRITER_DOCS_COMPLETION,
        input_tokens=356,
        output_tokens=124,
    )
    return F.CODE_WRITER_DOCS_COMPLETION


@observe(name="Code Writer Agent", span_type="agent_step")
def _code_writer_agent() -> str:
    request = F.CODE_WRITER_USER_REQUEST
    requirements = understand_requirements(request)
    code = write_code(requirements)
    save_file(code)

    # First test run — fails
    passed = run_shell_command(
        name="run_tests",
        command="pytest test_csv_parser.py -v",
        stdout=F.CODE_WRITER_FAILING_TEST_OUTPUT,
        returncode=1,
    )

    if not passed:
        fix = debug_failure(F.CODE_WRITER_FAILING_TEST_OUTPUT)
        apply_fix(fix)

        # Second test run — passes
        run_shell_command(
            name="run_tests_retry",
            command="pytest test_csv_parser.py -v",
            stdout=F.CODE_WRITER_PASSING_TEST_OUTPUT,
            returncode=0,
        )

    docs = write_docs(code)
    return docs


def run() -> None:
    """Entry point for the orchestrator."""
    beacon_sdk.init(backend_url="http://localhost:7474", auto_patch=False)
    _code_writer_agent()


if __name__ == "__main__":
    run()
    print("Code Writer Agent demo complete.")
