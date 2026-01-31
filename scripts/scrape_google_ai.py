#!/usr/bin/env python3
"""
CLI script to scrape Google AI Mode.

Usage:
    python scripts/scrape_google_ai.py "what is the best crm"
    python scripts/scrape_google_ai.py "best project management software" --headless
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scrapers.google_ai_scraper import GoogleAIScraper


def main():
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python scripts/scrape_google_ai.py <query> [--headless] [--screenshot]")
        print('Example: python scripts/scrape_google_ai.py "what is the best crm"')
        sys.exit(1)

    query = sys.argv[1]
    headless = "--headless" in sys.argv
    screenshot = "--screenshot" in sys.argv
    
    # Parse proxy argument
    proxy = None
    for arg in sys.argv:
        if arg.startswith("--proxy="):
            proxy = arg.split("=")[1]
            break

    # Output directory
    output_dir = Path(__file__).parent.parent / "data" / "results" / "google"

    print("=" * 60)
    print("Google AI Mode Scraper (undetected-chromedriver)")
    print("=" * 60)
    print(f"Query: {query}")
    print(f"Headless: {headless}")
    print(f"Screenshot: {screenshot}")
    print()

    # Run scraper
    with GoogleAIScraper(headless=headless, proxy=proxy) as scraper:
        result = scraper.scrape(query, take_screenshot=screenshot)

        if result.success:
            # Save result
            filepath = scraper.save_result(result, output_dir)

            print()
            print("=" * 60)
            print("RESULT SUMMARY")
            print("=" * 60)
            print(f"Query: {result.query}")
            print(f"Sources found: {result.source_count}")
            print()

            # Show first 500 chars of response
            if result.response_text:
                print("Response preview:")
                print("-" * 40)
                print(result.response_text[:500])
                if len(result.response_text) > 500:
                    print(f"... ({len(result.response_text)} total chars)")
                print()

            # Show first 5 sources
            if result.sources:
                print("Top sources:")
                print("-" * 40)
                for i, source in enumerate(result.sources[:5], 1):
                    print(f"{i}. {source['title'][:60]}")
                    print(f"   {source['url'][:70]}")
                    if source.get('publisher'):
                        print(f"   Publisher: {source['publisher']}")
                    print()

            print("=" * 60)
            print(f"SUCCESS! Full results saved to: {filepath}")
            print("=" * 60)
        else:
            print()
            print("=" * 60)
            print("SCRAPING FAILED")
            print("=" * 60)
            print(f"Error: {result.error}")
            sys.exit(1)


if __name__ == "__main__":
    main()
