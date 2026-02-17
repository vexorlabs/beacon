"""Beacon SDK Phase 1 validation script.

Run with the backend running:
    cd backend && source .venv/bin/activate && uvicorn app.main:app --port 7474

Then:
    cd sdk && source .venv/bin/activate && python examples/hello_world.py

Expected: a trace with 3 spans appears in ~/.beacon/traces.db
"""

import beacon_sdk
from beacon_sdk import observe

beacon_sdk.init(backend_url="http://localhost:7474")


@observe(name="fetch_data", span_type="tool_use")
def fetch_data(query: str) -> str:
    """Simulates fetching data."""
    return f"Results for: {query}"


@observe(name="process_results", span_type="agent_step")
def process_results(data: str) -> str:
    """Simulates processing fetched data."""
    return f"Processed: {data}"


@observe(name="run_agent")
def run_agent(question: str) -> str:
    """Top-level agent function. Creates the root span."""
    data = fetch_data(question)
    result = process_results(data)
    return result


if __name__ == "__main__":
    answer = run_agent("What is the capital of France?")
    print(f"Agent answer: {answer}")
    print("Check ~/.beacon/traces.db for the trace!")
