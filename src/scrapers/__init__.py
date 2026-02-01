"""
AiSEO Scrapers Package

Organized by target platform:
- google/     - Google AI Mode scraper
- chatgpt/    - ChatGPT scraper
- perplexity/ - Perplexity AI scraper
- common/     - Shared utilities and Bright Data browser scraper
"""

# Common components
from .common.base import BaseScraper
from .common.brightdata_browser import BrightDataBrowserScraper

# Platform-specific scrapers
from .google.scraper import GoogleAIScraper
from .chatgpt.scraper import ChatGPTScraper
from .perplexity.scraper import PerplexityScraper

__all__ = [
    'BaseScraper',
    'BrightDataBrowserScraper',
    'GoogleAIScraper',
    'ChatGPTScraper', 
    'PerplexityScraper',
]
