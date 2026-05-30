import asyncio
import html as _html
import json
import queue as q_module
import random
import re
import threading
from datetime import date, datetime
import streamlit as st
from streamlit_javascript import st_javascript
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from research_agent import CLINICALTRIALS_MCP_URL, PUBMED_MCP_URL, SYSTEM_PROMPT, model, classifier_model

_SOUND_SEND = """
<script>
(function(){
  try {
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    ctx.resume().then(function(){
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(520, ctx.currentTime);
      osc.frequency.linearRampToValueAtTime(680, ctx.currentTime + 0.08);
      gain.gain.setValueAtTime(0.07, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);
      osc.start(); osc.stop(ctx.currentTime + 0.12);
    });
  } catch(e) {}
})();
</script>
"""

_SOUND_DONE = """
<script>
(function(){
  try {
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    ctx.resume().then(function(){
      [[880, 0], [1108, 0.14]].forEach(function(p){
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.type = 'sine';
        osc.frequency.value = p[0];
        var t = ctx.currentTime + p[1];
        gain.gain.setValueAtTime(0.08, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.55);
        osc.start(t); osc.stop(t + 0.55);
      });
    });
  } catch(e) {}
})();
</script>
"""

_INIT_PARENT = """
<script>
(function(){
    var p = window.parent;
    if (!p || p._cri_init) return;
    p._cri_init = true;
    if (p.history && 'scrollRestoration' in p.history) {
        p.history.scrollRestoration = 'manual';
    }
    function goTop() {
        p.scrollTo(0, 0);
        ['[data-testid="stAppViewContainer"]','[data-testid="stMainBlockContainer"]'].forEach(function(s){
            var el = p.document.querySelector(s);
            if (el) el.scrollTop = 0;
        });
    }
    p.requestAnimationFrame(function(){ goTop(); p.requestAnimationFrame(goTop); });
    setTimeout(goTop, 400);
})();
</script>
"""

_ENTERPRISE_RIBBON = """
<script>
(function(){
    var p = window.parent;
    if (!p || p.document.getElementById('ent-ribbon')) return;
    var el = p.document.createElement('div');
    el.id = 'ent-ribbon';
    el.className = 'ent-ribbon';
    el.innerHTML = '<div class="ent-ribbon-left">'
        + '<span class="ent-burger">&#9776;</span>'
        + '<span class="ent-brand">🧬 LifeSciences Intelligence</span>'
        + '</div>'
        + '<div class="ent-ribbon-right">'
        + '<div class="ent-avatar">AR</div>'
        + '<div><div class="ent-profile-name">Alex Reynolds</div>'
        + '<div class="ent-profile-role">Research Lead</div></div>'
        + '</div>';
    p.document.body.prepend(el);
})();
</script>
"""

_SCROLL_BTN_SHOW = """
<script>
(function(){
    var p = window.parent;
    if (!p || p.document.getElementById('cri-scroll-btn')) return;
    var btn = p.document.createElement('button');
    btn.id = 'cri-scroll-btn';
    btn.title = 'Scroll to bottom';
    btn.innerHTML = '&#8595;';
    btn.style.cssText = 'position:fixed;bottom:80px;right:16px;width:36px;height:36px;'
        + 'border-radius:50%;background:#0891b2;color:#fff;border:none;cursor:pointer;'
        + 'font-size:18px;font-weight:700;box-shadow:0 2px 8px rgba(0,0,0,0.18);'
        + 'z-index:99999;opacity:0.82;transition:opacity 0.2s;';
    btn.onmouseover = function(){ btn.style.opacity='1'; };
    btn.onmouseout  = function(){ btn.style.opacity='0.82'; };
    btn.onclick = function(){
        var doc = p.document;
        // Find the element with the largest scrollable height — works across Streamlit versions
        var best = null;
        var bestH = 0;
        doc.querySelectorAll('section, div, main, article').forEach(function(el){
            var ov = p.getComputedStyle(el).overflowY;
            if ((ov === 'auto' || ov === 'scroll') && el.scrollHeight > bestH) {
                bestH = el.scrollHeight;
                best = el;
            }
        });
        if (best) {
            best.scrollTop = best.scrollHeight;
        }
        // Always scroll specific known Streamlit containers and the window too
        ['[data-testid="stAppViewContainer"]','[data-testid="stMain"]','.main'].forEach(function(s){
            var el = doc.querySelector(s);
            if (el) el.scrollTop = el.scrollHeight;
        });
        p.scrollTo(0, doc.documentElement.scrollHeight);
    };
    p.document.body.appendChild(btn);
})();
</script>
"""

