from __future__ import annotations

from beacon_sdk.models import (
    SCREENSHOT_MAX_BYTES,
    TRUNCATION_LIMITS,
    Span,
    SpanStatus,
    SpanType,
)


def test_span_default_values_are_set_correctly():
    span = Span()
    assert span.span_id  # non-empty UUID
    assert span.start_time > 0
    assert span.end_time is None
    assert span.status == SpanStatus.UNSET
    assert span.attributes == {}


def test_span_to_dict_matches_api_contract():
    span = Span(
        trace_id="trace-1",
        name="test",
        span_type=SpanType.LLM_CALL,
        status=SpanStatus.OK,
    )
    d = span.to_dict()
    assert d["span_id"] == span.span_id
    assert d["trace_id"] == "trace-1"
    assert d["span_type"] == "llm_call"
    assert d["status"] == "ok"
    assert d["parent_span_id"] is None
    assert d["error_message"] is None
    assert isinstance(d["attributes"], dict)


def test_span_end_sets_end_time_and_status():
    span = Span()
    span.end()
    assert span.end_time is not None
    assert span.status == SpanStatus.OK


def test_span_end_with_error_sets_error_message():
    span = Span()
    span.end(status=SpanStatus.ERROR, error_message="boom")
    assert span.status == SpanStatus.ERROR
    assert span.error_message == "boom"


def test_set_attribute_truncates_long_prompt():
    span = Span()
    long_text = "x" * (TRUNCATION_LIMITS["llm.prompt"] + 100)
    span.set_attribute("llm.prompt", long_text)
    assert span.attributes["llm.prompt"].endswith("[TRUNCATED]")
    assert len(span.attributes["llm.prompt"]) == TRUNCATION_LIMITS["llm.prompt"] + len(
        "[TRUNCATED]"
    )


def test_set_attribute_does_not_truncate_short_text():
    span = Span()
    span.set_attribute("llm.prompt", "short")
    assert span.attributes["llm.prompt"] == "short"


def test_set_attribute_drops_oversized_screenshot():
    span = Span()
    big_screenshot = "x" * (SCREENSHOT_MAX_BYTES + 1)
    span.set_attribute("browser.screenshot", big_screenshot)
    assert span.attributes["browser.screenshot"] is None


def test_span_type_enum_values_match_spec():
    expected = {
        "llm_call",
        "tool_use",
        "agent_step",
        "browser_action",
        "file_operation",
        "shell_command",
        "chain",
        "custom",
    }
    actual = {t.value for t in SpanType}
    assert actual == expected


def test_span_status_enum_values_match_spec():
    expected = {"ok", "error", "unset"}
    actual = {s.value for s in SpanStatus}
    assert actual == expected
