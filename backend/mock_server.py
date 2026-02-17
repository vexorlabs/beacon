"""
Standalone mock server for frontend development.
Returns hardcoded JSON matching the Beacon API contract (docs/api-contracts.md).
Requires no dependencies beyond Python stdlib.

Usage:
    python backend/mock_server.py

Then run the frontend:
    cd frontend && npm run dev

The Vite proxy will forward /v1/* requests to this server on port 7474.
"""

from __future__ import annotations

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

# --- Mock Data ---

NOW = time.time()

TRACES: list[dict[str, Any]] = [
    {
        "trace_id": "trace-001",
        "name": "ReAct Agent: Search Query",
        "start_time": NOW - 120,
        "end_time": NOW - 115,
        "duration_ms": 5000,
        "span_count": 5,
        "status": "ok",
        "total_cost_usd": 0.0032,
        "total_tokens": 1250,
        "tags": {},
    },
    {
        "trace_id": "trace-002",
        "name": "Browser Agent: Form Fill",
        "start_time": NOW - 300,
        "end_time": NOW - 290,
        "duration_ms": 10000,
        "span_count": 8,
        "status": "ok",
        "total_cost_usd": 0.0051,
        "total_tokens": 2100,
        "tags": {},
    },
    {
        "trace_id": "trace-003",
        "name": "Code Agent: Fix Bug",
        "start_time": NOW - 600,
        "end_time": NOW - 595,
        "duration_ms": 5000,
        "span_count": 4,
        "status": "error",
        "total_cost_usd": 0.0018,
        "total_tokens": 800,
        "tags": {},
    },
]

