import json
import queue as q_module
import random
import re
from datetime import datetime

import streamlit as st
from streamlit_javascript import st_javascript
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config import (
    CLINICALTRIALS_MCP_URL, PUBMED_MCP_URL,
    PAGE_TITLE, PAGE_ICON,
    BRAND_TAGLINE,
    CHAT_PLACEHOLDER, STATUS_RETRIEVING, SECTION_SUGGESTIONS,
    EXPORT_BUTTON_LABEL, CLEAR_BUTTON_LABEL, EXPORT_PDF_TIP,
    SIDEBAR_SOURCES_HDR, SIDEBAR_HISTORY_HDR, SIDEBAR_RETRIEVED_HDR,
    LS_KEY,
)
from prompts import SYSTEM_PROMPT
from questions import QUESTION_POOL
from research_agent import model, classifier_model, run_async, _loop
from langchain_mcp_adapters.client import MultiServerMCPClient
from ui.styles import get_css
from ui.components import (
    SOUND_SEND, SOUND_DONE, INIT_PARENT,
    SCROLL_BTN_SHOW, SCROLL_BTN_HIDE,
    get_ribbon_js,
    play, copy_button, render_sources, save_session, clear_session_storage,
    build_html_export,
)

import asyncio

# ── Tool source classification ─────────────────────────────────────────────────
_CT_KEYWORDS = {"clinical", "trial", "nct", "study"}
_PM_KEYWORDS = {"pubmed", "article", "paper", "literature", "abstract", "pmid", "mesh"}


def _source_badge(tool_name: str) -> str:
    name = tool_name.lower()
    if any(k in name for k in _CT_KEYWORDS):
        return "🏥"
    if any(k in name for k in _PM_KEYWORDS):
        return "📚"
    return "🔧"


def _is_ct_tool(name: str) -> bool:
    return any(k in name.lower() for k in _CT_KEYWORDS)


# ── Agent setup ────────────────────────────────────────────────────────────────

@st.cache_resource
def get_agent():
    async def _setup():
        client = MultiServerMCPClient(
            {
                "clinicaltrials": {"url": CLINICALTRIALS_MCP_URL, "transport": "streamable_http"},
                "pubmed":          {"url": PUBMED_MCP_URL,         "transport": "streamable_http"},
            }
        )
        mcp_tools = await client.get_tools()
        return create_agent(model, mcp_tools, system_prompt=SYSTEM_PROMPT), mcp_tools
    return run_async(_setup())


# ── Intent classification ──────────────────────────────────────────────────────

def _build_classifier_context(chat_display: list) -> str:
    nct_ids, pmids, topics = [], [], []
    for item in chat_display:
        if item["role"] != "assistant":
            continue
        for src_type, src_id in item.get("sources", []):
            if src_type == "ct" and src_id not in nct_ids:
                nct_ids.append(src_id)
            elif src_type == "pm" and src_id not in pmids:
                pmids.append(src_id)
        if item.get("content"):
            for heading in re.findall(r'^#{1,3} (.+)$', item["content"], re.MULTILINE):
                topic = heading[:60]
                if topic not in topics:
                    topics.append(topic)
    parts = []
    if topics:
        parts.append("Topics discussed: " + "; ".join(topics[-3:]))
    if nct_ids:
        parts.append("Trials shown: " + ", ".join(nct_ids[-6:]))
    if pmids:
        parts.append("Papers shown: PMID " + ", PMID ".join(pmids[-6:]))
    return "\n".join(parts) if parts else "No research results retrieved yet."


async def classify_intent(user_message: str, context: str) -> str:
    prompt = (
        "You are a query classifier for a clinical research assistant.\n\n"
        "Research results already retrieved in this session:\n"
        f"{context}\n\n"
        "New user message:\n"
        f"{user_message}\n\n"
        "Is the user asking about something from the retrieved results above "
        "(e.g. clarification, comparison, summary, or more detail)? "
        "Or are they asking for NEW information requiring a database search?\n\n"
        "Reply with exactly one word — 'followup' or 'research':"
    )
    result = await classifier_model.ainvoke(prompt)
    output = result.content.strip().lower()
    return "followup" if "followup" in output else "research"


