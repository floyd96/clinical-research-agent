import asyncio
import os
import threading

from dotenv import load_dotenv
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from config import (
    CLINICALTRIALS_MCP_URL, PUBMED_MCP_URL,
    MODEL_ID, MAIN_MAX_TOKENS, CLASSIFIER_MAX_TOKENS,
)
from prompts import SYSTEM_PROMPT

load_dotenv()

# ── LLM endpoints ─────────────────────────────────────────────────────────────

_llm = HuggingFaceEndpoint(
    repo_id=MODEL_ID,
    task="text-generation",
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
    max_new_tokens=MAIN_MAX_TOKENS,
)
model = ChatHuggingFace(llm=_llm)

# Separate endpoint capped at CLASSIFIER_MAX_TOKENS — one-word output only.
_classifier_llm = HuggingFaceEndpoint(
    repo_id=MODEL_ID,
    task="text-generation",
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
    max_new_tokens=CLASSIFIER_MAX_TOKENS,
)
classifier_model = ChatHuggingFace(llm=_classifier_llm)

# ── Persistent async event loop (shared across Streamlit reruns) ──────────────

_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()


def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()


# ── CLI runner ────────────────────────────────────────────────────────────────

async def _run_cli(user_input: str, agent) -> None:
    result = await agent.ainvoke({"messages": [HumanMessage(content=user_input)]})
    for msg in result["messages"][1:]:
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                for call in msg.tool_calls:
                    print(f"  [tool call] {call['name']}({call['args']})")
            elif msg.content:
                print(f"Agent: {msg.content}")
        elif isinstance(msg, ToolMessage):
            print(f"  [tool result] {msg.name} → {msg.content[:300]}")
    print()


async def main() -> None:
    client = MultiServerMCPClient(
        {
            "clinicaltrials": {"url": CLINICALTRIALS_MCP_URL, "transport": "streamable_http"},
            "pubmed":          {"url": PUBMED_MCP_URL,         "transport": "streamable_http"},
        }
    )
    mcp_tools = await client.get_tools()
    agent = create_agent(model, mcp_tools, system_prompt=SYSTEM_PROMPT)

    ct_tools = [t.name for t in mcp_tools if "clinical" in t.name.lower() or "trial" in t.name.lower()]
    pm_tools = [t.name for t in mcp_tools if t.name not in ct_tools]
    print(f"{CLINICALTRIALS_MCP_URL.split('/')[2]} — Clinical Research Intelligence Agent\n")
    print(f"ClinicalTrials tools : {ct_tools}")
    print(f"PubMed tools         : {pm_tools}\n")
    print("Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Session ended.")
            break
        await _run_cli(user_input, agent)


if __name__ == "__main__":
    asyncio.run(main())
