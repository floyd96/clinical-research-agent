import os
import re
import random
from typing import Optional

# asyncpg default pool size (10) hits Supabase session pooler's 15-connection cap.
# Cap it at 3 — sufficient for a demo, stays within the free-tier limit.
import asyncpg as _asyncpg
_orig_create_pool = _asyncpg.create_pool
async def _small_pool(dsn=None, *, min_size=10, max_size=10, **kw):
    return await _orig_create_pool(dsn, min_size=1, max_size=3, statement_cache_size=0, **kw)
_asyncpg.create_pool = _small_pool

import logging

import chainlit as cl
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

_log = logging.getLogger(__name__)

from config import (
    CLINICALTRIALS_MCP_URL, PUBMED_MCP_URL,
    BRAND_TAGLINE, BETA_WHITELIST,
)
from db import (
    upsert_user, create_session, set_session_title,
    save_message,
)
from prompts import SYSTEM_PROMPT
from questions import QUESTION_POOL
from research_agent import model, classifier_model


_CT_KEYWORDS = {"clinical", "trial", "nct", "study"}

# Patterns that are unambiguously new research requests — bypass LLM classifier.
_FORCE_RESEARCH = re.compile(
    r'^(find|search|show|list|give\s+me|look\s+up|get|fetch|how\s+many|are\s+there|compare)\b'
    r'|\b(find|search|show|list|identify|retrieve)\b.{0,60}\b(trial|studi|paper|publication|article|literature|record)\b'
    r'|\bpublished\s+(paper|studi|article|evidence|literature|result)\b'
    r'|\bNCT\d{6,8}\b'
    r'|\b\d{2,3}[\s-]?year[\s-]?old\b'
    r'|\b(HbA1c|eligib)\b',
    re.IGNORECASE,
)


def _is_ct_tool(name: str) -> bool:
    return any(k in name.lower() for k in _CT_KEYWORDS)


# ── Auth ───────────────────────────────────────────────────────────────────────

@cl.oauth_callback
def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: dict,
    default_user: cl.User,
) -> Optional[cl.User]:
    email = raw_user_data.get("email", "")
    if email.lower() in [e.lower() for e in BETA_WHITELIST]:
        return cl.User(identifier=email, metadata=raw_user_data)
    return None


# ── Starter questions (shown before first message) ─────────────────────────────

@cl.set_starters
async def set_starters():
    starters = random.sample(QUESTION_POOL, 4)
    return [
        cl.Starter(
            label=f"{badge} {q}",
            message=q,
        )
        for badge, q in starters
    ]


# ── Session start ──────────────────────────────────────────────────────────────

@cl.on_chat_start
async def on_chat_start():
    user = cl.user_session.get("user")
    email = user.identifier if user else ""
    first_name = email.split("@")[0].capitalize()

    uid = upsert_user(email=email, display_name=first_name)

    # Auto-generated session ID — safe, no FK conflicts
    sid = create_session(uid)

    cl.user_session.set("db_user_id", uid)
    cl.user_session.set("db_session_id", sid)
    cl.user_session.set("lc_messages", [])
    cl.user_session.set("turn", 0)

    try:
        client = MultiServerMCPClient({
            "clinicaltrials": {"url": CLINICALTRIALS_MCP_URL, "transport": "streamable_http"},
            "pubmed":         {"url": PUBMED_MCP_URL,         "transport": "streamable_http"},
        })
        mcp_tools = await client.get_tools()
        agent = create_react_agent(model, mcp_tools, prompt=SYSTEM_PROMPT)
        cl.user_session.set("agent", agent)
        _log.info("Agent initialised with %d tools", len(mcp_tools))
    except Exception as exc:
        _log.error("on_chat_start failed: %r", exc)
        raise


# ── Message handler ────────────────────────────────────────────────────────────

@cl.on_message
async def on_message(message: cl.Message):
    await handle_query(message.content)


