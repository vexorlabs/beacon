from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import httpx


def _make_span(**overrides: object) -> dict[str, object]:
    """Build a valid span dict with sensible defaults."""
    defaults: dict[str, object] = {
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


def _make_llm_span(**overrides: object) -> dict[str, object]:
    """Build an llm_call span with OpenAI provider attributes."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]
    attrs: dict[str, object] = {
        "llm.provider": "openai",
        "llm.model": "gpt-4o",
        "llm.prompt": json.dumps(messages),
        "llm.temperature": 0.7,
        "llm.max_tokens": 100,
        "llm.completion": "Hi there! How can I help you?",
        "llm.tokens.total": 50,
        "llm.cost_usd": 0.001,
    }
    extra_attrs = overrides.pop("attributes", {}) if "attributes" in overrides else {}
    assert isinstance(extra_attrs, dict)
    attrs.update(extra_attrs)
    return _make_span(span_type="llm_call", attributes=attrs, **overrides)


def _make_anthropic_llm_span(**overrides: object) -> dict[str, object]:
    """Build an llm_call span with Anthropic provider attributes."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]
    attrs: dict[str, object] = {
        "llm.provider": "anthropic",
        "llm.model": "claude-3-5-sonnet-20241022",
        "llm.prompt": json.dumps(messages),
        "llm.temperature": 0.7,
        "llm.max_tokens": 100,
        "llm.completion": "Hi there! How can I help you?",
        "llm.tokens.total": 50,
        "llm.cost_usd": 0.001,
    }
    extra_attrs = overrides.pop("attributes", {}) if "attributes" in overrides else {}
    assert isinstance(extra_attrs, dict)
    attrs.update(extra_attrs)
    return _make_span(span_type="llm_call", attributes=attrs, **overrides)


def _mock_openai_response(
    content: str = "New response from OpenAI",
) -> httpx.Response:
    """Create a mock httpx.Response matching OpenAI chat completions format."""
    return httpx.Response(
        status_code=200,
        json={
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "total_tokens": 30,
            },
        },
        request=httpx.Request(
            "POST", "https://api.openai.com/v1/chat/completions"
        ),
    )


def test_replay_nonexistent_span_returns_400(client) -> None:
    """POST replay with a random span_id that does not exist should return 400."""
    response = client.post(
        "/v1/replay",
        json={
            "span_id": str(uuid.uuid4()),
            "modified_attributes": {},
        },
    )
    assert response.status_code == 400
    assert "Span not found" in response.json()["detail"]


def test_replay_non_llm_span_returns_400(client) -> None:
    """Replaying a tool_use span should return 400."""
    span = _make_span(span_type="tool_use")
    client.post("/v1/spans", json={"spans": [span]})

    response = client.post(
        "/v1/replay",
        json={
            "span_id": span["span_id"],
            "modified_attributes": {},
        },
    )
    assert response.status_code == 400
    assert "llm_call" in response.json()["detail"]


@patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
def test_replay_llm_call_success(mock_post: AsyncMock, client) -> None:
    """Replay an llm_call span with mocked OpenAI response."""
    mock_post.return_value = _mock_openai_response("New response from OpenAI")

    span = _make_llm_span()
    client.post("/v1/spans", json={"spans": [span]})

    response = client.post(
        "/v1/replay",
        json={
            "span_id": span["span_id"],
            "modified_attributes": {"llm.temperature": 0.0},
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert "replay_id" in data
    assert data["original_span_id"] == span["span_id"]
    assert data["new_output"]["llm.completion"] == "New response from OpenAI"
    assert data["new_output"]["llm.tokens.input"] == 20
    assert data["new_output"]["llm.tokens.output"] == 10
    assert "llm.cost_usd" in data["new_output"]

    assert data["diff"]["old_completion"] == "Hi there! How can I help you?"
    assert data["diff"]["new_completion"] == "New response from OpenAI"
    assert data["diff"]["changed"] is True


@patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
def test_replay_stores_in_db(
    mock_post: AsyncMock, client, db_session
) -> None:
    """After a successful replay, verify a row exists in replay_runs table."""
    mock_post.return_value = _mock_openai_response()

    span = _make_llm_span()
    client.post("/v1/spans", json={"spans": [span]})

    response = client.post(
        "/v1/replay",
        json={
            "span_id": span["span_id"],
            "modified_attributes": {"llm.temperature": 0.5},
        },
    )
    assert response.status_code == 200
    replay_id = response.json()["replay_id"]

    from app.models import ReplayRun

    replay_run = db_session.get(ReplayRun, replay_id)
    assert replay_run is not None
    assert replay_run.original_span_id == span["span_id"]
    assert replay_run.trace_id == span["trace_id"]

    stored_output = json.loads(replay_run.new_output)
    assert "llm.completion" in stored_output
    stored_diff = json.loads(replay_run.diff)
    assert "old_completion" in stored_diff
    assert "new_completion" in stored_diff
    assert "changed" in stored_diff


def _mock_anthropic_response(
    content: str = "New response from Anthropic",
) -> httpx.Response:
    """Create a mock httpx.Response matching Anthropic messages format."""
    return httpx.Response(
        status_code=200,
        json={
            "content": [{"type": "text", "text": content}],
            "usage": {
                "input_tokens": 15,
                "output_tokens": 8,
            },
        },
        request=httpx.Request(
            "POST", "https://api.anthropic.com/v1/messages"
        ),
    )


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
def test_replay_anthropic_provider(mock_post: AsyncMock, client) -> None:
    """Replay an Anthropic llm_call span with mocked response.

    Verifies system message extraction: the system message should be passed
    as a top-level 'system' field, not in the messages array.
    """
    mock_post.return_value = _mock_anthropic_response("New response from Anthropic")

    span = _make_anthropic_llm_span()
    client.post("/v1/spans", json={"spans": [span]})

    response = client.post(
        "/v1/replay",
        json={
            "span_id": span["span_id"],
            "modified_attributes": {"llm.temperature": 0.0},
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["original_span_id"] == span["span_id"]
    assert data["new_output"]["llm.completion"] == "New response from Anthropic"
    assert data["new_output"]["llm.tokens.input"] == 15
    assert data["new_output"]["llm.tokens.output"] == 8
    assert "llm.cost_usd" in data["new_output"]
    assert data["diff"]["changed"] is True

    # Verify the mock was called with Anthropic API URL
    call_args = mock_post.call_args
    assert "anthropic.com" in str(call_args)
