# ── MCP endpoints ─────────────────────────────────────────────────────────────
CLINICALTRIALS_MCP_URL = "https://clinicaltrials.caseyjhand.com/mcp"
PUBMED_MCP_URL         = "https://pubmed.caseyjhand.com/mcp"

# ── Model configuration ───────────────────────────────────────────────────────
MODEL_ID               = "Qwen/Qwen2.5-72B-Instruct"
MAIN_MAX_TOKENS        = 2048
CLASSIFIER_MAX_TOKENS  = 5

# ── Brand identity ────────────────────────────────────────────────────────────
BRAND_TAGLINE          = "Clinical research intelligence for Mayo investigators and coordinators."

# ── Beta access whitelist ─────────────────────────────────────────────────────
BETA_WHITELIST: list[str] = [
    "swapno777@gmail.com",
    # add up to 19 more addresses here
]
