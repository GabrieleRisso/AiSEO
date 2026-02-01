#!/usr/bin/env python3
"""
Setup daily recurring scraping jobs for UK market analysis.
Creates jobs for both google_ai and chatgpt scrapers using the least expensive config (direct VPN).
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000/api"

# All ecommerce platform queries
QUERIES = [
    "What is the best ecommerce platform in 2026?",
    "Which is better, Shopify or WooCommerce?",
    "What ecommerce platform should I use for a small business?",
    "How do I start an online store?",
    "What's the cheapest way to sell products online?",
    "Which ecommerce platform has the best SEO features?",
    "What platform should I use for dropshipping?",
    "Is Shopify worth the price?",
    "What are the best alternatives to WooCommerce?",
    "Should I use BigCommerce or Shopify for my store?",
    "What's the easiest platform to set up an online shop?",
    "Which ecommerce platform is best for beginners?",
    "How do I choose between Wix and Shopify?",
    "What platform do most successful online stores use?",
    "Is Squarespace good for selling products?",
    "What ecommerce tools do I need to start selling online?",
    "Which platform has the lowest transaction fees?",
    "What's the best ecommerce platform for digital products?",
    "How does Shopify compare to other ecommerce platforms?",
    "What should I look for in an ecommerce platform?",
]

# Least expensive config: direct VPN (free)
JOB_CONFIG = {
    "country": "uk",
    "frequency": "daily",  # Run every day
    "proxy_layer": "direct",  # Cheapest: VPN only (free)
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
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"     Response: {e.response.text}")
            except:
                pass
        return None

def main():
    print("🚀 Setting up daily UK scraping jobs...")
    print(f"   Country: UK")
    print(f"   Frequency: Daily")
    print(f"   Proxy Layer: Direct (VPN only - cheapest)")
    print(f"   Scrapers: google_ai + chatgpt")
    print(f"   Total queries: {len(QUERIES)}")
    print(f"   Total jobs to create: {len(QUERIES) * 2}\n")
    
    results = {
        "google_ai": {"success": 0, "failed": 0, "jobs": []},
        "chatgpt": {"success": 0, "failed": 0, "jobs": []}
    }
    
    # Create jobs for Google AI
    print("📊 Creating Google AI jobs...")
    for i, query in enumerate(QUERIES, 1):
        print(f"  [{i}/{len(QUERIES)}] {query[:60]}...")
        result = create_job(query, "google_ai")
        if result:
            results["google_ai"]["success"] += 1
            results["google_ai"]["jobs"].append({
                "query": query,
                "job_id": result.get("job_id"),
                "status": result.get("status"),
                "next_run_at": result.get("next_run_at")
            })
            print(f"     ✅ Job ID: {result.get('job_id')}, Status: {result.get('status')}")
        else:
            results["google_ai"]["failed"] += 1
    
    print()
    
    # Create jobs for ChatGPT
    print("💬 Creating ChatGPT jobs...")
    for i, query in enumerate(QUERIES, 1):
        print(f"  [{i}/{len(QUERIES)}] {query[:60]}...")
        result = create_job(query, "chatgpt")
        if result:
            results["chatgpt"]["success"] += 1
            results["chatgpt"]["jobs"].append({
                "query": query,
                "job_id": result.get("job_id"),
                "status": result.get("status"),
                "next_run_at": result.get("next_run_at")
            })
            print(f"     ✅ Job ID: {result.get('job_id')}, Status: {result.get('status')}")
        else:
            results["chatgpt"]["failed"] += 1
    
    # Summary
    print("\n" + "="*70)
    print("📈 SUMMARY")
    print("="*70)
    print(f"Google AI Jobs:")
    print(f"  ✅ Success: {results['google_ai']['success']}")
    print(f"  ❌ Failed: {results['google_ai']['failed']}")
    print(f"\nChatGPT Jobs:")
    print(f"  ✅ Success: {results['chatgpt']['success']}")
    print(f"  ❌ Failed: {results['chatgpt']['failed']}")
    print(f"\nTotal Jobs Created: {results['google_ai']['success'] + results['chatgpt']['success']}")
    print(f"Total Jobs Failed: {results['google_ai']['failed'] + results['chatgpt']['failed']}")
    
    # Save results to file
    output_file = f"/tmp/uk_daily_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Results saved to: {output_file}")
    
    print("\n✨ Daily jobs are now scheduled!")
    print("   Jobs will run automatically every day and populate the database.")
    print("   Check the dashboard or API to monitor job status.")

if __name__ == "__main__":
    main()
