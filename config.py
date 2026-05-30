"""
NDSS 2026 Paper Scraper - Configuration
"""

import os


def _load_dotenv(path: str = ".env"):
    """Minimal .env loader — no extra dependencies needed."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if key not in os.environ:
                os.environ[key] = val


_load_dotenv()

# --- DeepSeek API ---
# Set DEEPSEEK_API_KEY in your environment, or create a .env file (see .env.example)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

# --- Scraping ---
LISTING_URL = "https://www.ndss-symposium.org/ndss2026/accepted-papers/"
REQUEST_TIMEOUT = 30  # seconds
MAX_CONCURRENT = 8    # concurrent detail page fetches
RETRY_TIMES = 3
RETRY_DELAY = 2  # seconds between retries

# --- Caching ---
DATA_DIR = "data"
PAPERS_JSON = "data/papers.json"        # scraped papers cache
CLASSIFIED_JSON = "data/classified.json" # classified results cache

# --- Output ---
OUTPUT_DIR = "output"
OUTPUT_MD = "output/NDSS2026.md"

# --- Classification ---
# Batch size for DeepSeek API classification
CLASSIFY_BATCH_SIZE = 15
# Delay between batches to avoid rate limiting
BATCH_DELAY = 1.0
