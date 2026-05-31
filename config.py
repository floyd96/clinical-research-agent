# ── MCP endpoints ─────────────────────────────────────────────────────────────
CLINICALTRIALS_MCP_URL = "https://clinicaltrials.caseyjhand.com/mcp"
PUBMED_MCP_URL         = "https://pubmed.caseyjhand.com/mcp"

# ── Model configuration ───────────────────────────────────────────────────────
MODEL_ID               = "llama-3.3-70b-versatile"   # Groq — main agent
CLASSIFIER_MODEL_ID    = "llama-3.1-8b-instant"      # Groq — one-word intent classifier
MAIN_MAX_TOKENS        = 2048
CLASSIFIER_MAX_TOKENS  = 5

# ── Brand identity ────────────────────────────────────────────────────────────
BRAND_TAGLINE          = "Clinical research intelligence for Mayo investigators and coordinators."

# ── Beta access whitelist ─────────────────────────────────────────────────────
BETA_WHITELIST: list[str] = [
    "swapno777@gmail.com",
    # add up to 19 more addresses here
]
