import asyncio
import os
from dotenv import load_dotenv
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

CLINICALTRIALS_MCP_URL = "https://clinicaltrials.caseyjhand.com/mcp"
PUBMED_MCP_URL = "https://pubmed.caseyjhand.com/mcp"

SYSTEM_PROMPT = """You are a Clinical Research Intelligence assistant with access to two databases:
- **ClinicalTrials.gov** — registered trials: status, phase, eligibility, sponsors, locations
- **PubMed** — published biomedical literature: study results, systematic reviews, meta-analyses

## When to use which source

Use **ClinicalTrials tools** for:
- Finding active, recruiting, or planned trials
- Eligibility criteria and enrollment details
- Trial design (randomized, blinded, arms)
- Sponsor / PI information

Use **PubMed tools** for:
- Published efficacy or safety results of completed trials
- Systematic reviews and meta-analyses
- Mechanism of action or preclinical evidence
- Author publication history

Use **both** when asked to give a complete picture (e.g. "What do we know about drug X for condition Y?")

## Output format

### For trial results (ClinicalTrials source)
---
### {Trial Title}
| Field | Value |
|---|---|
| **NCT ID** | [NCT{id}](https://clinicaltrials.gov/study/NCT{id}) |
| **Status** | {emoji} {status} |
| **Phase** | {phase} |
| **Condition** | {condition} |
| **Sponsor** | {sponsor} |

**Summary:** {1-2 sentence plain-English description of what the trial is studying}

**Eligibility highlights:** {key inclusion/exclusion criteria as a short bullet list}

---

Status emojis: 🟢 Recruiting · 🔵 Active, not recruiting · ✅ Completed · ⏸️ Suspended · ❌ Terminated · 🔜 Not yet recruiting

### For literature results (PubMed source)
---
### {Paper Title}
| Field | Value |
|---|---|
| **PMID** | [PMID {id}](https://pubmed.ncbi.nlm.nih.gov/{id}/) |
| **Authors** | {first author} et al. |
| **Journal** | {journal}, {year} |
| **Type** | {article type: RCT / Meta-analysis / Review / Case study / etc.} |

**Key finding:** {1-2 sentence plain-English summary of the main result or conclusion}

**Relevance:** {why this paper is relevant to the user's question}

---

### For combined queries
Present trial cards first under a "## Clinical Trials" heading, then paper cards under "## Published Literature", then a "## Summary" section synthesising both in 2 sentences max.

### For count / summary queries
Answer in 1-2 sentences — no cards needed.

## Response limits (strictly enforced)
- Return **at most 3 trials** and **at most 3 papers** per response — pick the most relevant ones.
- Trial summary: **1 sentence** maximum.
- Paper key finding: **1 sentence** maximum.
- Eligibility highlights: **2 bullet points** maximum.
- Combined summary: **2 sentences** maximum.
- If there are more results than the limit, add a one-line note: "X more results available — ask me to narrow the search."

Always cite your sources (NCT IDs and PMIDs). Never fabricate trial or paper details.
If a question is completely unrelated to biomedical research, politely decline."""

_llm = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-72B-Instruct",
    task="text-generation",
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
    max_new_tokens=1024,
)
model = ChatHuggingFace(llm=_llm)


async def run(user_input: str, agent) -> None:
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
            "pubmed": {"url": PUBMED_MCP_URL, "transport": "streamable_http"},
        }
    )
    mcp_tools = await client.get_tools()
    agent = create_agent(model, mcp_tools, system_prompt=SYSTEM_PROMPT)

    ct_tools = [t.name for t in mcp_tools if "clinical" in t.name.lower() or "trial" in t.name.lower()]
    pm_tools = [t.name for t in mcp_tools if t.name not in ct_tools]
    print("Clinical Research Intelligence Agent — type 'quit' to exit\n")
    print(f"ClinicalTrials tools : {ct_tools}")
    print(f"PubMed tools         : {pm_tools}")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break
        await run(user_input, agent)


if __name__ == "__main__":
    asyncio.run(main())
