"""Beacon Demo — Run all demo agents.

Runs 4 demo scenarios in sequence, each producing a trace in the Beacon UI.
No API keys required — all LLM responses are simulated.

Usage:
    # Start the backend first:
    make dev

    # Then run demos:
    make demo
    # or directly:
    python sdk/examples/demo/run_all.py
"""

from __future__ import annotations

import importlib
import os
import sys
import time

import requests

# Ensure sdk/examples is on the path so `demo.*` is importable
_EXAMPLES_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _EXAMPLES_DIR not in sys.path:
    sys.path.insert(0, _EXAMPLES_DIR)

BACKEND_URL = "http://localhost:7474"

SCENARIOS = [
    ("Research Agent", "demo.research_agent"),
    ("Code Writer Agent", "demo.code_writer_agent"),
    ("Web Scraper Agent", "demo.web_scraper_agent"),
    ("RAG Pipeline", "demo.rag_pipeline"),
]


def check_backend() -> bool:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def main() -> None:
    if not check_backend():
        print(f"ERROR: Backend not reachable at {BACKEND_URL}")
        print("Start it first with: make dev")
        sys.exit(1)

    print("Beacon Demo — 4 agent scenarios")
    print("Open http://localhost:5173 to watch traces appear live\n")

    for i, (label, module_path) in enumerate(SCENARIOS, 1):
        print(f"[{i}/{len(SCENARIOS)}] {label} ...", end=" ", flush=True)
        mod = importlib.import_module(module_path)
        mod.run()
        print("done")

        if i < len(SCENARIOS):
            time.sleep(2)

    print(f"\nAll demos complete. {len(SCENARIOS)} traces created.")
    print("View them at http://localhost:5173")


if __name__ == "__main__":
    main()
