#!/usr/bin/env python3
"""
NDSS 2026 Paper Scraper & Classifier
====================================
Scrapes the NDSS 2026 accepted papers list, fetches abstracts from detail pages,
classifies papers into research areas using DeepSeek API, and generates a
well-organized markdown output.

Usage:
  python main.py                    # Full pipeline (scrape + classify + output)
  python main.py --scrape-only      # Only scrape papers
  python main.py --classify-only    # Only classify (from cache)
  python main.py --force            # Force re-scrape and re-classify
  python main.py --output-only      # Only generate markdown from cache
  python main.py --test-batch N     # Test classify N papers only
"""

import argparse
import sys

import config
from scraper import scrape_all_papers, load_cache
from classifier import classify_all_papers
from output import generate_markdown


def main():
    parser = argparse.ArgumentParser(
        description="NDSS 2026 Paper Scraper & Classifier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                        # Full pipeline
  python main.py --scrape-only          # Just scrape (save to cache)
  python main.py --classify-only        # Just classify (from cached scrape)
  python main.py --force                # Re-do everything from scratch
  python main.py --test-batch 10        # Test classification on first 10 papers
        """,
    )
    parser.add_argument(
        "--scrape-only", action="store_true",
        help="Only scrape papers, skip classification and output.",
    )
    parser.add_argument(
        "--classify-only", action="store_true",
        help="Only classify papers (requires scraped cache).",
    )
    parser.add_argument(
        "--output-only", action="store_true",
        help="Only generate markdown from classified cache.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-scrape and re-classify (ignore cache).",
    )
    parser.add_argument(
        "--test-batch", type=int, metavar="N", default=0,
        help="Test classification on first N papers only (for validation).",
    )
    args = parser.parse_args()

    # Determine mode
    scrape = not (args.classify_only or args.output_only)
    classify = not (args.scrape_only or args.output_only)
    output = not (args.scrape_only or args.classify_only)

    if args.scrape_only:
        scrape, classify, output = True, False, False
    elif args.classify_only:
        scrape, classify, output = False, True, False
    elif args.output_only:
        scrape, classify, output = False, False, True

    print("=" * 60)
    print("  NDSS 2026 Paper Scraper & Classifier")
    print(f"  Mode: {'Scrape' if scrape else ''}"
          f"{' + Classify' if classify else ''}"
          f"{' + Output' if output else ''}")
    print("=" * 60)

    # --- Step 1: Scrape ---
    papers = []
    if scrape:
        print("\n[STEP 1/3] Scraping papers...")
        papers = scrape_all_papers(force=args.force)
        print(f"  Scraped {len(papers)} papers.")
    else:
        # Load from cache
        cache = load_cache(config.PAPERS_JSON)
        papers = cache.get("papers", [])
        if not papers:
            print("[ERROR] No cached papers found. Run with --scrape-only first.")
            sys.exit(1)
        print(f"\n[INFO] Loaded {len(papers)} papers from cache.")

    # --- Test batch truncation ---
    if args.test_batch and args.test_batch > 0:
        papers = papers[:args.test_batch]
        print(f"[TEST] Using only first {len(papers)} papers.")

    # --- Step 2: Classify ---
    if classify:
        print(f"\n[STEP 2/3] Classifying {len(papers)} papers...")
        papers = classify_all_papers(papers, force=args.force)

    # --- Step 3: Generate Markdown ---
    if output:
        print(f"\n[STEP 3/3] Generating markdown...")
        generate_markdown(papers, config.OUTPUT_MD)

    print("\n" + "=" * 60)
    print("  Done!")
    print(f"  Output: {config.OUTPUT_MD}")
    print("=" * 60)


if __name__ == "__main__":
    main()
