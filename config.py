"""
NDSS 2026 Paper Scraper - Configuration
"""

# --- DeepSeek API ---
DEEPSEEK_API_KEY = "sk-ffc3619d69c145b7ae89d2630f072dd4"
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