SPANS: dict[str, list[dict[str, Any]]] = {
    "trace-001": [
        {
            "span_id": "span-001-root",
            "trace_id": "trace-001",
            "parent_span_id": None,
            "span_type": "chain",
            "name": "ReAct Agent",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 120,
            "end_time": NOW - 115,
            "attributes": {"chain.type": "react", "chain.input": "What is the capital of France?"},
        },
        {
            "span_id": "span-001-llm1",
            "trace_id": "trace-001",
            "parent_span_id": "span-001-root",
            "span_type": "llm_call",
            "name": "gpt-4o",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 120,
            "end_time": NOW - 119,
            "attributes": {
                "llm.provider": "openai",
                "llm.model": "gpt-4o",
                "llm.prompt": '[{"role":"user","content":"What is the capital of France?"}]',
                "llm.completion": "I need to search for this. Let me use the search tool.",
                "llm.tokens.input": 50,
                "llm.tokens.output": 30,
                "llm.tokens.total": 80,
                "llm.cost_usd": 0.0008,
            },
        },
        {
            "span_id": "span-001-tool1",
            "trace_id": "trace-001",
            "parent_span_id": "span-001-root",
            "span_type": "tool_use",
            "name": "search",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 119,
            "end_time": NOW - 117,
            "attributes": {
                "tool.name": "search",
                "tool.input": '{"query": "capital of France"}',
                "tool.output": '{"result": "Paris is the capital of France."}',
            },
        },
        {
            "span_id": "span-001-llm2",
            "trace_id": "trace-001",
            "parent_span_id": "span-001-root",
            "span_type": "llm_call",
            "name": "gpt-4o",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 117,
            "end_time": NOW - 116,
            "attributes": {
                "llm.provider": "openai",
                "llm.model": "gpt-4o",
                "llm.prompt": '[{"role":"user","content":"What is the capital of France?"},{"role":"assistant","content":"..."},{"role":"tool","content":"Paris is the capital of France."}]',
                "llm.completion": "The capital of France is Paris.",
                "llm.tokens.input": 120,
                "llm.tokens.output": 15,
                "llm.tokens.total": 135,
                "llm.cost_usd": 0.0012,
            },
        },
        {
            "span_id": "span-001-agent1",
            "trace_id": "trace-001",
            "parent_span_id": "span-001-root",
            "span_type": "agent_step",
            "name": "Final Answer",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 116,
            "end_time": NOW - 115,
            "attributes": {
                "agent.framework": "langchain",
                "agent.step_name": "Final Answer",
                "agent.output": "The capital of France is Paris.",
            },
        },
    ],
    "trace-002": [
        {
            "span_id": "span-002-root",
            "trace_id": "trace-002",
            "parent_span_id": None,
            "span_type": "chain",
            "name": "Browser Agent",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 300,
            "end_time": NOW - 290,
            "attributes": {"chain.type": "browser_agent"},
        },
        {
            "span_id": "span-002-llm1",
            "trace_id": "trace-002",
            "parent_span_id": "span-002-root",
            "span_type": "llm_call",
            "name": "claude-3.5-sonnet",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 300,
            "end_time": NOW - 299,
            "attributes": {
                "llm.provider": "anthropic",
                "llm.model": "claude-3.5-sonnet",
                "llm.prompt": '[{"role":"user","content":"Fill out the contact form"}]',
                "llm.completion": "I will navigate to the form and fill it out.",
                "llm.tokens.input": 80,
                "llm.tokens.output": 40,
                "llm.tokens.total": 120,
                "llm.cost_usd": 0.0015,
            },
        },
        {
            "span_id": "span-002-browser1",
            "trace_id": "trace-002",
            "parent_span_id": "span-002-root",
            "span_type": "browser_action",
            "name": "goto",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 298,
            "end_time": NOW - 296,
            "attributes": {
                "browser.action": "goto",
                "browser.url": "https://example.com/contact",
                "browser.page_title": "Contact Us",
            },
        },
        {
            "span_id": "span-002-browser2",
            "trace_id": "trace-002",
            "parent_span_id": "span-002-root",
            "span_type": "browser_action",
            "name": "fill",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 296,
            "end_time": NOW - 295,
            "attributes": {
                "browser.action": "fill",
                "browser.selector": "#name",
                "browser.value": "John Doe",
            },
        },
        {
            "span_id": "span-002-browser3",
            "trace_id": "trace-002",
            "parent_span_id": "span-002-root",
            "span_type": "browser_action",
            "name": "fill",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 295,
            "end_time": NOW - 294,
            "attributes": {
                "browser.action": "fill",
                "browser.selector": "#email",
                "browser.value": "john@example.com",
            },
        },
        {
            "span_id": "span-002-browser4",
            "trace_id": "trace-002",
            "parent_span_id": "span-002-root",
            "span_type": "browser_action",
            "name": "click",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 294,
            "end_time": NOW - 293,
            "attributes": {
                "browser.action": "click",
                "browser.selector": "#submit-btn",
            },
        },
        {
            "span_id": "span-002-llm2",
            "trace_id": "trace-002",
            "parent_span_id": "span-002-root",
            "span_type": "llm_call",
            "name": "claude-3.5-sonnet",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 293,
            "end_time": NOW - 291,
            "attributes": {
                "llm.provider": "anthropic",
                "llm.model": "claude-3.5-sonnet",
                "llm.prompt": '[{"role":"user","content":"..."}]',
                "llm.completion": "The form has been submitted successfully.",
                "llm.tokens.input": 200,
                "llm.tokens.output": 25,
                "llm.tokens.total": 225,
                "llm.cost_usd": 0.0020,
            },
        },
        {
            "span_id": "span-002-agent1",
            "trace_id": "trace-002",
            "parent_span_id": "span-002-root",
            "span_type": "agent_step",
            "name": "Complete",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 291,
            "end_time": NOW - 290,
            "attributes": {
                "agent.framework": "custom",
                "agent.output": "Form submitted successfully.",
            },
        },
    ],
    "trace-003": [
        {
            "span_id": "span-003-root",
            "trace_id": "trace-003",
            "parent_span_id": None,
            "span_type": "chain",
            "name": "Code Agent",
            "status": "error",
            "error_message": "File not found: /src/utils.py",
            "start_time": NOW - 600,
            "end_time": NOW - 595,
            "attributes": {"chain.type": "code_agent"},
        },
        {
            "span_id": "span-003-llm1",
            "trace_id": "trace-003",
            "parent_span_id": "span-003-root",
            "span_type": "llm_call",
            "name": "gpt-4o",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 600,
            "end_time": NOW - 599,
            "attributes": {
                "llm.provider": "openai",
                "llm.model": "gpt-4o",
                "llm.prompt": '[{"role":"user","content":"Fix the bug in utils.py"}]',
                "llm.completion": "I will read the file first.",
                "llm.tokens.input": 60,
                "llm.tokens.output": 20,
                "llm.tokens.total": 80,
                "llm.cost_usd": 0.0008,
            },
        },
        {
            "span_id": "span-003-file1",
            "trace_id": "trace-003",
            "parent_span_id": "span-003-root",
            "span_type": "file_operation",
            "name": "read /src/utils.py",
            "status": "error",
            "error_message": "FileNotFoundError: /src/utils.py",
            "start_time": NOW - 598,
            "end_time": NOW - 598,
            "attributes": {
                "file.operation": "read",
                "file.path": "/src/utils.py",
            },
        },
        {
            "span_id": "span-003-shell1",
            "trace_id": "trace-003",
            "parent_span_id": "span-003-root",
            "span_type": "shell_command",
            "name": "find . -name utils.py",
            "status": "ok",
            "error_message": None,
            "start_time": NOW - 597,
            "end_time": NOW - 596,
            "attributes": {
                "shell.command": "find",
                "shell.args": '. -name "utils.py"',
                "shell.exit_code": 0,
                "shell.stdout": "./lib/utils.py\n./tests/test_utils.py",
                "shell.cwd": "/home/user/project",
            },
        },
    ],
}

