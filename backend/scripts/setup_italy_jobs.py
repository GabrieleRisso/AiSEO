#!/usr/bin/env python3
"""
Setup daily scraping jobs for Italy market analysis.
Uses browser mode for higher success rate.
Author: Cyberdeck (automated via OpenClaw)
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000/api"

# Italian ecommerce queries (localized)
QUERIES_IT = [
    "Qual è la migliore piattaforma ecommerce nel 2026?",
    "Meglio Shopify o WooCommerce?",
    "Quale piattaforma ecommerce per piccole imprese?",
    "Come aprire un negozio online in Italia?",
    "Qual è il modo più economico per vendere online?",
    "Quale piattaforma ecommerce ha le migliori funzionalità SEO?",
    "Quale piattaforma usare per il dropshipping?",
    "Shopify vale il prezzo?",
    "Quali sono le alternative a WooCommerce?",
    "BigCommerce o Shopify per il mio negozio?",
    "Qual è la piattaforma più facile per aprire un negozio online?",
    "Quale piattaforma ecommerce è migliore per principianti?",
    "Come scegliere tra Wix e Shopify?",
    "Quale piattaforma usano i negozi online di successo?",
    "Squarespace è buono per vendere prodotti?",
    "Quali strumenti servono per iniziare a vendere online?",
    "Quale piattaforma ha le commissioni più basse?",
    "Migliore piattaforma ecommerce per prodotti digitali?",
    "Shopify confronto con altre piattaforme ecommerce?",
    "Cosa cercare in una piattaforma ecommerce?",
]

# English queries for international comparison
QUERIES_EN = [
    "What is the best ecommerce platform in 2026?",
    "Shopify vs WooCommerce which is better?",
    "Best ecommerce platform for small business?",
    "How to start an online store?",
    "Cheapest way to sell products online?",
]

# Browser mode config (higher success rate)
JOB_CONFIG = {
    "country": "it",
    "frequency": "daily",
    "proxy_layer": "browser",  # Full browser mode
    "num_results": 10,
    "device_type": "desktop",
    "os_type": "windows",
    "browser_type": "chrome",
    "human_behavior": True,
    "take_screenshot": True,
    "run_in_background": True,
    "antidetect_enabled": True,
    "profile": "desktop_1080p",
    "scroll_full_page": True,
}


def create_job(query: str, scraper_type: str) -> dict:
    """Create a scraping job"""
    payload = {
        **JOB_CONFIG,
        "query": query,
        "scraper_type": scraper_type,
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/jobs/scrape",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def main():
    print("🇮🇹 Setting up Italy scraping jobs...")
    print(f"   Country: Italy (it)")
    print(f"   Frequency: Daily")
    print(f"   Proxy Layer: Browser (full automation)")
    print(f"   Scrapers: google_ai + chatgpt")
    print(f"   Italian queries: {len(QUERIES_IT)}")
    print(f"   English queries: {len(QUERIES_EN)}")
    print(f"   Total jobs: {(len(QUERIES_IT) + len(QUERIES_EN)) * 2}\n")
    
    results = {"google_ai": [], "chatgpt": []}
    
    all_queries = QUERIES_IT + QUERIES_EN
    
    # Google AI jobs
    print("📊 Creating Google AI jobs...")
    for i, query in enumerate(all_queries, 1):
        lang = "IT" if query in QUERIES_IT else "EN"
        print(f"  [{i}/{len(all_queries)}] [{lang}] {query[:50]}...")
        result = create_job(query, "google_ai")
        if result:
            results["google_ai"].append(result)
            print(f"     ✅ Job ID: {result.get('job_id')}")
    
    print()
    
    # ChatGPT jobs
    print("💬 Creating ChatGPT jobs...")
    for i, query in enumerate(all_queries, 1):
        lang = "IT" if query in QUERIES_IT else "EN"
        print(f"  [{i}/{len(all_queries)}] [{lang}] {query[:50]}...")
        result = create_job(query, "chatgpt")
        if result:
            results["chatgpt"].append(result)
            print(f"     ✅ Job ID: {result.get('job_id')}")
    
    # Summary
    print("\n" + "="*60)
    print("📈 SUMMARY - Italy Market")
    print("="*60)
    print(f"Google AI: {len(results['google_ai'])} jobs created")
    print(f"ChatGPT: {len(results['chatgpt'])} jobs created")
    print(f"Total: {len(results['google_ai']) + len(results['chatgpt'])} jobs")
    
    # Save results
    output_file = f"/tmp/italy_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Saved to: {output_file}")
    
    print("\n✨ Italy jobs scheduled! Check dashboard for results.")


if __name__ == "__main__":
    main()
