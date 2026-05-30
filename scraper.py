"""
NDSS 2026 Paper Scraper
Scrapes paper titles, links, authors, and abstracts from the NDSS 2026 website.
"""

import json
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from tqdm import tqdm

import config


def fetch_page(url: str, timeout: int = None) -> str | None:
    """Fetch a webpage with retries. Returns HTML string or None on failure."""
    timeout = timeout or config.REQUEST_TIMEOUT
    for attempt in range(config.RETRY_TIMES):
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    )
                },
            )
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            if attempt < config.RETRY_TIMES - 1:
                time.sleep(config.RETRY_DELAY * (attempt + 1))
            else:
                print(f"  [ERROR] Failed to fetch {url}: {e}")
                return None


def parse_listing_page(html: str) -> list[dict]:
    """
    Parse the accepted-papers listing page.
    Returns a list of dicts: {pid, title, url, authors}.
    """
    soup = BeautifulSoup(html, "lxml")
    papers = []

    items = soup.find_all("div", class_="pt-cv-content-item")
    for item in items:
        # Paper title and link
        title_tag = item.find("h2", class_="pt-cv-title")
        if not title_tag:
            continue
        link_tag = title_tag.find("a")
        if not link_tag:
            continue

        title = link_tag.get_text(strip=True)
        url = link_tag.get("href", "")

        # Authors
        authors_tag = item.find("div", class_="pt-cv-ctf-display_authors")
        authors = ""
        if authors_tag:
            p = authors_tag.find("p")
            if p:
                authors = p.get_text(strip=True)

        # Post ID (data-pid)
        pid = item.get("data-pid", "")

        papers.append({
            "pid": pid,
            "title": title,
            "url": url,
            "authors": authors,
        })

    return papers


def parse_detail_page(html: str) -> str:
    """Extract abstract from a paper detail page."""
    soup = BeautifulSoup(html, "lxml")
    paper_data = soup.find("div", class_="paper-data")
    if not paper_data:
        return ""

    # Abstract is in the second <p> tag inside paper-data
    # (the first <p> is inside <strong> for authors)
    paragraphs = paper_data.find_all("p", recursive=False)
    if len(paragraphs) >= 2:
        # Skip the first <p> if it contains <strong> (authors block)
        # The abstract is usually the first non-author <p>
        for p in paragraphs:
            if p.find("strong"):
                continue
            text = p.get_text(strip=True)
            if len(text) > 50:  # likely an abstract
                return text
        # fallback: return the text of the second paragraph
        return paragraphs[-1].get_text(strip=True)

    # If structure differs, try to get all text from paper-data
    return paper_data.get_text(strip=True)


def load_cache(path: str) -> dict:
    """Load cached data from JSON file."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(path: str, data):
    """Save data to JSON cache file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def scrape_all_papers(force: bool = False) -> list[dict]:
    """
    Main scraping routine:
    1. Fetch listing page → get all paper titles/links/authors
    2. Fetch each detail page → get abstract
    3. Cache intermediate results
    Returns list of papers with abstracts populated.
    """
    # --- Step 1: Parse listing page ---
    cache = load_cache(config.PAPERS_JSON)
    if not force and cache.get("papers") and len(cache["papers"]) == 265:
        print(f"[INFO] Loaded {len(cache['papers'])} papers from cache. "
              f"Use --force to re-scrape.")
        papers = cache["papers"]
    else:
        print(f"[INFO] Fetching listing page: {config.LISTING_URL}")
        html = fetch_page(config.LISTING_URL)
        if not html:
            raise RuntimeError("Failed to fetch listing page.")

        papers = parse_listing_page(html)
        print(f"[INFO] Found {len(papers)} papers on listing page.")

        cache["papers"] = papers
        save_cache(config.PAPERS_JSON, cache)

    # --- Step 2: Fetch detail pages for abstracts ---
    papers_to_fetch = [
        p for p in papers
        if force or not p.get("abstract") or len(p.get("abstract", "")) < 50
    ]

    if not papers_to_fetch:
        print("[INFO] All abstracts already cached. Use --force to re-scrape.")
        return papers

    print(f"[INFO] Fetching abstracts for {len(papers_to_fetch)} papers "
          f"({config.MAX_CONCURRENT} concurrent)...")

    # Build a lookup for quick update
    paper_map = {p["pid"]: p for p in papers}

    def fetch_one(paper: dict) -> dict:
        """Fetch abstract for a single paper. Returns updated paper dict."""
        if paper.get("abstract") and len(paper["abstract"]) > 50 and not force:
            return paper
        html = fetch_page(paper["url"])
        if html:
            paper["abstract"] = parse_detail_page(html)
        else:
            paper["abstract"] = ""
        # Small delay between requests
        time.sleep(0.3)
        return paper

    with ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT) as executor:
        futures = {executor.submit(fetch_one, p): p["pid"] for p in papers_to_fetch}
        with tqdm(total=len(papers_to_fetch), desc="Scraping abstracts") as pbar:
            for future in as_completed(futures):
                pid = futures[future]
                try:
                    updated = future.result()
                    paper_map[pid] = updated
                except Exception as e:
                    print(f"  [ERROR] Failed for {pid}: {e}")
                pbar.update(1)
                # Save cache every 30 papers
                if pbar.n % 30 == 0:
                    cache["papers"] = list(paper_map.values())
                    save_cache(config.PAPERS_JSON, cache)

    # Final save
    cache["papers"] = list(paper_map.values())
    save_cache(config.PAPERS_JSON, cache)

    papers = cache["papers"]
    with_abstract = sum(1 for p in papers if p.get("abstract") and len(p["abstract"]) > 50)
    print(f"[INFO] Scraping complete: {with_abstract}/{len(papers)} papers have abstracts.")

    return papers


if __name__ == "__main__":
    papers = scrape_all_papers()
    print(f"\nSample paper:")
    print(json.dumps(papers[0], ensure_ascii=False, indent=2))
