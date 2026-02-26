"""Convert OTLP JSON trace payloads to Beacon SpanCreate objects."""

from __future__ import annotations

from typing import Any

from app.schemas import SpanCreate, SpanStatus, SpanType

# OTEL status codes: 0=UNSET, 1=OK, 2=ERROR
_OTEL_STATUS_MAP = {
    0: SpanStatus.UNSET,
    1: SpanStatus.OK,
    2: SpanStatus.ERROR,
}

# Valid span types that we recognise
_VALID_SPAN_TYPES = {e.value for e in SpanType}


def convert_otlp_to_spans(payload: dict[str, Any]) -> list[SpanCreate]:
    """Parse an OTLP JSON payload and return a list of SpanCreate objects.

    Expects the standard OTLP structure:
    { resourceSpans: [{ scopeSpans: [{ spans: [...] }] }] }
    """
    spans: list[SpanCreate] = []

    for resource_span in payload.get("resourceSpans", []):
        for scope_span in resource_span.get("scopeSpans", []):
            for otel_span in scope_span.get("spans", []):
                span_id = otel_span.get("spanId", "")
                trace_id = otel_span.get("traceId", "")
                if not span_id or not trace_id:
                    continue
                spans.append(_convert_span(otel_span))

    return spans


def _convert_span(otel_span: dict[str, Any]) -> SpanCreate:
    """Convert a single OTEL span dict to a SpanCreate."""
    # Timestamps: OTEL uses nanoseconds (as strings), we use epoch seconds (float)
    start_ns = int(otel_span.get("startTimeUnixNano", "0"))
    end_ns = int(otel_span.get("endTimeUnixNano", "0"))
    start_time = start_ns / 1_000_000_000
    end_time = end_ns / 1_000_000_000 if end_ns > 0 else None

    # Flatten OTEL attributes
    attributes = _flatten_attributes(otel_span.get("attributes", []))

    # Extract span_type from attributes, default to custom
    raw_span_type = attributes.pop("span_type", "custom")
    span_type = raw_span_type if raw_span_type in _VALID_SPAN_TYPES else "custom"

    # Extract error message from attributes
    error_message = attributes.pop("error.message", None)

    # OTEL status
    otel_status = otel_span.get("status", {})
    status_code = otel_status.get("code", 0)
    status = _OTEL_STATUS_MAP.get(status_code, SpanStatus.UNSET)

    # If status is error and we have a status message, use it as error_message
    if status == SpanStatus.ERROR and not error_message:
        error_message = otel_status.get("message")

    return SpanCreate(
        span_id=otel_span.get("spanId", ""),
        trace_id=otel_span.get("traceId", ""),
        parent_span_id=otel_span.get("parentSpanId") or None,
        span_type=SpanType(span_type),
        name=otel_span.get("name", "unknown"),
        status=status,
        error_message=error_message,
        start_time=start_time,
        end_time=end_time,
        attributes=attributes,
    )


def _flatten_attributes(
    otel_attrs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Convert OTEL attribute format to a flat dict.

    OTEL attributes look like:
    [{"key": "foo", "value": {"stringValue": "bar"}}]
    """
    result: dict[str, Any] = {}
    for attr in otel_attrs:
        key = attr.get("key", "")
        value_obj = attr.get("value", {})
        result[key] = _extract_value(value_obj)
    return result


def _extract_value(value_obj: dict[str, Any]) -> Any:
    """Extract the typed value from an OTEL attribute value object."""
    if "stringValue" in value_obj:
        return value_obj["stringValue"]
    if "intValue" in value_obj:
        return int(value_obj["intValue"])
    if "doubleValue" in value_obj:
        return float(value_obj["doubleValue"])
    if "boolValue" in value_obj:
        return bool(value_obj["boolValue"])
    if "arrayValue" in value_obj:
        return [_extract_value(v) for v in value_obj["arrayValue"].get("values", [])]
    return str(value_obj)
