"""
Google Gemini agent example: simple question-answering agent.

Requires:
    pip install beacon-sdk google-genai

Usage:
    1. Set GEMINI_API_KEY environment variable
    2. Start the Beacon backend:  make dev
    3. Run this script:           python sdk/examples/google_agent.py
    4. Open http://localhost:5173 to see llm_call spans in the trace graph.
"""

from __future__ import annotations

import os

from google import genai

import beacon_sdk

beacon_sdk.init(auto_patch=True)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))

# Non-streaming call
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="What is the capital of France?",
)
print(f"Response: {response.text}")

# Streaming call
print("\nStreaming: ", end="")
for chunk in client.models.generate_content_stream(
    model="gemini-2.5-flash",
    contents="Tell me a short story about a robot in three sentences.",
):
    print(chunk.text, end="")
print()

beacon_sdk.flush()
print("\nDone! Check http://localhost:5173 to see the traces.")