# ── Agent execution ────────────────────────────────────────────────────────────

def _build_clean_messages(chat_display: list) -> list:
    msgs = []
    for item in chat_display:
        if item["role"] == "user":
            msgs.append(HumanMessage(content=item["content"]))
        elif item["role"] == "assistant" and item.get("content"):
            msgs.append(AIMessage(content=item["content"]))
    return msgs


def run_direct(messages, response_placeholder):
    """Direct model stream for follow-ups — no tools, no agent loop."""
    updates = q_module.Queue()

    async def _stream():
        full_msgs = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        async for chunk in model.astream(full_msgs):
            if isinstance(chunk.content, str) and chunk.content:
                updates.put(("token", chunk.content))
        updates.put(("done",))

    future = asyncio.run_coroutine_threadsafe(_stream(), _loop)
    full_response = ""

    while True:
        try:
            kind, *data = updates.get(timeout=0.5)
            if kind == "token":
                full_response += data[0]
                response_placeholder.markdown(full_response + " ▌")
            elif kind == "done":
                response_placeholder.markdown(full_response)
                break
        except q_module.Empty:
            if future.done():
                break

    future.result()
    return full_response


def run_agent(messages, status_container, response_placeholder):
    """Stream agent events; return (result, tools_called, full_response, sources)."""
    updates = q_module.Queue()

    async def _stream():
        root_run_id = None
        result = None
        async for event in agent.astream_events({"messages": messages}, version="v2"):
            kind = event["event"]
            if kind == "on_chain_start" and root_run_id is None:
                root_run_id = event.get("run_id")
            elif kind == "on_tool_start":
                updates.put(("tool", event["name"]))
            elif kind == "on_tool_end":
                raw = str(event["data"].get("output", ""))
                for nct in re.findall(r'NCT\d{8}', raw):
                    updates.put(("source", ("ct", nct)))
                for pmid in re.findall(r'(?i)(?:"pmid"|pmid)["\s:]+(\d{6,8})', raw):
                    updates.put(("source", ("pm", pmid)))
            elif kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if (chunk
                        and isinstance(chunk.content, str)
                        and chunk.content
                        and not getattr(chunk, "tool_call_chunks", [])):
                    updates.put(("token", chunk.content))
            elif kind == "on_chain_end" and event.get("run_id") == root_run_id:
                result = event["data"].get("output")
        updates.put(("done", result))

    future = asyncio.run_coroutine_threadsafe(_stream(), _loop)
    result = None
    tools_called = []
    full_response = ""
    sources = set()
    status_collapsed = False

    while True:
        try:
            kind, data = updates.get(timeout=0.5)
            if kind == "tool":
                with status_container:
                    st.write(f"{_source_badge(data)} `{data}`")
                tools_called.append(data)
            elif kind == "source":
                sources.add(data)
            elif kind == "token":
                if not status_collapsed:
                    status_container.update(label="Done", state="complete", expanded=False)
                    status_collapsed = True
                full_response += data
                response_placeholder.markdown(full_response + " ▌")
            elif kind == "done":
                result = data
                if not status_collapsed:
                    status_container.update(label="Done", state="complete", expanded=False)
                response_placeholder.markdown(full_response)
                break
        except q_module.Empty:
            if future.done():
                break

    future.result()
    return result, tools_called, full_response, sources


# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")
st.markdown(get_css(), unsafe_allow_html=True)

agent, all_tools = get_agent()

# ── Session state ──────────────────────────────────────────────────────────────

if "lc_messages"       not in st.session_state:
    st.session_state.lc_messages       = []
if "chat_display"      not in st.session_state:
    st.session_state.chat_display      = []
if "queued_prompt"     not in st.session_state:
    st.session_state.queued_prompt     = None
if "example_questions" not in st.session_state:
    st.session_state.example_questions = random.sample(QUESTION_POOL, 4)
if "session_restored"  not in st.session_state:
    st.session_state.session_restored  = False

# ── Browser-local hour for greeting (avoids server UTC mismatch on prod) ──────
# +1 shifts range to 1-24 so 0 (st_javascript loading placeholder) is unambiguous

