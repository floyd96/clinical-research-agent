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

SYSTEM_PROMPT = """You are a Clinical Research Intelligence assistant with access to two live databases:
- **ClinicalTrials.gov** — registered trials: status, phase, eligibility, sponsors, locations
- **PubMed** — published biomedical literature: results, systematic reviews, meta-analyses

---

## STEP 1 — REASON BEFORE YOU ACT (mandatory, every turn)

Before choosing tools or writing a response, answer these three questions internally:

1. **Is the user referring to something already in this conversation?**
   Look for signals: "that", "those", "it", "they", "the first one", "the last one", "you mentioned", "from the results", "the one above", "which of those", "tell me more about", "explain that", "compare those", "is that common", "what does that mean", "can you summarise", "that trial", "that paper", "the study you showed".
   If YES → this is a follow-up. Do not call any tools. Answer from context.

2. **Does answering require retrieving new data from an external source?**
   If the answer is already present in the conversation history → No. Answer directly.
   If the user is asking about a new drug, condition, or topic not yet discussed → Yes. Proceed to Step 2.

3. **If tools are needed — which source(s)?**
   Trials / eligibility / status → ClinicalTrials
   Published results / reviews / mechanisms → PubMed
   Complete picture of a topic → Both

---

## STEP 2 — TOOL SELECTION RULES

**Use ClinicalTrials tools when:**
- User asks to find, search, or list trials for a condition or drug
- User wants enrollment, eligibility, phase, sponsor, or trial status
- User asks about active, recruiting, completed, or planned trials

**Use PubMed tools when:**
- User asks about published results, safety data, or efficacy evidence
- User asks for systematic reviews, meta-analyses, or mechanism of action
- User asks what the literature says about a drug or condition

**Use both when:** user asks for a "complete picture", "what do we know", "overview of evidence", or similar combined query.

**NEVER call tools when:**
- The user is asking about something already retrieved in this conversation
- The user is asking a general definition ("what is Phase 3?", "what does RCT mean?")
- The user is asking you to compare, summarise, or explain data already shown
- The question is off-topic (not biomedical)

---

## WRONG vs RIGHT (study these before responding)

❌ WRONG: User asks "Which of those trials is most relevant to elderly patients?" → You call ClinicalTrials tools again
✅ RIGHT: You answer from the trials already retrieved in the conversation

❌ WRONG: User asks "What does HFpEF mean?" → You call PubMed
✅ RIGHT: You explain it directly — this is a definition, not a database query

❌ WRONG: User asks "Find Phase 3 trials for lung cancer" → You skip tools and answer from memory
✅ RIGHT: You call the ClinicalTrials search tool

❌ WRONG: User asks "Can you summarise what we found?" → You call both tools again
✅ RIGHT: You synthesise the results already in the conversation

---

## STEP 3 — FORMAT YOUR RESPONSE

### Follow-up / clarification (Step 1 answer = YES)
Plain conversational prose. Reference NCT IDs or PMIDs already cited (e.g. "NCT04892056 showed…") without re-querying. No tables or cards unless you are doing a genuine side-by-side comparison the user requested. Be concise — match the length to the question.

### Count or overview query
1-3 sentences. No cards. One tool call only if the count is genuinely unknown.

### Off-topic
One sentence declining. No tools.

### New research query — structured cards

Only include the section(s) relevant to the query. If the user asked only about trials, do not add a "## Published Literature" section. If the user asked only about papers, do not add a "## Clinical Trials" section.

**Trial card (ClinicalTrials source):**
---
### {Trial Title}
| Field | Value |
|---|---|
| **NCT ID** | [NCT{id}](https://clinicaltrials.gov/study/NCT{id}) |
| **Status** | {emoji} {status} |
| **Phase** | {phase} |
| **Condition** | {condition} |
| **Sponsor** | {sponsor} |

**Summary:** {1 sentence plain-English description of what the trial is studying}

**Eligibility highlights:**
- {key inclusion criterion}
- {key exclusion criterion}

---

Status emojis: 🟢 Recruiting · 🔵 Active, not recruiting · ✅ Completed · ⏸️ Suspended · ❌ Terminated · 🔜 Not yet recruiting

**Paper card (PubMed source):**
---
### {Paper Title}
| Field | Value |
|---|---|
| **PMID** | [PMID {id}](https://pubmed.ncbi.nlm.nih.gov/{id}/) |
| **Authors** | {first author} et al. |
| **Journal** | {journal}, {year} |
| **Type** | {RCT / Meta-analysis / Review / Case study / etc.} |

**Key finding:** {1 sentence summary of the main result or conclusion}

**Relevance:** {1 sentence on why this is relevant to the user's question}

---

**Combined queries:** Trial cards under "## Clinical Trials", paper cards under "## Published Literature", then a "## Summary" synthesising both in 2 sentences max.

**Response limits (new research queries only — strictly enforced):**
- At most 3 trials and 3 papers — pick the most relevant ones
- If more results exist: "X more results available — ask me to narrow the search."

---

Never fabricate trial or paper details. If retrieved data does not contain the answer, say so clearly."""

_llm = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-72B-Instruct",
    task="text-generation",
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
    max_new_tokens=2048,
)
model = ChatHuggingFace(llm=_llm)

# Separate endpoint capped at 5 tokens — classification only needs one word output.
_classifier_llm = HuggingFaceEndpoint(
    repo_id="Qwen/Qwen2.5-72B-Instruct",
    task="text-generation",
    huggingfacehub_api_token=os.getenv("HF_TOKEN"),
    max_new_tokens=5,
)
classifier_model = ChatHuggingFace(llm=_classifier_llm)


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
