import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import json
import os

from brightdata import BrightDataClient
from .base import BaseScraper

class BrightDataScraper(BaseScraper):
    """
    Scraper using Bright Data SDK for high-reliability scraping.
    Focuses on SERP API (Google) primarily.
    """
    
    def __init__(self, headless: bool = True, proxy: str = None, antidetect = None):
        super().__init__(headless, proxy, antidetect)
        # We will initialize client in scrape() method
        self.client = None

    async def scrape(self, query: str, take_screenshot: bool = False) -> Dict[str, Any]:
        """
        Execute scrape using Bright Data SDK.
        Supports Google Search via SDK.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        token = os.environ.get("BRIGHTDATA_API_TOKEN")
        if not token:
             return {
                "status": "failed",
                "data": [],
                "response_text": "",
                "error": "BRIGHTDATA_API_TOKEN not found in environment",
                "metadata": {"source": "brightdata_sdk"}
            }

        try:
            # Map country code to full name for SDK 'location' parameter
            # Defaults to United States if unknown
            country_map = {
                "us": "United States",
                "uk": "United Kingdom",
                "gb": "United Kingdom",
                "fr": "France",
                "de": "Germany",
                "it": "Italy",
                "es": "Spain",
                "nl": "Netherlands",
                "ch": "Switzerland",
                "se": "Sweden",
                "ca": "Canada",
                "au": "Australia"
            }
            
            # Determine location from antidetect config or default
            target_country_code = "us"
            if self.antidetect and self.antidetect.config.target_country:
                target_country_code = self.antidetect.config.target_country.lower()
            
            location = country_map.get(target_country_code, "United States")
            print(f"BrightData SDK: Searching Google for '{query}' in '{location}'")

            # Initialize client and execute search
            async with BrightDataClient(token=token) as client:
                results = await client.search.google(
                    query=query,
                    location=location,
                    num_results=10
                )
            
            data = []
            response_text_parts = []
            
            # Process results
            # SDK returns a Result object with .data list
            # Each item typically has title, link, description, etc.
            
            if results.success:
                print(f"BrightData SDK: Success! Cost: ${getattr(results, 'cost', 0)}")
                
                # Extract organic results
                for item in results.data:
                    # SDK result format varies, need to handle organic results
                    # Typically list of dicts
                    title = item.get("title")
                    link = item.get("link")
                    snippet = item.get("description") or item.get("snippet")
                    
                    if title and link:
                        data.append({
                            "title": title,
                            "url": link,
                            "description": snippet,
                            "publisher": "", # Could parse domain
                            "date": item.get("date")
                        })
                        
                        # Build a pseudo-response text from snippets for AI processing
                        response_text_parts.append(f"## {title}\n{snippet}\n")

                response_text = "\n".join(response_text_parts)
                
                return {
                    "status": "success",
                    "data": data,
                    "response_text": response_text,
                    "html_content": "", # API might not return full HTML by default in this mode
                    "metadata": {
                        "source": "brightdata_sdk",
                        "cost": getattr(results, "cost", 0),
                        "time_ms": getattr(results, "time_ms", 0),
                        "timestamp": timestamp,
                        "proxy_used": "brightdata_api" 
                    }
                }
            else:
                return {
                    "status": "failed",
                    "data": [],
                    "response_text": "",
                    "error": getattr(results, "error", "Unknown SDK error"),
                    "metadata": {
                        "source": "brightdata_sdk",
                        "timestamp": timestamp
                    }
                }

        except Exception as e:
            print(f"BrightData SDK Error: {e}")
            return {
                "status": "failed",
                "data": [],
                "response_text": "",
                "error": str(e),
                "metadata": {
                    "source": "brightdata_sdk",
                    "timestamp": timestamp
                }
            }