_SCROLL_BTN_HIDE = """
<script>
(function(){
    var p = window.parent;
    var btn = p && p.document.getElementById('cri-scroll-btn');
    if (btn) btn.remove();
})();
</script>
"""


def _play(sound_html: str):
    st.components.v1.html(sound_html, height=0)


def _copy_button(text: str):
    clean = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    clean = re.sub(r'\*(.+?)\*',     r'\1', clean)
    clean = re.sub(r'^#{1,6}\s+',    '',    clean, flags=re.MULTILINE)
    clean = re.sub(r'^\|.*\|$',      '',    clean, flags=re.MULTILINE)
    clean = re.sub(r'^[-| :]+$',     '',    clean, flags=re.MULTILINE)
    clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean).strip()
    with st.expander("📋 Copy response"):
        st.code(clean, language=None, wrap_lines=True)


_LS_KEY = "cri_session"


def _save_session(chat_display: list):
    data = [
        {
            "role": i["role"],
            "content": i.get("content", ""),
            "sources": i.get("sources", []),
            "tools_used": i.get("tools_used", []),
        }
        for i in chat_display
    ]
    escaped = _html.escape(json.dumps(data, ensure_ascii=False))
    st.components.v1.html(
        f"""<textarea id="cri_d" style="display:none">{escaped}</textarea>
        <script>
        try{{
            var v=document.getElementById('cri_d').value;
            (window.parent||window).localStorage.setItem('{_LS_KEY}',v);
        }}catch(e){{}}
        </script>""",
        height=0,
    )


def _clear_session_storage():
    st.components.v1.html(
        f"<script>try{{(window.parent||window).localStorage.removeItem('{_LS_KEY}');}}catch(e){{}}</script>",
        height=0,
    )

# One persistent event loop so the async HTTP pool is never tied to a closed loop.
_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()


def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()


def _build_classifier_context(chat_display: list) -> str:
    """Build a compact session-wide context summary for the intent classifier."""
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


def _build_clean_messages(chat_display: list) -> list:
    """Build HumanMessage/AIMessage list from display history — no tool call artifacts."""
    msgs = []
    for item in chat_display:
        if item["role"] == "user":
            msgs.append(HumanMessage(content=item["content"]))
        elif item["role"] == "assistant" and item.get("content"):
            msgs.append(AIMessage(content=item["content"]))
    return msgs


@st.cache_resource
def get_agent():
    async def _setup():
        client = MultiServerMCPClient(
            {
                "clinicaltrials": {"url": CLINICALTRIALS_MCP_URL, "transport": "streamable_http"},
                "pubmed": {"url": PUBMED_MCP_URL, "transport": "streamable_http"},
            }
        )
        mcp_tools = await client.get_tools()
        return create_agent(model, mcp_tools, system_prompt=SYSTEM_PROMPT), mcp_tools
    return run_async(_setup())


# ── Tool source classification ────────────────────────────────────────────────
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


def _render_sources(sources):
    ct = sorted(i for t, i in sources if t == "ct")
    pm = sorted(i for t, i in sources if t == "pm")
    with st.expander(f"📎 {len(sources)} source(s)", expanded=False):
        if ct:
            st.markdown("**🏥 ClinicalTrials.gov**")
            for nct in ct:
                st.markdown(f"- [{nct}](https://clinicaltrials.gov/study/{nct})")
        if pm:
            st.markdown("**📚 PubMed**")
            for pmid in pm:
                st.markdown(f"- [PMID {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")


