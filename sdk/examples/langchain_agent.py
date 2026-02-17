"""Example: LangChain ReAct agent with Beacon instrumentation.

Prerequisites:
    pip install beacon-sdk[langchain] langchain langchain-openai
    export OPENAI_API_KEY=...

Usage:
    1. Start the Beacon backend:  cd backend && uvicorn app.main:app --port 7474
    2. Start the Beacon frontend: cd frontend && npm run dev
    3. Run this script:            python sdk/examples/langchain_agent.py
    4. Open http://localhost:5173 to see the trace
"""

from __future__ import annotations

import beacon_sdk
from beacon_sdk.integrations.langchain import BeaconCallbackHandler

# Initialize Beacon SDK (connects to backend at localhost:7474)
beacon_sdk.init()

# LangChain imports
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate


@tool
def search(query: str) -> str:
    """Search the web for information."""
    # Mock search result for demo purposes
    return f"Search result for '{query}': Paris is the capital of France. It has a population of about 2.1 million."


@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    # Simple eval for demo (do not use in production)
    try:
        result = eval(expression)  # noqa: S307
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def main() -> None:
    # Create the Beacon callback handler
    beacon_handler = BeaconCallbackHandler()

    # Set up the LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Define the ReAct prompt
    prompt = PromptTemplate.from_template(
        """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
    )

    # Create the agent
    tools = [search, calculator]
    agent = create_react_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
    )

    # Run with Beacon callback handler
    result = executor.invoke(
        {"input": "What is the population of the capital of France?"},
        config={"callbacks": [beacon_handler]},
    )

    print(f"\nResult: {result['output']}")
    print("\nOpen http://localhost:5173 to see the trace in Beacon!")


if __name__ == "__main__":
    main()
