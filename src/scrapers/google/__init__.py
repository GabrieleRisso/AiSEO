"""
Google AI Mode Scraper

Provides scrapers for Google AI Mode (udm=50) using:
- Selenium/undetected-chromedriver (local browser)
- Bright Data Scraping Browser (cloud browser)
"""
from .scraper import GoogleAIScraper

__all__ = ['GoogleAIScraper']
