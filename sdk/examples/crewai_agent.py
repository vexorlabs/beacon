"""CrewAI agent with Beacon tracing (zero configuration).

Requires:
    pip install beacon-sdk crewai crewai-tools
    export OPENAI_API_KEY=...

Usage:
    1. Start Beacon: make dev
    2. Run: python sdk/examples/crewai_agent.py
    3. Open http://localhost:5173 to see the trace
"""

from __future__ import annotations

import beacon_sdk

# Init BEFORE importing crewai so the auto-patch applies
beacon_sdk.init()

from crewai import Agent, Crew, Process, Task  # noqa: E402

researcher = Agent(
    role="Senior Researcher",
    goal="Uncover cutting-edge developments in AI",
    backstory="You are an expert researcher at a leading tech think tank.",
    verbose=True,
)

writer = Agent(
    role="Tech Writer",
    goal="Write compelling technical content",
    backstory="You are a renowned content strategist and tech writer.",
    verbose=True,
)

research_task = Task(
    description="Research the latest advancements in AI agents in 2025.",
    expected_output="A detailed summary of the top 3 AI agent frameworks.",
    agent=researcher,
)

write_task = Task(
    description="Write a short blog post about AI agent frameworks based on the research.",
    expected_output="A 3-paragraph blog post.",
    agent=writer,
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process=Process.sequential,
    verbose=True,
)

result = crew.kickoff(inputs={"topic": "AI Agents in 2025"})

print(f"\nResult:\n{result.raw}")
beacon_sdk.flush()
print("\nOpen http://localhost:5173 to see the trace!")
