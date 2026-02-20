from __future__ import annotations

import uuid


def _make_span(**overrides):
    """Build a valid span dict with sensible defaults."""
    defaults = {
        "span_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "parent_span_id": None,
        "span_type": "custom",
        "name": "test-span",
        "status": "ok",
        "error_message": None,
        "start_time": 1700000000.0,
        "end_time": 1700000001.0,
        "attributes": {},
    }
    defaults.update(overrides)
    return defaults


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "db_path" in data


def test_ingest_single_span_returns_accepted_one(client):
    span = _make_span()
    response = client.post("/v1/spans", json={"spans": [span]})
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 1
    assert data["rejected"] == 0


def test_ingest_span_creates_trace_row(client, db_session):
    trace_id = str(uuid.uuid4())
    span = _make_span(trace_id=trace_id)
    client.post("/v1/spans", json={"spans": [span]})

    from app.models import Trace

    trace = db_session.get(Trace, trace_id)
    assert trace is not None
    assert trace.trace_id == trace_id


def test_ingest_span_sets_trace_name_from_first_span(client, db_session):
    trace_id = str(uuid.uuid4())
    span = _make_span(trace_id=trace_id, name="my-agent")
    client.post("/v1/spans", json={"spans": [span]})

    from app.models import Trace

    trace = db_session.get(Trace, trace_id)
    assert trace.name == "my-agent"


def test_ingest_multiple_spans_same_trace_increments_span_count(
    client, db_session
):
    trace_id = str(uuid.uuid4())
    span1 = _make_span(trace_id=trace_id)
    span2 = _make_span(trace_id=trace_id)
    client.post("/v1/spans", json={"spans": [span1]})
    client.post("/v1/spans", json={"spans": [span2]})

    from app.models import Trace

    trace = db_session.get(Trace, trace_id)
    assert trace.span_count == 2


def test_ingest_span_updates_trace_end_time(client, db_session):
    trace_id = str(uuid.uuid4())
    span1 = _make_span(
        trace_id=trace_id, start_time=1700000000.0, end_time=1700000001.0
    )
    span2 = _make_span(
        trace_id=trace_id, start_time=1700000002.0, end_time=1700000005.0
    )
    client.post("/v1/spans", json={"spans": [span1]})
    client.post("/v1/spans", json={"spans": [span2]})

    from app.models import Trace

    trace = db_session.get(Trace, trace_id)
    assert trace.end_time == 1700000005.0
    assert trace.start_time == 1700000000.0


def test_ingest_llm_call_span_updates_trace_cost_and_tokens(
    client, db_session
):
    trace_id = str(uuid.uuid4())
    span = _make_span(
        trace_id=trace_id,
        span_type="llm_call",
        attributes={
            "llm.cost_usd": 0.05,
            "llm.tokens.total": 1000,
        },
    )
    client.post("/v1/spans", json={"spans": [span]})

    from app.models import Trace

    trace = db_session.get(Trace, trace_id)
    assert trace.total_cost_usd == 0.05
    assert trace.total_tokens == 1000


def test_ingest_span_with_missing_required_field_returns_422(client):
    bad_span = {"trace_id": str(uuid.uuid4()), "name": "missing-fields"}
    response = client.post("/v1/spans", json={"spans": [bad_span]})
    assert response.status_code == 422


def test_ingest_span_with_invalid_span_type_returns_422(client):
    span = _make_span(span_type="not_a_real_type")
    response = client.post("/v1/spans", json={"spans": [span]})
    assert response.status_code == 422


def test_ingest_duplicate_span_id_updates_existing(client, db_session):
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    span_v1 = _make_span(
        span_id=span_id,
        trace_id=trace_id,
        status="unset",
        end_time=None,
    )
    span_v2 = _make_span(
        span_id=span_id,
        trace_id=trace_id,
        status="ok",
        end_time=1700000002.0,
    )
    client.post("/v1/spans", json={"spans": [span_v1]})
    client.post("/v1/spans", json={"spans": [span_v2]})

    from app.models import Span

    span = db_session.get(Span, span_id)
    assert span.status == "ok"
    assert span.end_time == 1700000002.0


def test_ingest_batch_of_spans_returns_correct_count(client):
    trace_id = str(uuid.uuid4())
    spans = [_make_span(trace_id=trace_id) for _ in range(5)]
    response = client.post("/v1/spans", json={"spans": spans})
    data = response.json()
    assert data["accepted"] == 5


def test_get_span_by_id_returns_span(client):
    span_id = str(uuid.uuid4())
    span = _make_span(span_id=span_id)
    client.post("/v1/spans", json={"spans": [span]})

    response = client.get(f"/v1/spans/{span_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["span_id"] == span_id
    assert data["name"] == "test-span"
    assert data["duration_ms"] is not None


def test_get_span_by_id_not_found_returns_404(client):
    response = client.get(f"/v1/spans/{uuid.uuid4()}")
    assert response.status_code == 404


def test_ingest_error_span_sets_trace_status_to_error(client, db_session):
    trace_id = str(uuid.uuid4())
    span1 = _make_span(trace_id=trace_id, status="ok")
    span2 = _make_span(trace_id=trace_id, status="error")
    client.post("/v1/spans", json={"spans": [span1]})
    client.post("/v1/spans", json={"spans": [span2]})

    from app.models import Trace

    trace = db_session.get(Trace, trace_id)
    assert trace.status == "error"


def test_ingest_span_with_sdk_language_persists_on_span_and_trace(
    client, db_session
):
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    span = _make_span(
        span_id=span_id, trace_id=trace_id, sdk_language="python"
    )
    response = client.post("/v1/spans", json={"spans": [span]})
    assert response.status_code == 200

    from app.models import Span, Trace

    db_span = db_session.get(Span, span_id)
    assert db_span.sdk_language == "python"

    trace = db_session.get(Trace, trace_id)
    assert trace.sdk_language == "python"


def test_get_span_returns_sdk_language(client):
    span_id = str(uuid.uuid4())
    span = _make_span(span_id=span_id, sdk_language="javascript")
    client.post("/v1/spans", json={"spans": [span]})

    response = client.get(f"/v1/spans/{span_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["sdk_language"] == "javascript"


def test_sdk_language_defaults_to_none(client):
    span_id = str(uuid.uuid4())
    span = _make_span(span_id=span_id)
    client.post("/v1/spans", json={"spans": [span]})

    response = client.get(f"/v1/spans/{span_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["sdk_language"] is None
