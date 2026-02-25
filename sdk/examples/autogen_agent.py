"""Example: AutoGen multi-agent conversation traced with Beacon.

Prerequisites:
    pip install pyautogen beacon-sdk

Usage:
    # Start the Beacon backend first:
    cd backend && uvicorn app.main:app --port 7474

    # Then run this example:
    python sdk/examples/autogen_agent.py

    # Open http://localhost:5173 to see the trace.
"""

import beacon_sdk

# Initialize Beacon — auto-patches AutoGen's ConversableAgent and GroupChat
beacon_sdk.init()

try:
    from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent
except ImportError:
    print("This example requires 'pyautogen'. Install with: pip install pyautogen")
    raise SystemExit(1)

import os

# Configure agents
config_list = [
    {
        "model": "gpt-4o-mini",
        "api_key": os.environ.get("OPENAI_API_KEY", "sk-..."),
    }
]

llm_config = {"config_list": config_list}

# Create agents
researcher = AssistantAgent(
    name="researcher",
    system_message="You are a research assistant. Find relevant information and provide concise summaries.",
    llm_config=llm_config,
)

writer = AssistantAgent(
    name="writer",
    system_message="You are a technical writer. Take research findings and write clear documentation.",
    llm_config=llm_config,
)

user_proxy = UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=2,
    code_execution_config=False,
)

# Create group chat
group_chat = GroupChat(
    agents=[user_proxy, researcher, writer],
    messages=[],
    max_round=4,
)

manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)

# Start the conversation — Beacon automatically traces all agent interactions
user_proxy.initiate_chat(
    manager,
    message="Research the key features of Python 3.13 and write a brief summary.",
)

# Flush spans to ensure they're all sent
beacon_sdk.flush()
print("Done! Check http://localhost:5173 for the trace.")
