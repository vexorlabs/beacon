"""LangChain agent with Beacon tracing.

Requires:
    pip install beacon-sdk langchain langchain-openai
    export OPENAI_API_KEY=...

Usage:
    1. Start Beacon: make dev
    2. Run: python sdk/examples/langchain_agent.py
    3. Open http://localhost:5173 to see the trace
"""

from __future__ import annotations

import beacon_sdk
from beacon_sdk.integrations.langchain import BeaconCallbackHandler

beacon_sdk.init()

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate


@tool
def search(query: str) -> str:
    """Search the web for information."""
    return f"Result for '{query}': Paris is the capital of France, population ~2.1 million."


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, [search], prompt)
executor = AgentExecutor(agent=agent, tools=[search])

# The only Beacon-specific line — pass the callback handler
result = executor.invoke(
    {"input": "What is the population of the capital of France?"},
    config={"callbacks": [BeaconCallbackHandler()]},
)

print(f"Result: {result['output']}")
print("Open http://localhost:5173 to see the trace!")