async def handle_query(query: str):
    agent   = cl.user_session.get("agent")
    lc_msgs = cl.user_session.get("lc_messages", [])
    sid     = cl.user_session.get("db_session_id")
    uid     = cl.user_session.get("db_user_id")
    turn    = cl.user_session.get("turn", 0)

    if agent is None:
        await cl.Message(content="⚠️ Agent failed to start — check server logs.").send()
        return

    lc_msgs.append(HumanMessage(content=query))

    # Intent classification (skip on first turn — always research)
    intent = "research"
    if turn > 0:
        # Fast path: deterministic signals that are unambiguously new data requests.
        # Topical overlap confuses the LLM classifier, so catch obvious cases first.
        if not _FORCE_RESEARCH.search(query):
            ctx = _build_classifier_context(lc_msgs[:-1])
            try:
                result = await classifier_model.ainvoke(
                    f"Classify the new message as 'followup' or 'research'.\n\n"
                    f"'followup' ONLY when the user explicitly references results already "
                    f"shown — e.g. 'those trials', 'that study', 'which of those', "
                    f"'tell me more about that', 'summarise what you found'. "
                    f"Topical overlap alone is NOT a followup.\n"
                    f"'research' for any new data request: new condition, drug, patient "
                    f"profile, trial search, paper search, NCT ID, or PMID lookup.\n\n"
                    f"Prior context: {ctx}\n"
                    f"New message: {query}\n\n"
                    f"Reply with one word only — 'followup' or 'research':"
                )
                first = re.split(r'\W+', result.content.strip().lower())[0]
                intent = "followup" if first == "followup" else "research"
            except Exception:
                pass

    msg = cl.Message(content="")
    sources: set[tuple[str, str]] = set()

    if intent == "followup":
        async for chunk in model.astream([SystemMessage(content=SYSTEM_PROMPT)] + lc_msgs):
            if isinstance(chunk.content, str) and chunk.content:
                await msg.stream_token(chunk.content)
    else:
        # Buffer model text — pre-tool reasoning is discarded on each tool_start.
        # Only the text generated after the final tool completes reaches the user.
        pending = ""
        try:
            async for event in agent.astream_events(
                {"messages": lc_msgs},
                version="v2",
                config={"recursion_limit": 10},
            ):
                kind = event["event"]
                if kind == "on_tool_start":
                    pending = ""  # discard inter-tool reasoning; not the final answer
                    badge = "🏥" if _is_ct_tool(event["name"]) else "📚"
                    try:
                        async with cl.Step(name=f"{badge} {event['name']}", type="tool"):
                            pass
                    except Exception as step_exc:
                        _log.warning("Step persistence failed (non-fatal): %r", step_exc)
                elif kind == "on_tool_end":
                    raw = str(event["data"].get("output", ""))
                    for nct in re.findall(r'NCT\d{8}', raw):
                        sources.add(("ct", nct))
                    for pmid in re.findall(r'(?i)(?:"pmid"|pmid)["\s:]+(\d{6,8})', raw):
                        sources.add(("pm", pmid))
                elif kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if (chunk and isinstance(chunk.content, str) and chunk.content
                            and not getattr(chunk, "tool_call_chunks", [])):
                        pending += chunk.content
        except Exception as exc:
            _log.error("Agent error: %r", exc)
        if pending:
            await msg.stream_token(pending)
        elif not msg.content:
            await msg.stream_token(
                "The search did not return results. Try narrowing your query "
                "with a specific condition, drug name, or NCT ID."
            )

    # Attach source links as inline elements
    if sources:
        ct = sorted(i for t, i in sources if t == "ct")
        pm = sorted(i for t, i in sources if t == "pm")
        lines = []
        if ct:
            lines.append("**🏥 ClinicalTrials.gov**")
            lines.extend(f"- [{nct}](https://clinicaltrials.gov/study/{nct})" for nct in ct[:5])
        if pm:
            lines.append("**📚 PubMed**")
            lines.extend(f"- [PMID {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)" for pmid in pm[:5])
        panel_title = f"Evidence & Citations — {len(ct) + len(pm)} source(s)"
        msg.elements = [
            cl.Text(name=panel_title, content="\n".join(lines), display="side")
        ]

    await msg.update()

    # Update session state
    lc_msgs.append(AIMessage(content=msg.content))
    cl.user_session.set("lc_messages", lc_msgs)
    cl.user_session.set("turn", turn + 1)

    # Persist to Supabase
    user_idx = turn * 2
    try:
        save_message(sid, user_idx,     "user",      query,       [],  [])
        save_message(sid, user_idx + 1, "assistant", msg.content, [], list(sources))
        if turn == 0:
            try:
                set_session_title(sid, query)
            except Exception:
                pass
    except Exception:
        pass


def _build_classifier_context(msgs: list) -> str:
    parts = []
    for m in msgs[-6:]:
        if isinstance(m, AIMessage) and m.content:
            for heading in re.findall(r'^#{1,3} (.+)$', m.content, re.MULTILINE):
                parts.append(heading[:60])
    return "\n".join(parts) if parts else "No prior research context."
