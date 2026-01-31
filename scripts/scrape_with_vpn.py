#!/usr/bin/env python3
"""
Wrapper script to scrape Google AI Mode routing through specific VPN containers.
Usage:
    python scripts/scrape_with_vpn.py "query" --country us
"""

import sys
import argparse
from pathlib import Path
import os

# Map country codes to proxy URLs
# These hostnames match the service names in docker-compose.yml
# In Railway, you would use the internal service domains or private networking
PROXY_MAP = {}

def main():
    parser = argparse.ArgumentParser(description="Scrape Google AI with VPN routing")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--country", "-c", help="Specific country/proxy to use (e.g., 'us', 'fr')")
    parser.add_argument("--random", action="store_true", help="Pick a random proxy from the pool")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless (default: True)")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Run with visible browser")
    parser.add_argument("--screenshot", action="store_true", help="Take screenshots")
    
    args = parser.parse_args()
    
    # Load dynamic proxy map from environment variables
    # Looks for variables starting with PROXY_
    proxy_map = PROXY_MAP.copy()
    for key, val in os.environ.items():
        if key.startswith("PROXY_"):
            code = key.replace("PROXY_", "").lower()
            proxy_map[code] = val
            
    selected_proxy = None
    country_code = "unknown"
    
    if args.random:
        import random
        if not proxy_map:
            print("Error: No proxies available in environment.")
            sys.exit(1)
        country_code, selected_proxy = random.choice(list(proxy_map.items()))
        print(f"Randomly selected proxy: {country_code.upper()}")
        
    elif args.country:
        selected_proxy = proxy_map.get(args.country.lower())
        country_code = args.country.lower()
        if not selected_proxy:
            print(f"Error: No proxy defined for country {args.country}")
            print(f"Available: {', '.join(proxy_map.keys())}")
            sys.exit(1)
    else:
        # Default to US if exists, else first available
        if "us" in proxy_map:
            selected_proxy = proxy_map["us"]
            country_code = "us"
        elif proxy_map:
            country_code, selected_proxy = list(proxy_map.items())[0]
        else:
            print("Error: No proxies configured.")
            sys.exit(1)
            
    print(f"Routing through {country_code.upper()} via {selected_proxy}")
    
    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    
    try:
        from scrapers.google_ai_scraper import GoogleAIScraper
    except ImportError:
        print("Error: Could not import GoogleAIScraper. Make sure you are running from the project root or scripts directory.")
        sys.exit(1)
    
    with GoogleAIScraper(headless=args.headless, proxy=selected_proxy) as scraper:
        result = scraper.scrape(args.query, take_screenshot=args.screenshot)
        
        output_dir = Path(__file__).parent.parent / "data" / "results" / "google"
        if result.success:
            filepath = scraper.save_result(result, output_dir)
            print(f"Success! Saved to {filepath}")
            if result.response_text:
                print("\nResponse Preview:")
                print(result.response_text[:200] + "...")
        else:
            print(f"Failed: {result.error}")
            sys.exit(1)

if __name__ == "__main__":
    main()