def _md_to_html_body(text: str) -> str:
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Headers
    for n in (3, 2, 1):
        t = re.sub(rf'^{"#"*n} (.+)$', rf'<h{n}>\1</h{n}>', t, flags=re.MULTILINE)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\*(.+?)\*',     r'<em>\1</em>',         t)
    t = re.sub(r'`(.+?)`',       r'<code>\1</code>',      t)
    # Links
    t = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', t)
    # Tables: | col | col |
    def _table(m):
        rows = [r for r in m.group(0).splitlines() if r.strip() and not re.match(r'^\|[-| ]+\|$', r.strip())]
        html = "<table>"
        for i, row in enumerate(rows):
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            tag = "th" if i == 0 else "td"
            html += "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"
        return html + "</table>"
    t = re.sub(r'(\|.+\|\n?)+', _table, t)
    # Horizontal rules
    t = re.sub(r'^---+$', '<hr>', t, flags=re.MULTILINE)
    # Paragraphs
    parts = re.split(r'\n{2,}', t)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p.startswith(("<h", "<table", "<hr")):
            out.append(p)
        else:
            out.append(f"<p>{p.replace(chr(10), '<br>')}</p>")
    return "\n".join(out)


def _build_html_export(chat_display: list) -> str:
    css = """
    body { font-family: -apple-system, Arial, sans-serif; max-width: 820px;
           margin: 40px auto; color: #1e293b; line-height: 1.6; }
    h1 { color: #0f172a; font-size: 1.6rem; margin-bottom: 4px; }
    .meta { color: #64748b; font-size: 0.85rem; margin-bottom: 2rem; }
    hr { border: none; border-top: 1px solid #e2e8f0; margin: 2rem 0; }
    .question { background: #e0f2fe; border-radius: 8px; padding: 12px 16px;
                color: #0369a1; font-weight: 600; margin: 1.5rem 0 0.5rem; }
    .answer   { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px;
                padding: 16px 20px; margin-bottom: 0.5rem; }
    .sources  { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
                padding: 10px 14px; font-size: 0.82rem; color: #64748b; margin-top: 6px; }
    .sources a { color: #0891b2; text-decoration: none; }
    table { border-collapse: collapse; width: 100%; margin: 0.75rem 0; font-size: 0.875rem; }
    th { background: #f1f5f9; padding: 6px 12px; text-align: left;
         font-weight: 600; border-bottom: 2px solid #e2e8f0; }
    td { padding: 6px 12px; border-bottom: 1px solid #f1f5f9; }
    code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; font-size: 0.85em; }
    @media print { body { margin: 20px; } }
    """
    body_parts = [
        f"<h1>🧬 Clinical Research Intelligence</h1>",
        f'<div class="meta">Session Report &nbsp;·&nbsp; {date.today().strftime("%B %d, %Y")}</div>',
        "<hr>",
    ]
    for item in chat_display:
        if item["role"] == "user":
            body_parts.append(f'<div class="question">{item["content"]}</div>')
        else:
            body_parts.append(f'<div class="answer">{_md_to_html_body(item.get("content",""))}</div>')
            srcs = item.get("sources", [])
            if srcs:
                ct = sorted(i for t, i in srcs if t == "ct")
                pm = sorted(i for t, i in srcs if t == "pm")
                links = []
                for nct in ct:
                    links.append(f'🏥 <a href="https://clinicaltrials.gov/study/{nct}">{nct}</a>')
                for pmid in pm:
                    links.append(f'📚 <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/">PMID {pmid}</a>')
                body_parts.append(f'<div class="sources"><strong>Sources:</strong> {"&nbsp;&nbsp;".join(links)}</div>')

    html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Research Session</title><style>{css}</style></head><body>{''.join(body_parts)}</body></html>"
    return html


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


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Clinical Research Intelligence",
    page_icon="🧬",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ── Mobile-First Light Theme Override ─────────────── */
    @media (max-width: 768px) {
        /* Force light theme on mobile */
        html, body, [data-stale="false"] {
            background-color: #ffffff !important;
            color: #1e293b !important;
        }
        [data-testid="stApp"] {
            background-color: #f8fafc !important;
        }
        /* Ensure all text is dark on mobile */
        *, *::before, *::after {
            color: inherit !important;
        }
    }

    /* ── Global font ──────────────────────────────────── */
    html, body, [class*="css"], .stMarkdown, button, input, textarea {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }

    /* ── Enterprise ribbon ───────────────────────────────── */
    .ent-ribbon {
        position: fixed; top: 0; left: 0; right: 0; height: 52px;
        background: #0f172a; display: flex; align-items: center;
        justify-content: space-between; padding: 0 1.25rem;
        z-index: 10000; box-shadow: 0 1px 4px rgba(0,0,0,0.3);
        font-family: 'Inter', -apple-system, sans-serif;
    }
    .ent-ribbon-left { display: flex; align-items: center; gap: 1rem; }
    .ent-burger { font-size: 1.1rem; color: #94a3b8; cursor: default; line-height: 1; }
    .ent-brand { font-size: 0.875rem; font-weight: 600; color: #f1f5f9; letter-spacing: -0.01em; }
    .ent-ribbon-right { display: flex; align-items: center; gap: 0.625rem; }
    .ent-avatar {
        width: 30px; height: 30px; border-radius: 50%;
        background: #0891b2; color: #fff;
        font-size: 0.7rem; font-weight: 700;
        display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }
    .ent-profile-name { font-size: 0.78rem; font-weight: 600; color: #f1f5f9; line-height: 1.2; }
    .ent-profile-role { font-size: 0.68rem; color: #64748b; line-height: 1.2; }
    [data-testid="stSidebar"] { top: 52px !important; }

    /* ── Layout ──────────────────────────────────────── */
    [data-testid="stMainBlockContainer"] {
        max-width: 840px;
        margin: 0 auto;
        padding: 1.5rem 2rem 6rem;
    }
    @media (max-width: 768px) {
        [data-testid="stMainBlockContainer"] {
            padding: 3rem 0.5rem 4rem;
            max-width: 100%;
        }
    }
    @media (max-width: 480px) {
        [data-testid="stMainBlockContainer"] {
            padding: 2.75rem 0.25rem 4rem;
        }
    }

    /* ── Background ───────────────────────────────────── */
    [data-testid="stMain"] { background: #f5f4f0; }
    @media (max-width: 768px) {
        [data-testid="stMain"] { background: #f7f6f3 !important; }
    }

    /* ── Workspace header ─────────────────────────────── */
    .workspace-header { padding: 2rem 0 1.75rem; }
    .greeting-text {
        font-size: 2.2rem; font-weight: 700; color: #0f172a;
        letter-spacing: -0.04em; line-height: 1.1; margin-bottom: 0.5rem;
    }
    .greeting-sub { font-size: 1rem; color: #64748b; font-weight: 400; }
    @media (max-width: 768px) {
        .workspace-header { padding: 1.25rem 0 1rem; }
        .greeting-text { font-size: 1.5rem; }
        .greeting-sub { font-size: 0.875rem; }
    }

    /* ── Badges ───────────────────────────────────────── */
    .badge {
        display: inline-flex; align-items: center; gap: 5px;
        padding: 5px 12px; border-radius: 20px;
        font-size: 0.78rem; font-weight: 600; letter-spacing: 0.01em;
    }
    .badge-ct { background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .badge-pm { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
    @media (max-width: 768px) {
        .badge {
            font-size: 0.7rem;
            padding: 4px 10px;
            background: #ffffff !important;
            border: 1.5px solid !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .badge-ct {
            color: #1e40af !important;
            border-color: #3b82f6 !important;
        }
        .badge-pm {
            color: #059669 !important;
            border-color: #10b981 !important;
        }
    }
    @media (max-width: 480px) {
        .badge { font-size: 0.65rem; padding: 3px 8px; }
    }

    /* ── Section label ────────────────────────────────── */
    .section-label {
        font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em;
        text-transform: uppercase; color: #a8a29e; margin: 1.5rem 0 0.75rem;
    }

    /* ── Example question buttons ─────────────────────── */
    div[data-testid="column"] .stButton > button {
        background: #ffffff; border: 1px solid #e8e5e0; border-radius: 14px;
        padding: 1rem 1.125rem; text-align: left; height: auto; min-height: 72px;
        font-size: 0.875rem; color: #374151; font-weight: 500;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05); transition: all 0.15s ease;
        white-space: normal; line-height: 1.5; width: 100%;
    }
    div[data-testid="column"] .stButton > button:hover {
        border-color: #d4c9b8; background: #fdf8f3;
        box-shadow: 0 3px 10px rgba(0,0,0,0.08);
        transform: translateY(-1px); color: #1a1a1a;
    }
    @media (max-width: 768px) {
        div[data-testid="column"] .stButton > button {
            min-height: 56px; font-size: 0.82rem; padding: 0.75rem 0.875rem;
            border-radius: 10px; background: #ffffff !important;
            border: 1px solid #e8e5e0 !important; color: #374151 !important;
            margin-bottom: 0.5rem;
        }
        div[data-testid="column"] .stButton > button:active {
            background: #fdf8f3 !important;
            border-color: #d4c9b8 !important;
            transform: scale(0.98);
        }
    }
    @media (max-width: 480px) {
        div[data-testid="column"] .stButton > button {
            min-height: 52px; font-size: 0.78rem;
            padding: 0.625rem 0.75rem; border-radius: 8px;
        }
    }

    /* ── Message cards ────────────────────────────────── */
    [data-testid="stChatMessage"] {
        background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        padding: 1rem 1.25rem !important; margin-bottom: 0.75rem;
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: #eff6ff; border-color: #bfdbfe;
    }
    @media (max-width: 768px) {
        [data-testid="stChatMessage"] {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px;
            padding: 0.75rem 0.875rem !important;
            margin: 0 0.25rem 0.5rem 0.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background: #f8fafc !important;
            border-color: #cbd5e1 !important;
        }
        /* Force text colors on mobile */
        [data-testid="stChatMessage"] * {
            color: #1e293b !important;
        }
        [data-testid="stChatMessage"] a {
            color: #2563eb !important;
        }
    }
    @media (max-width: 480px) {
        [data-testid="stChatMessage"] {
            padding: 0.625rem 0.75rem !important;
            margin: 0 0.125rem 0.375rem 0.125rem;
            border-radius: 10px;
        }
    }

    /* ── Compact header ───────────────────────────────── */
    .compact-header {
        display: flex; align-items: center; gap: 0.625rem;
        padding: 0.25rem 0 0.875rem; flex-wrap: wrap;
    }
    .compact-title {
        font-size: 1.05rem; font-weight: 700; color: #0f172a;
        letter-spacing: -0.015em; margin-right: 0.25rem;
    }
    @media (max-width: 768px) {
        .compact-header {
            padding: 0.5rem 0.5rem 0.75rem;
            background: #ffffff;
            border-radius: 10px;
            margin: 0.25rem 0.25rem 0.75rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            border: 1px solid #e2e8f0;
            gap: 0.5rem;
        }
        .compact-title {
            font-size: 0.9rem;
            color: #1e293b !important;
        }
    }
    @media (max-width: 480px) {
        .compact-header {
            padding: 0.375rem 0.5rem 0.5rem;
            margin: 0.125rem 0.125rem 0.5rem;
        }
        .compact-title { font-size: 0.85rem; }
    }

    /* ── Tables in chat ───────────────────────────────── */
    [data-testid="stChatMessage"] table {
        display: block; overflow-x: auto; white-space: nowrap;
        border-collapse: collapse; font-size: 0.85rem; margin: 0.5rem 0;
    }
    [data-testid="stChatMessage"] table th {
        background: #f8fafc; padding: 7px 14px; text-align: left;
        font-weight: 600; font-size: 0.8rem; color: #475569;
        border-bottom: 1.5px solid #e2e8f0;
    }
    [data-testid="stChatMessage"] table td {
        padding: 7px 14px; border-bottom: 1px solid #f1f5f9; color: #334155;
    }
    [data-testid="stChatMessage"] table tr:last-child td { border-bottom: none; }

    /* ── Copy response block ──────────────────────────── */
    [data-testid="stChatMessage"] [data-testid="stExpander"] pre {
        background: #f8fafc !important; color: #475569 !important;
        font-family: inherit !important; font-size: 0.85rem !important;
        white-space: pre-wrap !important; word-break: break-word !important;
    }

    /* ── Toolbar hidden ───────────────────────────────── */
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }

    /* ── Sidebar ──────────────────────────────────────── */
    [data-testid="stSidebar"] { background: #faf9f7; border-right: 1px solid #e8e5e0; }

    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            background: #f8fafc !important;
            border-right: 1px solid #e2e8f0 !important;
        }
        [data-testid="stSidebar"] * {
            color: #1e293b !important;
        }
        [data-testid="stSidebar"] .stMarkdown h2 {
            color: #1e293b !important;
            font-size: 1rem !important;
        }
        [data-testid="stSidebar"] .stButton > button {
            background: #ffffff !important;
            color: #374151 !important;
            border: 1px solid #d1d5db !important;
            font-size: 0.8rem !important;
        }
        [data-testid="stSidebar"] .stDownloadButton > button {
            background: #3b82f6 !important;
            color: #ffffff !important;
            border: none !important;
        }
    }

    /* ── Mobile Input Enhancements ────────────────────── */
    @media (max-width: 768px) {
        [data-testid="stChatInput"] {
            background: #ffffff !important;
            border-radius: 12px !important;
            border: 1.5px solid #d1d5db !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        }
        [data-testid="stChatInput"] input {
            color: #1e293b !important;
            font-size: 0.9rem !important;
            padding: 0.75rem !important;
        }
        [data-testid="stChatInput"] input::placeholder {
            color: #6b7280 !important;
        }
        /* Chat input container */
        [data-testid="stChatInputContainer"] {
            background: #f8fafc !important;
            padding: 0.75rem 0.5rem !important;
        }
    }

    /* ── Source pills ─────────────────────────────────── */
    .source-pill {
        display: inline-flex; align-items: center;
        padding: 3px 10px; border-radius: 20px;
        font-size: 0.72rem; font-weight: 600; margin-right: 4px;
    }
    .pill-ct { background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .pill-pm { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }

    /* ── Mobile Status & Expanders ─────────────────────── */
    @media (max-width: 768px) {
        .source-pill {
            background: #ffffff !important;
            border: 1px solid !important;
            font-size: 0.65rem;
            padding: 2px 8px;
        }
        .pill-ct {
            color: #1e40af !important;
            border-color: #3b82f6 !important;
        }
        .pill-pm {
            color: #059669 !important;
            border-color: #10b981 !important;
        }

        /* Expander improvements */
        [data-testid="stExpander"] {
            background: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
        }
        [data-testid="stExpander"] summary {
            background: #ffffff !important;
            color: #374151 !important;
            font-size: 0.8rem !important;
            padding: 0.5rem !important;
        }
        [data-testid="stExpander"] div {
            background: #f8fafc !important;
            color: #4b5563 !important;
        }

        /* Status indicators */
        [data-testid="stStatus"] {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        }
        [data-testid="stStatus"] * {
            color: #374151 !important;
        }
    }

    /* ── Sidebar enterprise elements ─────────────────── */
    .src-status { display:flex; align-items:center; gap:0.5rem; padding:0.25rem 0; font-size:0.82rem; }
    .src-dot { color:#16a34a; font-size:0.55rem; flex-shrink:0; }
    .src-name { color:#334155; font-weight:500; flex:1; }
    .src-conn { color:#16a34a; font-size:0.72rem; font-weight:600; }
    .hist-item { font-size:0.73rem; color:#64748b; padding:0.15rem 0.5rem; border-left:2px solid #e2e8f0; margin:0.15rem 0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    </style>
    """,
    unsafe_allow_html=True,
)

agent, all_tools = get_agent()

_PROFILE_FIRST_NAME = "Alex"
_hour = datetime.now().hour
_greeting = f"Good {'morning' if _hour < 12 else 'afternoon' if _hour < 17 else 'evening'}, {_PROFILE_FIRST_NAME}."

# ── Question pool ─────────────────────────────────────────────────────────────
_QUESTION_POOL = [
    ("🏥 + 📚", "What do we know about semaglutide for Type 2 Diabetes? Show trials and evidence."),
    ("🏥", "Find Phase 3 trials currently recruiting for Alzheimer's disease"),
    ("📚", "What does published literature say about CAR-T therapy safety?"),
    ("🏥 + 📚", "Are there trials for heart failure with HFpEF, and what results have been published?"),
    ("🏥", "What CRISPR gene therapy trials are currently active?"),
    ("📚", "Summarise recent meta-analyses on immunotherapy for lung cancer"),
    ("🏥 + 📚", "What do we know about GLP-1 agonists for obesity? Show trials and key papers."),
    ("🏥", "Find recruiting trials for Parkinson's disease in Phase 2 or 3"),
    ("📚", "What does the literature say about long COVID treatment outcomes?"),
    ("🏥 + 📚", "Are there trials for ALS, and what have completed trials shown?"),
    ("🏥", "Which trials are studying mRNA vaccines beyond COVID-19?"),
    ("📚", "What are the published safety findings for CAR-T in paediatric ALL?"),
    ("🏥 + 📚", "Overview of clinical research on psoriasis biologics — trials and evidence"),
    ("🏥", "Find trials studying ketamine or esketamine for treatment-resistant depression"),
    ("📚", "Recent systematic reviews on aspirin for cardiovascular prevention"),
    ("🏥 + 📚", "What is the current evidence on stem cell therapy for multiple sclerosis?"),
]

# ── Session state ─────────────────────────────────────────────────────────────
if "lc_messages" not in st.session_state:
    st.session_state.lc_messages = []
if "chat_display" not in st.session_state:
    st.session_state.chat_display = []
if "queued_prompt" not in st.session_state:
    st.session_state.queued_prompt = None
if "example_questions" not in st.session_state:
    st.session_state.example_questions = random.sample(_QUESTION_POOL, 4)
if "session_restored" not in st.session_state:
    st.session_state.session_restored = False

# ── Restore history from localStorage (runs every render; restores once) ─────
_ls_value = st_javascript(f"(window.parent||window).localStorage.getItem('{_LS_KEY}') || 'null'")
if (isinstance(_ls_value, str)
        and _ls_value not in ("null", "undefined", "")
        and not st.session_state.session_restored
        and not st.session_state.chat_display):
    try:
        _saved = json.loads(_ls_value)
        if _saved:
            st.session_state.chat_display = _saved
            st.session_state.lc_messages = _build_clean_messages(_saved)
            st.session_state.session_restored = True
            st.rerun()
    except Exception:
        pass

# Save history on every render so it's always up-to-date when user refreshes
if st.session_state.chat_display:
    _save_session(st.session_state.chat_display)

# Clear localStorage on the render AFTER clear is clicked (iframe survives without an immediate rerun)
if st.session_state.pop("clear_storage", False):
    _clear_session_storage()

# Init parent window: disable scroll restoration + scroll to top (runs once per browser session)
st.components.v1.html(_INIT_PARENT, height=0)

# Enterprise ribbon — injected once into parent window, persists across rerenders
st.components.v1.html(_ENTERPRISE_RIBBON, height=0)

# Play done chime on the rerun that follows agent completion
if st.session_state.pop("play_done_sound", False):
    _play(_SOUND_DONE)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    ct_tools = [t for t in all_tools if _is_ct_tool(t.name)]
    pm_tools = [t for t in all_tools if t not in ct_tools]

    st.markdown("**Data Sources**")
    st.markdown(
        '<div class="src-status"><span class="src-dot">●</span>'
        '<span class="src-name">ClinicalTrials.gov</span>'
        '<span class="src-conn">● Live</span></div>'
        '<div class="src-status"><span class="src-dot">●</span>'
        '<span class="src-name">PubMed</span>'
        '<span class="src-conn">● Live</span></div>',
        unsafe_allow_html=True,
    )

    st.divider()

    user_queries = [m["content"] for m in st.session_state.chat_display if m["role"] == "user"]
    if user_queries:
        st.markdown(f"**Session History** · {len(user_queries)}")
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
        st.markdown("**Retrieved Sources**")
        for nct in session_nct[:5]:
            st.markdown(f"🏥 [{nct}](https://clinicaltrials.gov/study/{nct})")
        for pmid in session_pm[:5]:
            st.markdown(f"📚 [PMID {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")
        st.divider()

    has_chat = bool(st.session_state.chat_display)
    st.download_button(
        label="📄 Export session",
        data=_build_html_export(st.session_state.chat_display) if has_chat else " ",
        file_name=f"research_session_{date.today().isoformat()}.html",
        mime="text/html",
        use_container_width=True,
        disabled=not has_chat,
    )
    if has_chat:
        st.caption("Open in browser → Ctrl+P → Save as PDF")

    st.divider()
    if st.button("🗑️ Clear session", use_container_width=True):
        st.session_state.lc_messages = []
        st.session_state.chat_display = []
        st.session_state.session_restored = True
        st.session_state.example_questions = random.sample(_QUESTION_POOL, 4)
        st.session_state.clear_storage = True
        st.rerun()

# ── Hero (empty) / Compact header (active) ────────────────────────────────────
if not st.session_state.chat_display:
    st.components.v1.html(_SCROLL_BTN_HIDE, height=0)
    st.markdown(
        f'<div class="workspace-header">'
        f'<div class="greeting-text">{_greeting}</div>'
        f'<div class="greeting-sub">Your clinical research workspace is ready.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">Try asking</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    for i, (badge, ex) in enumerate(st.session_state.example_questions):
        col = col1 if i % 2 == 0 else col2
        if col.button(ex, use_container_width=True, key=f"ex{i}"):
            st.session_state.queued_prompt = ex
            st.rerun()

else:
    st.components.v1.html(_SCROLL_BTN_SHOW, height=0)
    st.markdown(
        '<div class="compact-header">'
        '<span class="badge badge-ct">🏥 ClinicalTrials.gov</span>'
        '<span class="badge badge-pm">📚 PubMed</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    for item_idx, item in enumerate(st.session_state.chat_display):
        with st.chat_message(item["role"], avatar="🧬" if item["role"] == "assistant" else None):
            if item.get("tools_used"):
                tool_sources = set()
                for t in item["tools_used"]:
                    if _is_ct_tool(t):
                        tool_sources.add("ct")
                    else:
                        tool_sources.add("pm")

                label = {
                    frozenset({"ct"}): "🏥 ClinicalTrials only",
                    frozenset({"pm"}): "📚 PubMed only",
                    frozenset({"ct", "pm"}): "🏥 ClinicalTrials + 📚 PubMed",
                }.get(frozenset(tool_sources), f"{len(item['tools_used'])} tool call(s)")

                with st.expander(label):
                    for t in item["tools_used"]:
                        st.code(f"{_source_badge(t)}  {t}", language="text")

            st.markdown(item["content"])

            if item.get("sources"):
                _render_sources(item["sources"])

            if item["role"] == "assistant" and item.get("content"):
                _copy_button(item["content"])

# ── Input ─────────────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask about clinical trials, published research, or both...")
if not prompt and st.session_state.queued_prompt:
    prompt = st.session_state.queued_prompt
    st.session_state.queued_prompt = None

# ── Agent invocation ──────────────────────────────────────────────────────────
if prompt:
    _play(_SOUND_SEND)
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_display.append({"role": "user", "content": prompt})
    st.session_state.lc_messages.append(HumanMessage(content=prompt))

    # ── Classify intent before routing ────────────────────────────────────────
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

    with st.chat_message("assistant", avatar="🧬"):
        response_placeholder = st.empty()

        if intent == "followup":
            full_response = run_direct(
                _build_clean_messages(st.session_state.chat_display),
                response_placeholder,
            )
            tools_called, sources, result = [], set(), None
        else:
            status_container = st.status("Researching...", expanded=True)
            result, tools_called, full_response, sources = run_agent(
                st.session_state.lc_messages, status_container, response_placeholder
            )
            if not full_response and result is None:
                st.error("Agent returned no response. Please try again.")
            if sources:
                _render_sources(sources)

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
