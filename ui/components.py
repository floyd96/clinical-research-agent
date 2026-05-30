"""
Reusable UI components and JS/HTML snippets.

All Streamlit calls are inside functions — nothing executes at import time.
"""

import html as _html
import json
import re
from datetime import date

import streamlit as st

from config import (
    LS_KEY, BRAND_NAME, COLOR_PRIMARY,
    COLOR_CT_TEXT, COLOR_CT_BORDER,
    COLOR_PM_TEXT, COLOR_PM_BORDER,
)

# ── Audio snippets (Web Audio API — zero dependencies) ───────────────────────

SOUND_SEND = """
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

SOUND_DONE = """
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

# ── Layout / scroll helpers ───────────────────────────────────────────────────

INIT_PARENT = """
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

SCROLL_BTN_SHOW = """
<script>
(function(){
    var p = window.parent;
    if (!p || p.document.getElementById('cri-scroll-btn')) return;
    var btn = p.document.createElement('button');
    btn.id = 'cri-scroll-btn';
    btn.title = 'Scroll to bottom';
    btn.innerHTML = '&#8595;';
    btn.style.cssText = 'position:fixed;bottom:90px;right:20px;width:40px;height:40px;'
        + 'border-radius:50%;background:__COLOR__;color:#fff;border:2px solid rgba(255,255,255,0.7);cursor:pointer;'
        + 'font-size:20px;font-weight:700;box-shadow:0 3px 14px rgba(14,50,147,0.45);'
        + 'z-index:99999;opacity:0.95;transition:opacity 0.2s;';
    btn.onmouseover = function(){ btn.style.opacity='1'; };
    btn.onmouseout  = function(){ btn.style.opacity='0.82'; };
    btn.onclick = function(){
        var doc = p.document;
        var best = null; var bestH = 0;
        doc.querySelectorAll('section, div, main, article').forEach(function(el){
            var ov = p.getComputedStyle(el).overflowY;
            if ((ov === 'auto' || ov === 'scroll') && el.scrollHeight > bestH) {
                bestH = el.scrollHeight; best = el;
            }
        });
        if (best) { best.scrollTop = best.scrollHeight; }
        ['[data-testid="stAppViewContainer"]','[data-testid="stMain"]','.main'].forEach(function(s){
            var el = doc.querySelector(s);
            if (el) el.scrollTop = el.scrollHeight;
        });
        p.scrollTo(0, doc.documentElement.scrollHeight);
    };
    p.document.body.appendChild(btn);
})();
</script>
""".replace("__COLOR__", COLOR_PRIMARY)

SCROLL_BTN_HIDE = """
<script>
(function(){
    var p = window.parent;
    var btn = p && p.document.getElementById('cri-scroll-btn');
    if (btn) btn.remove();
})();
</script>
"""


def get_ribbon_js() -> str:
    """Enterprise ribbon — Mayo branding, no fake user persona."""
    return f"""
<script>
(function(){{
    var p = window.parent;
    if (!p || p.document.getElementById('ent-ribbon')) return;
    var el = p.document.createElement('div');
    el.id = 'ent-ribbon';
    el.className = 'ent-ribbon';
    el.innerHTML = '<div class="ent-ribbon-left">'
        + '<span class="ent-brand">{BRAND_NAME}</span>'
        + '</div>';
    p.document.body.prepend(el);
}})();
</script>
"""


# ── Streamlit component helpers ───────────────────────────────────────────────

def play(sound_html: str) -> None:
    st.components.v1.html(sound_html, height=0)


def copy_button(text: str) -> None:
    clean = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    clean = re.sub(r'\*(.+?)\*',     r'\1', clean)
    clean = re.sub(r'^#{1,6}\s+',    '',    clean, flags=re.MULTILINE)
    clean = re.sub(r'^\|.*\|$',      '',    clean, flags=re.MULTILINE)
    clean = re.sub(r'^[-| :]+$',     '',    clean, flags=re.MULTILINE)
    clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean)
    clean = re.sub(r'\n{3,}', '\n\n', clean).strip()
    with st.expander("📋 Copy response"):
        st.code(clean, language=None, wrap_lines=True)


def render_sources(sources: list) -> None:
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


def save_session(chat_display: list) -> None:
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
            (window.parent||window).localStorage.setItem('{LS_KEY}',v);
        }}catch(e){{}}
        </script>""",
        height=0,
    )


def clear_session_storage() -> None:
    st.components.v1.html(
        f"<script>try{{(window.parent||window).localStorage.removeItem('{LS_KEY}');}}catch(e){{}}</script>",
        height=0,
    )


# ── HTML export ───────────────────────────────────────────────────────────────

def _md_to_html_body(text: str) -> str:
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for n in (3, 2, 1):
        t = re.sub(rf'^{"#"*n} (.+)$', rf'<h{n}>\1</h{n}>', t, flags=re.MULTILINE)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\*(.+?)\*',     r'<em>\1</em>',         t)
    t = re.sub(r'`(.+?)`',       r'<code>\1</code>',      t)
    t = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', t)

    def _table(m):
        rows = [r for r in m.group(0).splitlines() if r.strip() and not re.match(r'^\|[-| ]+\|$', r.strip())]
        html = "<table>"
        for i, row in enumerate(rows):
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            tag = "th" if i == 0 else "td"
            html += "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"
        return html + "</table>"

    t = re.sub(r'(\|.+\|\n?)+', _table, t)
    t = re.sub(r'^---+$', '<hr>', t, flags=re.MULTILINE)
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


def build_html_export(chat_display: list) -> str:
    css = f"""
    body {{ font-family: Arial, sans-serif; max-width: 820px;
           margin: 40px auto; color: #1e293b; line-height: 1.6; }}
    h1 {{ color: {COLOR_PRIMARY}; font-size: 1.4rem; margin-bottom: 4px;
          font-family: Calibri, Arial, sans-serif; }}
    .meta {{ color: #64748b; font-size: 0.85rem; margin-bottom: 2rem; }}
    hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 2rem 0; }}
    .question {{ background: #dbeafe; border-radius: 8px; padding: 12px 16px;
                color: {COLOR_PRIMARY}; font-weight: 600; margin: 1.5rem 0 0.5rem; }}
    .answer   {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px;
                padding: 16px 20px; margin-bottom: 0.5rem; }}
    .sources  {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
                padding: 10px 14px; font-size: 0.82rem; color: #64748b; margin-top: 6px; }}
    .sources a {{ color: {COLOR_PRIMARY}; text-decoration: none; }}
    table {{ border-collapse: collapse; width: 100%; margin: 0.75rem 0; font-size: 0.875rem; }}
    th {{ background: #f1f5f9; padding: 6px 12px; text-align: left;
         font-weight: 600; border-bottom: 2px solid #e2e8f0;
         font-family: Calibri, Arial, sans-serif; }}
    td {{ padding: 6px 12px; border-bottom: 1px solid #f1f5f9; }}
    code {{ background: #f1f5f9; padding: 1px 5px; border-radius: 4px; font-size: 0.85em; }}
    @media print {{ body {{ margin: 20px; }} }}
    """
    body_parts = [
        f'<h1>Mayo Clinic Research Assistant</h1>',
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
                body_parts.append(
                    f'<div class="sources"><strong>Sources:</strong> {"&nbsp;&nbsp;".join(links)}</div>'
                )

    return (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>Mayo Clinic Research Assistant — Session Report</title>"
        f"<style>{css}</style></head><body>{''.join(body_parts)}</body></html>"
    )
