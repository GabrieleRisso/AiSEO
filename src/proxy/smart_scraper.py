"""
Smart Scraper - Unified Scraping with VPN-First Routing

All requests flow through:
1. Layer 1 (VPN): ProtonVPN container for the selected country
2. Layer 2 (Enhancement): Optional mode based on target site

Layer 2 Modes:
- direct: VPN only (cheapest)
- residential: VPN + Bright Data residential IPs
- unlocker: Bright Data Web Unlocker API
- browser: Bright Data Scraping Browser

The scraper automatically:
1. Routes through the correct country VPN
2. Selects appropriate Layer 2 based on URL
3. Verifies origin IP is correct
4. Falls back on failure (if enabled)
"""

import os
import asyncio
import aiohttp
import time
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path
import logging

from .layers import (
    Layer2Mode,
    LAYER2_INFO,
    SUPPORTED_COUNTRIES,
    get_layer2_for_url,
    get_proxy_config,
    ProxyConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    """Unified scrape result."""
    success: bool
    content: str
    url: str
    
    # Layer info
    country: str = ""
    layer2_mode: str = ""
    
    # Origin verification
    origin_ip: Optional[str] = None
    origin_city: Optional[str] = None
    origin_country: Optional[str] = None
    origin_verified: bool = False
    origin_warning: Optional[str] = None
    
    # Performance
    status_code: int = 0
    duration_seconds: float = 0.0
    data_kb: float = 0.0
    estimated_cost_usd: float = 0.0
    
    # Error handling
    error: Optional[str] = None
    fallback_used: bool = False
    attempts: int = 1


class SmartScraper:
    """
    Smart scraper with VPN-first routing.
    
    Usage:
        scraper = SmartScraper(country="it")
        
        # Auto-select Layer 2
        result = await scraper.scrape("https://google.com/search?q=test")
        
        # Force specific Layer 2 mode
        result = await scraper.scrape(
            "https://example.com",
            layer2="residential"
        )
    """
    
    # Fallback order (cheapest to most expensive)
    FALLBACK_ORDER = [
        Layer2Mode.DIRECT,
        Layer2Mode.RESIDENTIAL,
        Layer2Mode.UNLOCKER,
        Layer2Mode.BROWSER,
    ]
    
    # Known Zurich IPs (ProtonVPN HQ - should NOT be originating calls)
    ZURICH_INDICATORS = ["zurich", "zürich", "zuerich", "8.8"]
    
    def __init__(
        self,
        country: str = "it",
        enable_fallback: bool = True,
        verify_origin: bool = True,
        timeout: int = 60,
    ):
        """
        Initialize Smart Scraper.
        
        Args:
            country: Target country code (must be in SUPPORTED_COUNTRIES)
            enable_fallback: Enable fallback to more expensive layers on failure
            verify_origin: Verify origin IP before scraping
            timeout: Request timeout in seconds
        """
        self.country = country.lower()
        self.enable_fallback = enable_fallback
        self.verify_origin = verify_origin
        self.timeout = timeout
        
        if self.country not in SUPPORTED_COUNTRIES:
            logger.warning(f"Country {self.country} not supported, defaulting to 'it'")
            self.country = "it"
        
        self._config = get_proxy_config(self.country)
    
    async def verify_vpn_origin(self) -> dict:
        """
        Verify the VPN is routing traffic correctly.
        
        Returns origin info and warnings if routing seems incorrect.
        """
        proxy_url = self._config.vpn_proxy_url
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://ipinfo.io/json",
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        ip = data.get("ip", "unknown")
                        city = data.get("city", "unknown").lower()
                        country = data.get("country", "unknown")
                        region = data.get("region", "")
                        org = data.get("org", "")
                        
                        # Check for Zurich origin (ProtonVPN HQ - incorrect routing)
                        warning = None
                        is_zurich = any(z in city for z in self.ZURICH_INDICATORS)
                        
                        if is_zurich and self.country != "ch":
                            warning = (
                                f"⚠️ Origin appears to be Zurich (ProtonVPN HQ) but target country is {self.country.upper()}. "
                                f"VPN may not be routing correctly. Check PROTONVPN_KEY_{self.country.upper()} in .env"
                            )
                            logger.warning(warning)
                        
                        # Check country mismatch
                        expected_country = self.country.upper()
                        if expected_country == "UK":
                            expected_country = "GB"
                        
                        if country.upper() != expected_country and not warning:
                            warning = (
                                f"⚠️ Origin country is {country} but expected {expected_country}. "
                                f"VPN key may be incorrect for this country."
                            )
                            logger.warning(warning)
                        
                        return {
                            "ip": ip,
                            "city": data.get("city"),
                            "region": region,
                            "country": country,
                            "org": org,
                            "verified": warning is None,
                            "warning": warning,
                        }
                        
        except Exception as e:
            logger.error(f"Origin verification failed: {e}")
            return {
                "ip": "unknown",
                "verified": False,
                "warning": f"Failed to verify origin: {e}",
                "error": str(e),
            }
        
        return {"ip": "unknown", "verified": False}
    
    async def scrape(
        self,
        url: str,
        layer2: Optional[str] = None,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
    ) -> ScrapeResult:
        """
        Scrape a URL with automatic layer selection.
        
        Args:
            url: Target URL
            layer2: Force specific Layer 2 mode ("direct", "residential", "unlocker", "browser")
                    or None for auto-selection
            method: HTTP method
            headers: Custom headers
            body: Request body
        
        Returns:
            ScrapeResult with content and metadata
        """
        start_time = time.time()
        
        # Verify origin first
        origin_info = {}
        if self.verify_origin:
            origin_info = await self.verify_vpn_origin()
            if origin_info.get("warning"):
                logger.warning(f"[Layer 1] {origin_info['warning']}")
        
        # Determine Layer 2 mode
        if layer2:
            try:
                layer2_mode = Layer2Mode(layer2)
            except ValueError:
                logger.warning(f"Invalid layer2 mode '{layer2}', auto-selecting")
                layer2_mode = get_layer2_for_url(url)
        else:
            layer2_mode = get_layer2_for_url(url)
        
        logger.info(f"[Scrape] URL: {url}")
        logger.info(f"[Layer 1] VPN: {self.country.upper()} via {self._config.vpn_proxy_url}")
        logger.info(f"[Layer 2] Mode: {layer2_mode.value} ({LAYER2_INFO[layer2_mode]['name']})")
        
        # Build fallback chain
        if self.enable_fallback:
            modes_to_try = self._get_fallback_chain(layer2_mode)
        else:
            modes_to_try = [layer2_mode]
        
        last_error = None
        attempts = 0
        
        for mode in modes_to_try:
            attempts += 1
            try:
                result = await self._scrape_with_mode(url, mode, method, headers, body)
                
                if result.success:
                    result.origin_ip = origin_info.get("ip")
                    result.origin_city = origin_info.get("city")
                    result.origin_country = origin_info.get("country")
                    result.origin_verified = origin_info.get("verified", False)
                    result.origin_warning = origin_info.get("warning")
                    result.duration_seconds = time.time() - start_time
                    result.attempts = attempts
                    result.fallback_used = (mode != layer2_mode)
                    return result
                else:
                    last_error = result.error
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Layer 2 mode {mode.value} failed: {e}")
        
        # All modes failed
        return ScrapeResult(
            success=False,
            content="",
            url=url,
            country=self.country,
            layer2_mode=modes_to_try[-1].value if modes_to_try else "unknown",
            origin_ip=origin_info.get("ip"),
            origin_city=origin_info.get("city"),
            origin_country=origin_info.get("country"),
            origin_verified=origin_info.get("verified", False),
            origin_warning=origin_info.get("warning"),
            error=last_error or "All modes failed",
            duration_seconds=time.time() - start_time,
            attempts=attempts,
        )
    
    def _get_fallback_chain(self, start_mode: Layer2Mode) -> List[Layer2Mode]:
        """Get fallback chain starting from a specific mode."""
        try:
            start_idx = self.FALLBACK_ORDER.index(start_mode)
        except ValueError:
            start_idx = 0
        
        return self.FALLBACK_ORDER[start_idx:]
    
    async def _scrape_with_mode(
        self,
        url: str,
        mode: Layer2Mode,
        method: str,
        headers: Optional[Dict[str, str]],
        body: Optional[str],
    ) -> ScrapeResult:
        """Execute scrape with specific Layer 2 mode."""
        
        if mode == Layer2Mode.DIRECT:
            return await self._scrape_direct(url, method, headers, body)
        elif mode == Layer2Mode.RESIDENTIAL:
            return await self._scrape_residential(url, method, headers, body)
        elif mode == Layer2Mode.UNLOCKER:
            return await self._scrape_unlocker(url, method, headers, body)
        elif mode == Layer2Mode.BROWSER:
            return await self._scrape_browser(url)
        else:
            raise ValueError(f"Unknown mode: {mode}")
    
    async def _scrape_direct(
        self,
        url: str,
        method: str,
        headers: Optional[Dict[str, str]],
        body: Optional[str],
    ) -> ScrapeResult:
        """Scrape using VPN direct (Layer 1 only)."""
        proxy_url = self._config.vpn_proxy_url
        
        try:
            async with aiohttp.ClientSession() as session:
                kwargs = {
                    "proxy": proxy_url,
                    "timeout": aiohttp.ClientTimeout(total=self.timeout),
                    "headers": headers or {},
                }
                if method == "POST" and body:
                    kwargs["data"] = body
                
                async with session.request(method, url, **kwargs) as resp:
                    content = await resp.text()
                    data_kb = len(content.encode('utf-8')) / 1024
                    
                    return ScrapeResult(
                        success=resp.status == 200,
                        content=content,
                        url=url,
                        country=self.country,
                        layer2_mode=Layer2Mode.DIRECT.value,
                        status_code=resp.status,
                        data_kb=data_kb,
                        estimated_cost_usd=0.0,
                        error=None if resp.status == 200 else f"HTTP {resp.status}",
                    )
                    
        except Exception as e:
            return ScrapeResult(
                success=False,
                content="",
                url=url,
                country=self.country,
                layer2_mode=Layer2Mode.DIRECT.value,
                error=str(e),
            )
    
    async def _scrape_residential(
        self,
        url: str,
        method: str,
        headers: Optional[Dict[str, str]],
        body: Optional[str],
    ) -> ScrapeResult:
        """Scrape using VPN + Residential proxy."""
        proxy_url = self._config.residential_proxy_url
        
        try:
            async with aiohttp.ClientSession() as session:
                kwargs = {
                    "proxy": proxy_url,
                    "timeout": aiohttp.ClientTimeout(total=self.timeout),
                    "headers": headers or {},
                }
                if method == "POST" and body:
                    kwargs["data"] = body
                
                async with session.request(method, url, **kwargs) as resp:
                    content = await resp.text()
                    data_kb = len(content.encode('utf-8')) / 1024
                    cost = (data_kb / 1024 / 1024) * 8.40  # $8.40/GB
                    
                    return ScrapeResult(
                        success=resp.status == 200,
                        content=content,
                        url=url,
                        country=self.country,
                        layer2_mode=Layer2Mode.RESIDENTIAL.value,
                        status_code=resp.status,
                        data_kb=data_kb,
                        estimated_cost_usd=cost,
                        error=None if resp.status == 200 else f"HTTP {resp.status}",
                    )
                    
        except Exception as e:
            return ScrapeResult(
                success=False,
                content="",
                url=url,
                country=self.country,
                layer2_mode=Layer2Mode.RESIDENTIAL.value,
                error=str(e),
            )
    
    async def _scrape_unlocker(
        self,
        url: str,
        method: str,
        headers: Optional[Dict[str, str]],
        body: Optional[str],
    ) -> ScrapeResult:
        """Scrape using Web Unlocker API."""
        try:
            from .unlocker import WebUnlockerClient
            
            client = WebUnlockerClient(default_country=self.country)
            response = await client.unlock(
                url=url,
                country=self.country,
                method=method,
                body=body,
                headers=headers,
            )
            
            return ScrapeResult(
                success=response.success,
                content=response.content,
                url=url,
                country=self.country,
                layer2_mode=Layer2Mode.UNLOCKER.value,
                status_code=response.status_code,
                data_kb=len(response.content.encode('utf-8')) / 1024 if response.content else 0,
                estimated_cost_usd=response.estimated_cost_usd,
                error=response.error,
            )
            
        except ImportError:
            return ScrapeResult(
                success=False, content="", url=url,
                country=self.country, layer2_mode=Layer2Mode.UNLOCKER.value,
                error="Web Unlocker module not available",
            )
        except Exception as e:
            return ScrapeResult(
                success=False, content="", url=url,
                country=self.country, layer2_mode=Layer2Mode.UNLOCKER.value,
                error=str(e),
            )
    
    async def _scrape_browser(self, url: str) -> ScrapeResult:
        """Scrape using Scraping Browser."""
        try:
            from .browser import ScrapingBrowserClient
            
            async with ScrapingBrowserClient(country=self.country) as browser:
                response = await browser.navigate(url)
                
                return ScrapeResult(
                    success=response.success,
                    content=response.content,
                    url=url,
                    country=self.country,
                    layer2_mode=Layer2Mode.BROWSER.value,
                    data_kb=response.data_transferred_kb,
                    estimated_cost_usd=response.estimated_cost_usd,
                    error=response.error,
                )
                
        except ImportError:
            return ScrapeResult(
                success=False, content="", url=url,
                country=self.country, layer2_mode=Layer2Mode.BROWSER.value,
                error="Scraping Browser (Playwright) not available",
            )
        except Exception as e:
            return ScrapeResult(
                success=False, content="", url=url,
                country=self.country, layer2_mode=Layer2Mode.BROWSER.value,
                error=str(e),
            )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def smart_scrape(
    url: str,
    country: str = "it",
    layer2: Optional[str] = None,
) -> ScrapeResult:
    """
    Quick scrape with smart layer selection.
    
    Args:
        url: Target URL
        country: Target country
        layer2: Force layer 2 mode or None for auto
    
    Returns:
        ScrapeResult
    """
    scraper = SmartScraper(country=country)
    return await scraper.scrape(url, layer2=layer2)


def get_supported_calls() -> List[dict]:
    """
    Get list of all supported API calls with examples.
    
    Returns list suitable for documentation/frontend.
    """
    return [
        {
            "endpoint": "/smart-scrape",
            "method": "POST",
            "description": "Smart scrape with auto layer selection",
            "params": {
                "url": "Target URL (required)",
                "country": "Country code: fr, de, nl, it, es, uk, ch, se (default: it)",
                "layer2": "Layer 2 mode: direct, residential, unlocker, browser (auto if not set)",
            },
            "example": {
                "url": "https://google.com/search?q=best+pasta",
                "country": "it",
                "layer2": "unlocker"
            },
        },
        {
            "endpoint": "/unlock",
            "method": "POST", 
            "description": "Direct Web Unlocker API call",
            "params": {
                "url": "Target URL (required)",
                "country": "Country code (default: us)",
                "format": "Response format: raw, json, markdown (default: raw)",
            },
            "example": {
                "url": "https://www.amazon.com/dp/B08N5WRWNW",
                "country": "us"
            },
        },
        {
            "endpoint": "/scrape",
            "method": "POST",
            "description": "Legacy scrape endpoint with full options",
            "params": {
                "query": "Search query (required)",
                "country": "Country code",
                "scraper_type": "google_ai, perplexity, chatgpt",
                "proxy_layer": "auto, vpn_direct, residential, web_unlocker, scraping_browser",
            },
        },
    ]


def get_source_checklist() -> Dict[str, dict]:
    """
    Get checklist of supported modes for each source type.
    
    Returns dict mapping source_type to supported modes and status.
    """
    return {
        "google_ai": {
            "name": "Google AI Overview",
            "direct": {"supported": False, "reason": "Blocked by CAPTCHA"},
            "residential": {"supported": False, "reason": "Still blocked"},
            "unlocker": {"supported": True, "recommended": True, "cost": "~$10/1000 req"},
            "browser": {"supported": True, "recommended": False, "cost": "~$0.03/req"},
            "notes": "Google requires CAPTCHA bypass - use unlocker or browser",
        },
        "perplexity": {
            "name": "Perplexity AI",
            "direct": {"supported": False, "reason": "JS-heavy, requires browser"},
            "residential": {"supported": False, "reason": "JS-heavy, requires browser"},
            "unlocker": {"supported": False, "reason": "JS-heavy, requires browser"},
            "browser": {"supported": True, "recommended": True, "cost": "~$0.03/req"},
            "notes": "Perplexity requires full browser automation",
        },
        "chatgpt": {
            "name": "ChatGPT",
            "direct": {"supported": False, "reason": "JS-heavy, requires browser"},
            "residential": {"supported": False, "reason": "JS-heavy, requires browser"},
            "unlocker": {"supported": False, "reason": "JS-heavy, requires browser"},
            "browser": {"supported": True, "recommended": True, "cost": "~$0.03/req"},
            "notes": "ChatGPT requires full browser automation",
        },
        "bing": {
            "name": "Bing Search",
            "direct": {"supported": True, "recommended": True, "cost": "Free"},
            "residential": {"supported": True, "recommended": False, "cost": "~$8.40/GB"},
            "unlocker": {"supported": True, "recommended": False, "cost": "~$3/1000 req"},
            "browser": {"supported": True, "recommended": False, "cost": "~$0.03/req"},
            "notes": "Bing works with VPN direct in most cases",
        },
        "generic": {
            "name": "Generic Websites",
            "direct": {"supported": True, "recommended": True, "cost": "Free"},
            "residential": {"supported": True, "recommended": False, "cost": "~$8.40/GB"},
            "unlocker": {"supported": True, "recommended": False, "cost": "~$3/1000 req"},
            "browser": {"supported": True, "recommended": False, "cost": "~$0.03/req"},
            "notes": "Most sites work with VPN direct",
        },
    }
