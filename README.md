# Real-Time Trigger Detection System

Task 2 of the Pharma Lead Generation Platform - monitors industry signals for outsourcing opportunities.

## Quick Start

### 1. Install Dependencies

```bash
cd e:\End-To-End_PharmaLead\trigger_detection
pip install -r requirements.txt
```

### 2. Run the System

**🌐 Web Interface:**
```bash
python -m streamlit run app.py
```
Open http://localhost:8501

**💻 Command Line:**
```bash
python main.py              # Run all monitors once
python main.py --test-mode  # Quick test
python main.py --schedule   # Start automated scheduler
python main.py --stats      # View statistics
```

---

## Components

| Monitor | Sources | Frequency |
|---------|---------|-----------|
| 📰 News | RSS feeds, Google News | Every 4 hours |
| 📋 Regulatory | CDSCO, FDA alerts | Daily |
| 📑 Tender | GEM portal, CPPP | Every 12 hours |
| 📊 Financial | Stock filings, Job postings | Weekly |

---

## Trigger Keywords Detected

- Manufacturing partnerships
- Product approvals (CDSCO, FDA)
- Capacity expansions
- Licensing deals
- Competitor issues (FDA warnings)
- Job posting patterns (outsourcing signals)

---

## Output

Triggers are stored in SQLite database and can be exported as CSV. Each trigger includes:
- **Trigger Score** (1-10) - Opportunity importance
- **Sentiment Score** - Positive/negative analysis
- **Keywords** - Matched trigger phrases
- **Company Name** - Extracted if available

---

## Project Structure

```
trigger_detection/
├── main.py           # CLI entry point
├── app.py            # Streamlit dashboard
├── config/           # Configuration
├── monitors/         # 4 monitor implementations
├── analyzers/        # Sentiment, keyword, quantity
├── database/         # SQLite storage
├── scheduler/        # APScheduler jobs
└── utils/            # Helper functions
```
