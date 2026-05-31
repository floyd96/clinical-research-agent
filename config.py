# ── MCP endpoints ─────────────────────────────────────────────────────────────
CLINICALTRIALS_MCP_URL = "https://clinicaltrials.caseyjhand.com/mcp"
PUBMED_MCP_URL         = "https://pubmed.caseyjhand.com/mcp"

# ── Model configuration ───────────────────────────────────────────────────────
MODEL_ID               = "gpt-4o-mini"               # OpenAI — main agent
MAIN_MAX_TOKENS        = 2048

# ── Beta access whitelist ─────────────────────────────────────────────────────
BETA_WHITELIST: list[str] = [
    "swapno777@gmail.com",
    # add up to 19 more addresses here
]
