"""
Configuration for Real-Time Trigger Detection System
"""
import os
from dotenv import load_dotenv

# Load environment variables from parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# =============================================================================
# API KEYS
# =============================================================================
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# Note: Twitter API removed - requires paid subscription

# =============================================================================
# RSS FEED URLS
# =============================================================================
RSS_FEEDS = {
    "pharmabiz": "http://www.pharmabiz.com/RSSFeed.aspx",
    "business_standard_pharma": "https://www.business-standard.com/rss/companies/pharma-172.rss",
    "moneycontrol_pharma": "https://www.moneycontrol.com/rss/pharma.xml",
    "economic_times_pharma": "https://economictimes.indiatimes.com/industry/healthcare/biotech/pharmaceuticals/rssfeeds/13357808.cms",
    "livemint_pharma": "https://www.livemint.com/rss/companies/pharma",
}

# =============================================================================
# TRIGGER KEYWORDS - Phrases that indicate outsourcing opportunities
# =============================================================================
TRIGGER_KEYWORDS = {
    "manufacturing_partner": [
        "seeks manufacturing partner",
        "looking for contract manufacturer",
        "manufacturing partnership",
        "CMO agreement",
        "contract manufacturing deal",
        "outsource manufacturing",
        "third party manufacturing",
    ],
    "product_approval": [
        "new product approval",
        "DCGI approval",
        "CDSCO approval",
        "drug approval",
        "product launch",
        "new drug application approved",
    ],
    "expansion": [
        "capacity expansion",
        "new product line",
        "expanding portfolio",
        "geographic expansion",
        "market expansion plans",
    ],
    "licensing": [
        "loan license agreement",
        "licensing deal",
        "in-licensing",
        "out-licensing",
        "technology transfer",
    ],
    "competitor_issues": [
        "FDA warning letter",
        "import alert",
        "recall",
        "manufacturing deficiency",
        "quality issue",
        "plant shutdown",
    ],
}

# Flattened list of all keywords for quick matching
ALL_TRIGGER_KEYWORDS = [kw for keywords in TRIGGER_KEYWORDS.values() for kw in keywords]

# =============================================================================
# REGULATORY SOURCES
# =============================================================================
REGULATORY_SOURCES = {
    "cdsco": "https://cdsco.gov.in",
    "ipindia_patents": "https://ipindia.gov.in/",
    "fda_alerts": "https://www.fda.gov/drugs/drug-safety-and-availability",
    "fda_warning_letters": "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters",
}

# =============================================================================
# TENDER SOURCES
# =============================================================================
TENDER_SOURCES = {
    "gem": "https://gem.gov.in",
    "cppp": "https://eprocure.gov.in/cppp/",
}

# =============================================================================
# FINANCIAL SOURCES
# =============================================================================
FINANCIAL_SOURCES = {
    "bse": "https://www.bseindia.com",
    "nse": "https://www.nseindia.com",
    "screener": "https://www.screener.in",
}

# =============================================================================
# JOB BOARDS
# =============================================================================
JOB_SOURCES = {
    "linkedin_pharma": "https://www.linkedin.com/jobs/search/?keywords=pharmaceutical&location=India",
    "naukri_pharma": "https://www.naukri.com/pharmaceutical-jobs",
}

# =============================================================================
# SCHEDULER SETTINGS
# =============================================================================
SCHEDULE_CONFIG = {
    "news_monitor": {
        "interval_hours": 4,
        "enabled": True,
    },
    "regulatory_monitor": {
        "interval_hours": 24,
        "enabled": True,
    },
    "tender_monitor": {
        "interval_hours": 12,
        "enabled": True,
    },
    "financial_monitor": {
        "interval_hours": 168,  # Weekly
        "enabled": True,
    },
}

# =============================================================================
# DATABASE SETTINGS
# =============================================================================
DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'triggers.db')

# =============================================================================
# OUTPUT SETTINGS
# =============================================================================
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')

# =============================================================================
# RATE LIMITING
# =============================================================================
RATE_LIMIT_DELAY = 2.0  # seconds between requests
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30  # seconds

# =============================================================================
# SENTIMENT THRESHOLDS
# =============================================================================
SENTIMENT_THRESHOLDS = {
    "positive": 0.1,
    "negative": -0.1,
}

# =============================================================================
# PHARMA COMPANIES TO TRACK (Optional - for focused monitoring)
# =============================================================================
PHARMA_COMPANIES_TO_TRACK = [
    "Sun Pharma",
    "Cipla",
    "Dr Reddy's",
    "Lupin",
    "Aurobindo Pharma",
    "Zydus Lifesciences",
    "Torrent Pharma",
    "Alkem Labs",
    "Glenmark",
    "Biocon",
    "Mankind Pharma",
    "Ipca Labs",
    "Ajanta Pharma",
    "Natco Pharma",
    "Laurus Labs",
]
