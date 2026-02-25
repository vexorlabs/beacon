"""Example: LlamaIndex RAG pipeline traced with Beacon.

Prerequisites:
    pip install llama-index beacon-sdk

Usage:
    # Start the Beacon backend first:
    cd backend && uvicorn app.main:app --port 7474

    # Then run this example:
    python sdk/examples/llamaindex_agent.py

    # Open http://localhost:5173 to see the trace.
"""

import beacon_sdk

# Initialize Beacon — auto-patches LlamaIndex's query engine and retriever
beacon_sdk.init()

try:
    from llama_index.core import Document, Settings, VectorStoreIndex
    from llama_index.llms.openai import OpenAI
except ImportError:
    print(
        "This example requires 'llama-index'. Install with:\n"
        "  pip install llama-index llama-index-llms-openai"
    )
    raise SystemExit(1)

# Configure the LLM
Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)

# Create some sample documents
documents = [
    Document(text="Beacon is an open-source debugging platform for AI agents. It provides Chrome DevTools-like inspection for agent traces, including LLM calls, tool usage, and execution flow."),
    Document(text="Beacon supports Python and JavaScript SDKs. The Python SDK auto-patches OpenAI, Anthropic, Google Gemini, LangChain, CrewAI, AutoGen, and LlamaIndex."),
    Document(text="The Beacon UI features a trace graph view, timeline/waterfall view, prompt editor with replay, and AI-powered analysis including root cause analysis and cost optimization."),
]

# Build an in-memory index
index = VectorStoreIndex.from_documents(documents)

# Create a query engine
query_engine = index.as_query_engine()

# Run a query — Beacon automatically traces the query and retrieval
response = query_engine.query("What AI frameworks does Beacon support?")
print(f"Response: {response}")

# Run another query
response2 = query_engine.query("What debugging features does Beacon provide?")
print(f"Response: {response2}")

# Flush spans
beacon_sdk.flush()
print("\nDone! Check http://localhost:5173 for the traces.")
