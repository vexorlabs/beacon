"""Example: Ollama local model traced with Beacon.

Prerequisites:
    pip install ollama beacon-sdk
    # Ollama must be running locally: https://ollama.com

Usage:
    # Start the Beacon backend first:
    cd backend && uvicorn app.main:app --port 7474

    # Make sure Ollama is running and you've pulled a model:
    ollama pull llama3.2

    # Then run this example:
    python sdk/examples/ollama_agent.py

    # Open http://localhost:5173 to see the trace.

Note: Ollama with OpenAI-compatible API mode is also automatically traced
via the existing OpenAI auto-patch. This example uses the native Ollama client.
"""

import beacon_sdk

# Initialize Beacon — auto-patches ollama.chat() and ollama.generate()
beacon_sdk.init()

try:
    import ollama
except ImportError:
    print("This example requires 'ollama'. Install with: pip install ollama")
    raise SystemExit(1)

# Use ollama.chat — Beacon automatically creates an llm_call span
print("Calling ollama.chat...")
response = ollama.chat(
    model="llama3.2",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France? Answer in one sentence."},
    ],
)
print(f"Chat response: {response['message']['content']}")

# Use ollama.generate — Beacon automatically creates an llm_call span
print("\nCalling ollama.generate...")
response = ollama.generate(
    model="llama3.2",
    prompt="Write a haiku about debugging AI agents.",
)
print(f"Generate response: {response['response']}")

# Flush spans
beacon_sdk.flush()
print("\nDone! Check http://localhost:5173 for the traces.")