_js_hour = st_javascript("new Date().getHours() + 1")
_hour = (int(_js_hour) - 1) if isinstance(_js_hour, (int, float)) and 1 <= _js_hour <= 24 else datetime.now().hour
_greeting = f"Good {'morning' if _hour < 12 else 'afternoon' if _hour < 17 else 'evening'}."

# ── Restore history from localStorage ─────────────────────────────────────────

_ls_value = st_javascript(f"(window.parent||window).localStorage.getItem('{LS_KEY}') || 'null'")
if (isinstance(_ls_value, str)
        and _ls_value not in ("null", "undefined", "")
        and not st.session_state.session_restored
        and not st.session_state.chat_display):
    try:
        _saved = json.loads(_ls_value)
        if _saved:
            st.session_state.chat_display = _saved
            st.session_state.lc_messages  = _build_clean_messages(_saved)
            st.session_state.session_restored = True
            st.rerun()
    except Exception:
        pass

if st.session_state.chat_display:
    save_session(st.session_state.chat_display)

if st.session_state.pop("clear_storage", False):
    clear_session_storage()

st.components.v1.html(INIT_PARENT, height=0)
st.components.v1.html(get_ribbon_js(), height=0)

if st.session_state.pop("play_done_sound", False):
    play(SOUND_DONE)

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    ct_tools = [t for t in all_tools if _is_ct_tool(t.name)]
    pm_tools = [t for t in all_tools if t not in ct_tools]

    st.markdown(f"**{SIDEBAR_SOURCES_HDR}**")
    st.markdown(
        '<div style="font-size:0.82rem;color:#334155;line-height:1.7;">'
        '🏥 <a href="https://clinicaltrials.gov" target="_blank" style="color:#1F497D;text-decoration:none;">ClinicalTrials.gov</a><br>'
        '📚 <a href="https://pubmed.ncbi.nlm.nih.gov" target="_blank" style="color:#1a5f6e;text-decoration:none;">PubMed / EuropePMC</a>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    user_queries = [m["content"] for m in st.session_state.chat_display if m["role"] == "user"]
    if user_queries:
        st.markdown(f"**{SIDEBAR_HISTORY_HDR}** · {len(user_queries)}")
        for q in user_queries[-5:]:
            label = q[:52] + "…" if len(q) > 52 else q
            st.markdown(f'<div class="hist-item">{label}</div>', unsafe_allow_html=True)
        st.divider()

    session_nct, session_pm = [], []
    for m in st.session_state.chat_display:
        if m["role"] == "assistant":
            for src_type, src_id in m.get("sources", []):
                if src_type == "ct" and src_id not in session_nct:
                    session_nct.append(src_id)
                elif src_type == "pm" and src_id not in session_pm:
                    session_pm.append(src_id)
    if session_nct or session_pm:
        st.markdown(f"**{SIDEBAR_RETRIEVED_HDR}**")
        for nct in session_nct[:5]:
            st.markdown(f"🏥 [{nct}](https://clinicaltrials.gov/study/{nct})")
        for pmid in session_pm[:5]:
            st.markdown(f"📚 [PMID {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")
        st.divider()

    has_chat = bool(st.session_state.chat_display)
    st.download_button(
        label=EXPORT_BUTTON_LABEL,
        data=build_html_export(st.session_state.chat_display) if has_chat else " ",
        file_name=f"mayo_research_session_{datetime.now().strftime('%Y%m%d')}.html",
        mime="text/html",
        use_container_width=True,
        disabled=not has_chat,
    )
    if has_chat:
        st.caption(EXPORT_PDF_TIP)

    st.divider()
    if st.button(CLEAR_BUTTON_LABEL, use_container_width=True):
        st.session_state.lc_messages       = []
        st.session_state.chat_display      = []
        st.session_state.session_restored  = True
        st.session_state.example_questions = random.sample(QUESTION_POOL, 4)
        st.session_state.clear_storage     = True
        st.rerun()

    st.markdown(
        '<div style="margin-top:1.5rem;padding-top:0.75rem;border-top:1px solid #e8e5e0;'
        'font-size:0.72rem;color:#94a3b8;line-height:2;">'
        '<a href="#" style="color:#94a3b8;text-decoration:none;">Privacy</a>'
        ' &nbsp;·&nbsp; '
        '<a href="#" style="color:#94a3b8;text-decoration:none;">Help</a>'
        ' &nbsp;·&nbsp; '
        '<a href="#" style="color:#94a3b8;text-decoration:none;">Trial matching guidance</a>'
        '</div>',
        unsafe_allow_html=True,
    )

# ── Hero / compact header ──────────────────────────────────────────────────────

if not st.session_state.chat_display:
    st.components.v1.html(SCROLL_BTN_HIDE, height=0)
    st.markdown(
        f'<div class="workspace-header">'
        f'<div class="greeting-text">{_greeting}</div>'
        f'<div class="greeting-sub">{BRAND_TAGLINE}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(f'<div class="section-label">{SECTION_SUGGESTIONS}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    for i, (badge, ex) in enumerate(st.session_state.example_questions):
        col = col1 if i % 2 == 0 else col2
        if col.button(ex, use_container_width=True, key=f"ex{i}"):
            st.session_state.queued_prompt = ex
            st.rerun()

else:
    st.components.v1.html(SCROLL_BTN_SHOW, height=0)
    st.markdown(
        '<div class="compact-header">'
        f'<span class="badge badge-ct">🏥 ClinicalTrials.gov</span>'
        f'<span class="badge badge-pm">📚 PubMed</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    for item in st.session_state.chat_display:
        with st.chat_message(item["role"], avatar="🏥" if item["role"] == "assistant" else None):
            if item.get("tools_used"):
                tool_sources = set()
                for t in item["tools_used"]:
                    tool_sources.add("ct" if _is_ct_tool(t) else "pm")
                label = {
                    frozenset({"ct"}):       "🏥 ClinicalTrials only",
                    frozenset({"pm"}):       "📚 PubMed only",
                    frozenset({"ct", "pm"}): "🏥 ClinicalTrials + 📚 PubMed",
                }.get(frozenset(tool_sources), f"{len(item['tools_used'])} tool call(s)")
                with st.expander(label):
                    for t in item["tools_used"]:
                        st.code(f"{_source_badge(t)}  {t}", language="text")

            st.markdown(item["content"])

            if item.get("sources"):
                render_sources(item["sources"])

            if item["role"] == "assistant" and item.get("content"):
                copy_button(item["content"])

# ── Input ──────────────────────────────────────────────────────────────────────

prompt = st.chat_input(CHAT_PLACEHOLDER)
if not prompt and st.session_state.queued_prompt:
    prompt = st.session_state.queued_prompt
    st.session_state.queued_prompt = None

# ── Routing ────────────────────────────────────────────────────────────────────

if prompt:
    play(SOUND_SEND)
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_display.append({"role": "user", "content": prompt})
    st.session_state.lc_messages.append(HumanMessage(content=prompt))

    prior = st.session_state.chat_display[:-1]
    if prior:
        context = _build_classifier_context(prior)
        try:
            intent = run_async(classify_intent(prompt, context))
        except Exception as e:
            print(f"[classifier] fallback to research — {e}")
            intent = "research"
    else:
        intent = "research"

    with st.chat_message("assistant", avatar="🏥"):
        response_placeholder = st.empty()

        if intent == "followup":
            full_response = run_direct(
                _build_clean_messages(st.session_state.chat_display),
                response_placeholder,
            )
            tools_called, sources, result = [], set(), None
        else:
            status_container = st.status(STATUS_RETRIEVING, expanded=True)
            result, tools_called, full_response, sources = run_agent(
                st.session_state.lc_messages, status_container, response_placeholder
            )
            if not full_response and result is None:
                st.error("No response returned. Please try again.")
            if sources:
                render_sources(sources)

    if result or full_response:
        if result:
            st.session_state.lc_messages = result["messages"]
        elif full_response:
            st.session_state.lc_messages.append(AIMessage(content=full_response))
        st.session_state.chat_display.append({
            "role": "assistant",
            "content": full_response,
            "tools_used": tools_called,
            "sources": list(sources),
        })
        st.session_state.play_done_sound = True
        st.rerun()
