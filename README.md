# 🧬 Clinical Research Intelligence Agent

An AI-powered research assistant that searches **ClinicalTrials.gov** and **PubMed** simultaneously, delivering grounded, cited answers about clinical trials and published biomedical literature.

## Features

- **Dual-source search** — queries ClinicalTrials.gov and PubMed in a single conversation
- **Token streaming** — responses appear in real time as they generate
- **Structured output** — trial cards (NCT ID, phase, status, eligibility) and paper cards (PMID, authors, key finding)
- **Source grounding** — every response includes a verified sources panel with clickable links (NCT IDs and PMIDs extracted directly from tool outputs, not from the model)
- **Session export** — download the full conversation as a styled HTML report (printable to PDF)
- **Live tool status** — see which database is being queried in real time
- **Randomised example questions** — welcome screen rotates 4 questions from a pool of 16 on each session

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Qwen/Qwen2.5-72B-Instruct via HuggingFace Serverless Inference API |
| Agent framework | LangChain / LangGraph ReAct agent |
| Data sources | ClinicalTrials.gov MCP · PubMed MCP (Model Context Protocol) |
| UI | Streamlit |
| Hosting | Streamlit Community Cloud |

## Local Setup

**Prerequisites:** Python 3.10+, a [HuggingFace account](https://huggingface.co) with a token

```bash
# 1. Clone the repo
git clone https://github.com/metafloyd/clinical-research-agent.git
cd clinical-research-agent

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your HuggingFace token
cp .env.example .env
# Edit .env and set HF_TOKEN=hf_your_token_here

# 5. Run the app
streamlit run research_app.py
```

## Deployment (Streamlit Community Cloud)

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Select the repo, set main file to `research_app.py`
4. In **Advanced settings → Secrets**, add:
   ```toml
   HF_TOKEN = "hf_your_token_here"
   ```
5. Deploy — auto-redeploys on every `git push`

## Project Structure

```
├── research_app.py      # Streamlit UI
├── research_agent.py    # Agent logic, MCP connections, system prompt
├── requirements.txt
├── .env.example
└── .streamlit/
    └── config.toml
```

## Data Sources

| Source | What it covers |
|---|---|
| [ClinicalTrials.gov](https://clinicaltrials.gov) | Active, recruiting, and completed trials — phase, eligibility, sponsor, status |
| [PubMed](https://pubmed.ncbi.nlm.nih.gov) | Published results, systematic reviews, meta-analyses |
