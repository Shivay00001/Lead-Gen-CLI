# AI-Powered Lead Scraping & Enrichment CLI 🚀

![Lead Gen Banner](./assets/lead_gen_banner.jpg)

**Lead Gen CLI** is a powerful, automated tool designed to streamline lead acquisition, web scraping, and data enrichment. Built for high-performance extraction and intelligent data enhancement, it converts raw URLs and unstructured web data into enriched, actionable business profiles.

Whether you're building a sales pipeline, conducting market research, or generating B2B leads, this CLI tool handles the heavy lifting of data aggregation.

## 🌟 Key Features

*   **Automated Web Scraping:** High-speed extraction of key data points from target websites.
*   **AI Data Enrichment:** Automatically enriches basic leads with deep business insights, verified emails, social profiles, and company metrics.
*   **Real-time Processing Pipeline:** Stream data efficiently through scraping and enrichment stages.
*   **CSV Import/Export:** Seamlessly load target lists (`test_leads.csv`, `real_leads.csv`) and output enriched datasets ready for CRM integration.
*   **Developer Friendly CLI:** Easy-to-use command-line interface for integrating into existing automation workflows.

## 🛠️ Getting Started

### Prerequisites
*   Python 3.8+
*   Required dependencies listed in `requirements.txt`

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Shivay00001/Lead-Gen-CLI.git
   cd Lead-Gen-CLI
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage
Run the CLI tool directly from your terminal:
```bash
export OPENAI_API_KEY="sk-..."          # required for real intent scoring
python cli.py --keywords "AI SaaS" --title "CTO" --source github --limit 10 --output leads.csv
```
Options: `--source` is `github`, `linkedin`, or `twitter`. Without `OPENAI_API_KEY`
(or with an invalid key) the intent step is skipped gracefully — leads get
`intent_score: 0` / `"LLM unavailable"` instead of fake scores, and the pipeline
still completes. A **real key is required for real intent scores**.

`OPENAI_BASE_URL` and `OPENAI_MODEL` (default `gpt-4o-mini`) can point the client at
any OpenAI-compatible endpoint.

> Note: the old g4f / Pollinations.ai fallbacks were removed (unofficial, fragile,
> and their "scores" were fabricated). Intent scoring now uses a real
> OpenAI-compatible chat-completions client.

### Honest limits
*   Fetched leads come from public OSINT (GitHub API / DuckDuckGo); enrichment emails
    are **guessed patterns** (`first.last@domain`), not verified addresses.
*   `company_size` is a random placeholder, not real data.

## 📈 Use Cases
*   **B2B Sales:** Build enriched account lists with decision-maker contact info.
*   **Marketing Agencies:** Automate lead qualification and segmentation.
*   **Recruiters:** Extract and enrich candidate profiles at scale.

---
*Developed with ❤️ to empower your sales and marketing automation.*
