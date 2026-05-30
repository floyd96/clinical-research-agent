"""
Suggested search pool — 16 questions shown 4 at a time on the welcome screen.

Covers the full spectrum of available tools across both data sources.
Contextualized for Mayo investigators, research coordinators, and clinicians.

Badge key:
  "🏥"        → ClinicalTrials.gov tools only
  "📚"        → PubMed tools only
  "🏥 + 📚"  → Combined query across both sources
"""

QUESTION_POOL = [
    # ── Research coordinator: eligibility matching ────────────────────────────
    (
        "🏥",
        "Which recruiting trials could a 65-year-old patient with treatment-resistant "
        "hypertension and no prior biologics be eligible for?",
    ),
    (
        "🏥",
        "Find trials a 52-year-old woman with early-stage ovarian cancer and a BRCA1 "
        "mutation could qualify for.",
    ),

    # ── Research coordinator: landscape and counts ────────────────────────────
    (
        "🏥",
        "How many Phase 2 and Phase 3 trials are currently recruiting for pancreatic "
        "cancer in the United States?",
    ),
    (
        "🏥",
        "Which sponsors and institutions are most active in Alzheimer's disease trial "
        "research, and what phases are they running?",
    ),

    # ── Completed trial results ───────────────────────────────────────────────
    (
        "🏥",
        "What outcomes did completed Phase 3 trials for semaglutide in cardiovascular "
        "risk reduction report?",
    ),
    (
        "🏥 + 📚",
        "What have completed CAR-T trials for diffuse large B-cell lymphoma reported, "
        "and what does the published literature show on long-term outcomes?",
    ),

    # ── Clinical researcher: literature depth ─────────────────────────────────
    (
        "📚",
        "Get the full text of the most recent systematic review on checkpoint inhibitor "
        "toxicity in solid tumors.",
    ),
    (
        "📚",
        "Find papers related to the landmark CAR-T trial results in paediatric ALL — "
        "what else has been published in this area?",
    ),
    (
        "📚",
        "Are there preprints or ahead-of-print studies on long COVID neurological outcomes?",
    ),
    (
        "📚",
        "Give me APA citations for the top three papers on GLP-1 agonists and "
        "cardiovascular outcomes.",
    ),

    # ── Clinician: combined fast answers ─────────────────────────────────────
    (
        "🏥 + 📚",
        "What do we know about semaglutide for Type 2 Diabetes — active trials and "
        "published evidence?",
    ),
    (
        "🏥 + 📚",
        "Overview of CAR-T therapy in paediatric ALL — trial eligibility, safety "
        "findings, and recent literature.",
    ),
    (
        "🏥 + 📚",
        "Are there active trials for HFpEF, and what have completed trials and "
        "published studies reported?",
    ),

    # ── Advanced research intelligence ────────────────────────────────────────
    (
        "📚",
        "What is the official MeSH classification for HFpEF, and what related terms "
        "should I use in a literature search?",
    ),
    (
        "🏥",
        "What phases and locations dominate current CRISPR gene therapy trial activity "
        "globally?",
    ),
    (
        "🏥 + 📚",
        "Compare the trial landscape and published outcomes for SGLT2 inhibitors in "
        "heart failure.",
    ),

    # ── Competitive landscape ─────────────────────────────────────────────
    (
        "🏥 + 📚",
        "Competitive landscape for checkpoint inhibitors in NSCLC — which sponsors lead "
        "trial activity and what does the published evidence show?",
    ),
    (
        "🏥",
        "Which sponsors and institutions dominate Alzheimer's disease trial activity "
        "globally, and what phases are they running?",
    ),
]
