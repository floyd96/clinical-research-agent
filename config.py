# ── MCP endpoints ─────────────────────────────────────────────────────────────
CLINICALTRIALS_MCP_URL = "https://clinicaltrials.caseyjhand.com/mcp"
PUBMED_MCP_URL         = "https://pubmed.caseyjhand.com/mcp"

# ── Model configuration ───────────────────────────────────────────────────────
MODEL_ID               = "Qwen/Qwen2.5-72B-Instruct"
MAIN_MAX_TOKENS        = 2048
CLASSIFIER_MAX_TOKENS  = 5

# ── Mayo Clinic brand colors ──────────────────────────────────────────────────
# Source: Mayo Clinic Design Guide — Visual Identity System
COLOR_PRIMARY          = "#0E3293"   # Mayo deep blue — ribbon, primary actions, trust markers
COLOR_SECONDARY        = "#4F81BD"   # Mayo medium blue — secondary elements, headings
COLOR_NAVY             = "#1F497D"   # Deep navy — dark accents
COLOR_TEAL             = "#4BACC6"   # Teal — secondary highlight (PubMed badge, accents)
COLOR_YELLOW           = "#F79646"   # Warm amber — caution / notice only
COLOR_BG               = "#EEECE1"   # Warm off-white — page background
COLOR_SURFACE          = "#FFFFFF"   # Card / panel surface
COLOR_BORDER           = "#E2E8F0"   # Neutral border
COLOR_TEXT_BODY        = "#1e293b"   # Body text
COLOR_TEXT_MUTED       = "#64748b"   # Secondary / muted text
COLOR_USER_MSG_BG      = "#f1f5f9"   # User message bubble background — neutral, not blue (blue = links only)
COLOR_USER_MSG_BORDER  = "#e2e8f0"   # User message bubble border

# CT badge — Mayo blue family
COLOR_CT_BG            = "#dbeafe"
COLOR_CT_TEXT          = "#1F497D"
COLOR_CT_BORDER        = "#4F81BD"

# PM badge — Mayo teal family (never green)
COLOR_PM_BG            = "#e6f4f7"
COLOR_PM_TEXT          = "#1a5f6e"
COLOR_PM_BORDER        = "#4BACC6"

# ── Typography ────────────────────────────────────────────────────────────────
FONT_BODY              = "Arial, -apple-system, BlinkMacSystemFont, sans-serif"
FONT_HEADING           = "Calibri, Arial, -apple-system, sans-serif"

# ── Brand identity ────────────────────────────────────────────────────────────
BRAND_NAME             = "Mayo Clinic Research Assistant"
BRAND_TAGLINE          = "Clinical research intelligence for Mayo investigators and coordinators."
PAGE_TITLE             = "Mayo Clinic Research Assistant"
PAGE_ICON              = "🏥"

# ── UI copy strings ───────────────────────────────────────────────────────────
CHAT_PLACEHOLDER       = "Enter a condition, drug, trial ID, or research question…"
STATUS_RETRIEVING      = "Retrieving results…"
SECTION_SUGGESTIONS    = "Suggested searches"
EXPORT_BUTTON_LABEL    = "Export session report"
CLEAR_BUTTON_LABEL     = "New session"
SIDEBAR_SOURCES_HDR    = "Data Sources"
SIDEBAR_HISTORY_HDR    = "Query History"
SIDEBAR_RETRIEVED_HDR  = "Retrieved Sources"
EXPORT_PDF_TIP         = "To save as PDF: open in browser and select Print → Save as PDF."

# ── Session storage key ───────────────────────────────────────────────────────
LS_KEY                 = "cri_session"
