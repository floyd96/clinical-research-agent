import asyncio
import queue as q_module
import random
import re
import threading
from datetime import date
import streamlit as st
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from research_agent import CLINICALTRIALS_MCP_URL, PUBMED_MCP_URL, SYSTEM_PROMPT, model

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

def _play(sound_html: str):
    st.components.v1.html(sound_html, height=0)


def _copy_button(text: str, key: str):
    """Render a copy area using Streamlit's native code block (clipboard-safe)."""
    clean = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    clean = re.sub(r'\*(.+?)\*',     r'\1', clean)
    clean = re.sub(r'^#{1,6}\s+',    '',    clean, flags=re.MULTILINE)
    clean = re.sub(r'^\|.*\|$',      '',    clean, flags=re.MULTILINE)
    clean = re.sub(r'^[-| :]+$',     '',    clean, flags=re.MULTILINE)
    clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean).strip()
    with st.expander("📋 Copy response"):
        st.code(clean, language=None, wrap_lines=True)

# One persistent event loop so the async HTTP pool is never tied to a closed loop.
_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()


def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _loop).result()


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


def _md_to_html_body(text: str) -> str:
    """Convert a subset of markdown to HTML — no external library needed."""
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

    /* ── Global font ──────────────────────────────────── */
    html, body, [class*="css"], .stMarkdown, button, input, textarea {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }

    /* ── Layout ──────────────────────────────────────── */
    [data-testid="stMainBlockContainer"] {
        max-width: 840px;
        margin: 0 auto;
        padding: 1.5rem 2rem 6rem;
    }
    @media (max-width: 768px) {
        [data-testid="stMainBlockContainer"] { padding: 1rem 1rem 5rem; }
    }
    @media (max-width: 480px) {
        [data-testid="stMainBlockContainer"] { padding: 0.75rem 0.75rem 5rem; }
    }

    /* ── Background ───────────────────────────────────── */
    [data-testid="stMain"] { background: #f1f5f9; }
    .hero, .cap-grid { position: relative; z-index: 1; }

    /* ── Hero ─────────────────────────────────────────── */
    .hero { text-align: center; padding: 3rem 1rem 1.75rem; }
    .hero-icon { font-size: 3rem; line-height: 1; margin-bottom: 0.75rem; }
    .hero-title {
        font-size: 1.875rem; font-weight: 700; color: #0f172a;
        letter-spacing: -0.03em; margin-bottom: 0.5rem;
    }
    .hero-sub {
        font-size: 1rem; color: #64748b;
        max-width: 420px; margin: 0 auto 1.5rem; line-height: 1.65;
    }
    .hero-badges { display: flex; justify-content: center; gap: 0.5rem; flex-wrap: wrap; }
    @media (max-width: 640px) {
        .hero { padding: 2rem 0.5rem 1.25rem; }
        .hero-icon { font-size: 2.5rem; }
        .hero-title { font-size: 1.45rem; }
        .hero-sub { font-size: 0.9rem; }
    }

    /* ── Badges ───────────────────────────────────────── */
    .badge {
        display: inline-flex; align-items: center; gap: 5px;
        padding: 5px 12px; border-radius: 20px;
        font-size: 0.78rem; font-weight: 600; letter-spacing: 0.01em;
    }
    .badge-ct { background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .badge-pm { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
    @media (max-width: 480px) {
        .badge { font-size: 0.72rem; padding: 4px 9px; }
    }

    /* ── Capability cards ─────────────────────────────── */
    .cap-grid { display: flex; gap: 1rem; margin: 1.5rem 0 0; }
    .cap-card {
        flex: 1; background: #ffffff; border: 1.5px solid #e2e8f0;
        border-radius: 16px; padding: 1.25rem 1.375rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .cap-card-icon { font-size: 1.4rem; margin-bottom: 0.5rem; }
    .cap-card-title { font-size: 0.875rem; font-weight: 600; color: #1e293b; margin-bottom: 0.3rem; }
    .cap-card-body { font-size: 0.82rem; color: #64748b; line-height: 1.6; }
    @media (max-width: 580px) { .cap-grid { flex-direction: column; } }

    /* ── Section label ────────────────────────────────── */
    .section-label {
        font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
        text-transform: uppercase; color: #94a3b8; margin: 1.75rem 0 0.75rem;
    }

    /* ── Example question buttons ─────────────────────── */
    div[data-testid="column"] .stButton > button {
        background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px;
        padding: 0.875rem 1rem; text-align: left; height: auto; min-height: 68px;
        font-size: 0.875rem; color: #334155; font-weight: 500;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04); transition: all 0.15s ease;
        white-space: normal; line-height: 1.5; width: 100%;
    }
    div[data-testid="column"] .stButton > button:hover {
        border-color: #3b82f6; background: #eff6ff;
        box-shadow: 0 4px 12px rgba(59,130,246,0.1);
        transform: translateY(-1px); color: #1d4ed8;
    }
    @media (max-width: 580px) {
        div[data-testid="column"] .stButton > button {
            min-height: 56px; font-size: 0.82rem; padding: 0.75rem 0.875rem;
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
    @media (max-width: 640px) {
        [data-testid="stChatMessage"] {
            padding: 0.875rem 0.875rem !important; border-radius: 12px;
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
    @media (max-width: 480px) { .compact-title { font-size: 0.95rem; } }

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
    [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e8ecf0; }

    /* ── Source pills ─────────────────────────────────── */
    .source-pill {
        display: inline-flex; align-items: center;
        padding: 3px 10px; border-radius: 20px;
        font-size: 0.72rem; font-weight: 600; margin-right: 4px;
    }
    .pill-ct { background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .pill-pm { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
    </style>
    """,
    unsafe_allow_html=True,
)

agent, all_tools = get_agent()

# ── Session state ─────────────────────────────────────────────────────────────
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

if "lc_messages" not in st.session_state:
    st.session_state.lc_messages = []
if "chat_display" not in st.session_state:
    st.session_state.chat_display = []
if "queued_prompt" not in st.session_state:
    st.session_state.queued_prompt = None
if "example_questions" not in st.session_state:
    st.session_state.example_questions = random.sample(_QUESTION_POOL, 4)

# Scroll to top on fresh page load / refresh only (not on every rerun)
if "page_loaded" not in st.session_state:
    st.session_state.page_loaded = True
    st.components.v1.html("""
        <script>
        function scrollTop() {
            var p = window.parent;
            p.scrollTo({top: 0, behavior: 'instant'});
            var selectors = [
                '[data-testid="stAppViewContainer"]',
                '[data-testid="stMainBlockContainer"]',
                '.main', 'section.main'
            ];
            selectors.forEach(function(s) {
                var el = p.document.querySelector(s);
                if (el) el.scrollTop = 0;
            });
        }
        setTimeout(scrollTop, 100);
        setTimeout(scrollTop, 400);
        </script>
    """, height=0)

# Play done chime on the rerun that follows agent completion
if st.session_state.pop("play_done_sound", False):
    _play(_SOUND_DONE)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧬 Clinical Research Intelligence")
    st.divider()

    ct_tools = [t for t in all_tools if any(k in t.name.lower() for k in _CT_KEYWORDS)]
    pm_tools = [t for t in all_tools if t not in ct_tools]

    st.markdown("**Connected sources**")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            f'<span class="source-pill pill-ct">🏥 ClinicalTrials</span>'
            f'<br><small>{len(ct_tools)} tools</small>',
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            f'<span class="source-pill pill-pm">📚 PubMed</span>'
            f'<br><small>{len(pm_tools)} tools</small>',
            unsafe_allow_html=True,
        )

    st.divider()

    has_chat = len(st.session_state.chat_display) > 0
    st.download_button(
        label="📄 Export session",
        data=_build_html_export(st.session_state.chat_display) if has_chat else " ",
        file_name=f"research_session_{date.today().isoformat()}.html",
        mime="text/html",
        use_container_width=True,
        disabled=not has_chat,
    )
    if has_chat:
        st.caption("Open the file in a browser → Ctrl+P → Save as PDF")

    st.divider()
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.lc_messages = []
        st.session_state.chat_display = []
        st.session_state.example_questions = random.sample(_QUESTION_POOL, 4)
        st.rerun()

# ── Hero (empty) / Compact header (active) ────────────────────────────────────
if not st.session_state.chat_display:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-icon">🧬</div>
            <div class="hero-title">Clinical Research Intelligence</div>
            <div class="hero-sub">
                Search clinical trials and published literature together —
                get grounded, cited answers in seconds.
            </div>
            <div class="hero-badges">
                <span class="badge badge-ct">🏥 ClinicalTrials.gov</span>
                <span class="badge badge-pm">📚 PubMed</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="cap-grid">
            <div class="cap-card">
                <div class="cap-card-icon">🏥</div>
                <div class="cap-card-title">Clinical Trials</div>
                <div class="cap-card-body">
                    Find active, recruiting, or completed trials.
                    Explore phases, eligibility criteria, sponsors, and locations.
                </div>
            </div>
            <div class="cap-card">
                <div class="cap-card-icon">📚</div>
                <div class="cap-card-title">Published Literature</div>
                <div class="cap-card-body">
                    Discover published results, systematic reviews, and
                    meta-analyses from PubMed's 35M+ articles.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">Try asking</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    for i, (badge, ex) in enumerate(st.session_state.example_questions):
        col = col1 if i % 2 == 0 else col2
        if col.button(f"{badge}  {ex}", use_container_width=True, key=f"ex{i}"):
            st.session_state.queued_prompt = ex
            st.rerun()

else:
    st.markdown(
        '<div class="compact-header">'
        '<span class="compact-title">🧬 Clinical Research Intelligence</span>'
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
                    if any(k in t.lower() for k in _CT_KEYWORDS):
                        tool_sources.add("ct")
                    elif any(k in t.lower() for k in _PM_KEYWORDS):
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
                ct_hist = sorted(i for t, i in item["sources"] if t == "ct")
                pm_hist = sorted(i for t, i in item["sources"] if t == "pm")
                with st.expander(f"📎 {len(item['sources'])} source(s)", expanded=False):
                    if ct_hist:
                        st.markdown("**🏥 ClinicalTrials.gov**")
                        for nct in ct_hist:
                            st.markdown(f"- [{nct}](https://clinicaltrials.gov/study/{nct})")
                    if pm_hist:
                        st.markdown("**📚 PubMed**")
                        for pmid in pm_hist:
                            st.markdown(f"- [PMID {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")

            if item["role"] == "assistant" and item.get("content"):
                _copy_button(item["content"], f"hist_{item_idx}")

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

    with st.chat_message("assistant", avatar="🧬"):
        status_container = st.status("Researching...", expanded=True)
        response_placeholder = st.empty()
        result, tools_called, full_response, sources = run_agent(
            st.session_state.lc_messages, status_container, response_placeholder
        )

        if not full_response and result is None:
            st.error("Agent returned no response. Please try again.")

        if sources:
            ct_sources = sorted(i for t, i in sources if t == "ct")
            pm_sources = sorted(i for t, i in sources if t == "pm")
            with st.expander(f"📎 {len(sources)} source(s)", expanded=False):
                if ct_sources:
                    st.markdown("**🏥 ClinicalTrials.gov**")
                    for nct in ct_sources:
                        st.markdown(f"- [{nct}](https://clinicaltrials.gov/study/{nct})")
                if pm_sources:
                    st.markdown("**📚 PubMed**")
                    for pmid in pm_sources:
                        st.markdown(f"- [PMID {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")

    if result or full_response:
        if result:
            st.session_state.lc_messages = result["messages"]
        st.session_state.chat_display.append({
            "role": "assistant",
            "content": full_response,
            "tools_used": tools_called,
            "sources": list(sources),
        })
        st.session_state.play_done_sound = True
        st.rerun()