# Build flat span lookup
ALL_SPANS: dict[str, dict[str, Any]] = {}
for trace_spans in SPANS.values():
    for span in trace_spans:
        ALL_SPANS[span["span_id"]] = span


def build_graph(trace_id: str) -> dict[str, Any]:
    """Build React Flow nodes + edges from spans."""
    spans = SPANS.get(trace_id, [])
    nodes = []
    edges = []
    for span in spans:
        start = span.get("start_time", 0)
        end = span.get("end_time")
        duration_ms = (end - start) * 1000 if end is not None else None
        cost = span.get("attributes", {}).get("llm.cost_usd")
        nodes.append({
            "id": span["span_id"],
            "type": "spanNode",
            "data": {
                "span_id": span["span_id"],
                "span_type": span["span_type"],
                "name": span["name"],
                "status": span["status"],
                "duration_ms": duration_ms,
                "cost_usd": cost,
            },
            "position": {"x": 0, "y": 0},
        })
        if span["parent_span_id"]:
            edges.append({
                "id": f"edge-{span['parent_span_id']}-{span['span_id']}",
                "source": span["parent_span_id"],
                "target": span["span_id"],
            })
    return {"nodes": nodes, "edges": edges}


class MockHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.split("?")[0]

        if path == "/health":
            self._json_response({"status": "ok", "version": "0.1.0", "db_path": "mock"})
            return

        if path == "/v1/traces":
            self._json_response({
                "traces": TRACES,
                "total": len(TRACES),
                "limit": 50,
                "offset": 0,
            })
            return

        if path.startswith("/v1/traces/") and path.endswith("/graph"):
            trace_id = path.split("/")[3]
            graph = build_graph(trace_id)
            if graph["nodes"]:
                self._json_response(graph)
            else:
                self._error_response(404, "Trace not found")
            return

        if path.startswith("/v1/traces/"):
            trace_id = path.split("/")[3]
            trace = next((t for t in TRACES if t["trace_id"] == trace_id), None)
            if trace:
                self._json_response({**trace, "spans": SPANS.get(trace_id, [])})
            else:
                self._error_response(404, "Trace not found")
            return

        if path.startswith("/v1/spans/"):
            span_id = path.split("/")[3]
            span = ALL_SPANS.get(span_id)
            if span:
                self._json_response(span)
            else:
                self._error_response(404, "Span not found")
            return

        self._error_response(404, "Not found")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _json_response(self, data: Any) -> None:
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _error_response(self, code: int, detail: str) -> None:
        body = json.dumps({"detail": detail}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "http://localhost:5173")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format: str, *args: Any) -> None:
        # Shorter log format
        print(f"[mock] {args[0]}" if args else "")


def main() -> None:
    port = 7474
    server = HTTPServer(("localhost", port), MockHandler)
    print(f"Mock server running at http://localhost:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down")
        server.server_close()


if __name__ == "__main__":
    main()
