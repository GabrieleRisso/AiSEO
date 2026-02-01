"""
Bright Data Web Unlocker API Client

The Web Unlocker API provides:
- Automatic proxy selection and rotation
- Built-in anti-bot bypass
- Automatic CAPTCHA solving
- Pay only for successful requests (standard domains)
- Supports raw HTML, JSON, and markdown output

Best for:
- Protected sites (Google, Amazon, LinkedIn)
- High success rate requirements
- When you want managed infrastructure

Pricing (2025):
- Standard domains: ~$3/1000 successful requests
- Premium domains: ~$10/1000 requests
"""

import os
import asyncio
import aiohttp
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Literal
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class UnlockerFormat(str, Enum):
    """Response format options."""
    RAW = "raw"           # Raw HTML response
    JSON = "json"         # Parsed JSON (if site returns JSON)
    MARKDOWN = "markdown" # Converted to markdown


@dataclass
class UnlockerRequest:
    """Request configuration for Web Unlocker API."""
    url: str
    zone: Optional[str] = None
    format: UnlockerFormat = UnlockerFormat.RAW
    country: Optional[str] = None
    
    # HTTP method and body
    method: str = "GET"
    body: Optional[str] = None
    
    # Custom headers (requires zone configuration)
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    
    # Advanced options
    js_render: bool = False  # Enable JavaScript rendering
    premium: bool = False    # Force premium handling
    
    def to_payload(self) -> dict:
        """Convert to API payload."""
        payload = {
            "url": self.url,
            "format": self.format.value,
        }
        
        if self.zone:
            payload["zone"] = self.zone
        
        if self.country:
            payload["country"] = self.country
        
        if self.method != "GET":
            payload["method"] = self.method
        
        if self.body:
            payload["body"] = self.body
        
        if self.headers:
            payload["headers"] = self.headers
        
        if self.cookies:
            payload["cookies"] = self.cookies
        
        if self.js_render:
            payload["js_render"] = True
        
        return payload


@dataclass
class UnlockerResponse:
    """Response from Web Unlocker API."""
    success: bool
    status_code: int
    content: str
    
    # Response metadata
    headers: Dict[str, str] = field(default_factory=dict)
    content_type: Optional[str] = None
    
    # Cost and performance
    duration_seconds: float = 0.0
    estimated_cost_usd: float = 0.0
    is_premium: bool = False
    
    # Error info
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    # Request info
    url: str = ""
    country_used: Optional[str] = None


class WebUnlockerClient:
    """
    Bright Data Web Unlocker API Client.
    
    Provides a simple interface for the Web Unlocker API with:
    - Automatic retry with backoff
    - Cost tracking
    - Async/await support
    
    Usage:
        client = WebUnlockerClient()
        response = await client.unlock("https://www.google.com/search?q=test")
        print(response.content)
    """
    
    API_ENDPOINT = "https://api.brightdata.com/request"
    
    # Premium domains (charged at higher rate)
    PREMIUM_DOMAINS = [
        "google.com", "google.co.uk", "google.de", "google.fr", "google.it",
        "linkedin.com", "amazon.com", "amazon.co.uk", "amazon.de",
        "instagram.com", "facebook.com", "twitter.com", "x.com",
    ]
    
    # Cost per request (USD)
    COST_STANDARD = 0.003   # $3/1000 requests
    COST_PREMIUM = 0.010    # $10/1000 requests
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        zone: Optional[str] = None,
        default_country: str = "us",
        timeout: int = 60,
        retries: int = 3,
    ):
        """
        Initialize Web Unlocker client.
        
        Args:
            api_key: Bright Data API key (or BRIGHTDATA_API_TOKEN env var)
            zone: Web Unlocker zone name (or BRIGHTDATA_UNLOCKER_ZONE env var)
            default_country: Default country for geo-targeting
            timeout: Request timeout in seconds
            retries: Number of retry attempts
        """
        self.api_key = api_key or os.getenv("BRIGHTDATA_API_TOKEN")
        self.zone = zone or os.getenv("BRIGHTDATA_UNLOCKER_ZONE", "web_unlocker1")
        self.default_country = default_country.lower()
        self.timeout = timeout
        self.retries = retries
        
        if not self.api_key:
            raise ValueError(
                "API key required. Set BRIGHTDATA_API_TOKEN env var or pass api_key parameter."
            )
    
    def _is_premium_domain(self, url: str) -> bool:
        """Check if URL is a premium domain."""
        url_lower = url.lower()
        return any(domain in url_lower for domain in self.PREMIUM_DOMAINS)
    
    def _estimate_cost(self, url: str) -> float:
        """Estimate cost for a request."""
        if self._is_premium_domain(url):
            return self.COST_PREMIUM
        return self.COST_STANDARD
    
    async def unlock(
        self,
        url: str,
        country: Optional[str] = None,
        format: UnlockerFormat = UnlockerFormat.RAW,
        method: str = "GET",
        body: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        js_render: bool = False,
    ) -> UnlockerResponse:
        """
        Unlock a URL using Web Unlocker API.
        
        Args:
            url: Target URL to unlock
            country: Country code for geo-targeting (e.g., "us", "it", "de")
            format: Response format (raw, json, markdown)
            method: HTTP method (GET, POST)
            body: Request body for POST requests
            headers: Custom headers (requires zone configuration)
            js_render: Enable JavaScript rendering
        
        Returns:
            UnlockerResponse with content and metadata
        
        Example:
            response = await client.unlock(
                "https://www.google.com/search?q=best+pasta",
                country="it",
                format=UnlockerFormat.RAW
            )
        """
        request = UnlockerRequest(
            url=url,
            zone=self.zone,
            format=format,
            country=country or self.default_country,
            method=method,
            body=body,
            headers=headers or {},
            js_render=js_render,
        )
        
        return await self._execute_request(request)
    
    async def _execute_request(self, request: UnlockerRequest) -> UnlockerResponse:
        """Execute the API request with retries."""
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession() as session:
                    response = await self._make_request(session, request)
                    response.duration_seconds = time.time() - start_time
                    return response
                    
            except aiohttp.ClientError as e:
                last_error = str(e)
                logger.warning(f"Unlocker request failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return UnlockerResponse(
            success=False,
            status_code=0,
            content="",
            error=last_error or "Request failed after retries",
            duration_seconds=time.time() - start_time,
            url=request.url,
        )
    
    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        request: UnlockerRequest
    ) -> UnlockerResponse:
        """Make a single API request."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        payload = request.to_payload()
        is_premium = self._is_premium_domain(request.url)
        
        logger.info(f"Unlocker request: {request.url} (premium={is_premium})")
        
        async with session.post(
            self.API_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as resp:
            content = await resp.text()
            
            response = UnlockerResponse(
                success=resp.status == 200,
                status_code=resp.status,
                content=content,
                headers=dict(resp.headers),
                content_type=resp.headers.get("Content-Type"),
                estimated_cost_usd=self._estimate_cost(request.url) if resp.status == 200 else 0,
                is_premium=is_premium,
                url=request.url,
                country_used=request.country,
            )
            
            if resp.status != 200:
                response.error = f"HTTP {resp.status}"
                response.error_code = str(resp.status)
                logger.error(f"Unlocker error: {resp.status} - {content[:200]}")
            
            return response
    
    async def unlock_batch(
        self,
        urls: list[str],
        country: Optional[str] = None,
        concurrency: int = 5,
    ) -> list[UnlockerResponse]:
        """
        Unlock multiple URLs concurrently.
        
        Args:
            urls: List of URLs to unlock
            country: Country code for all requests
            concurrency: Max concurrent requests
        
        Returns:
            List of UnlockerResponse objects
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def limited_unlock(url: str) -> UnlockerResponse:
            async with semaphore:
                return await self.unlock(url, country=country)
        
        tasks = [limited_unlock(url) for url in urls]
        return await asyncio.gather(*tasks)
    
    def get_cost_summary(self, responses: list[UnlockerResponse]) -> dict:
        """Get cost summary for a batch of responses."""
        total_cost = sum(r.estimated_cost_usd for r in responses)
        successful = sum(1 for r in responses if r.success)
        premium_count = sum(1 for r in responses if r.is_premium)
        
        return {
            "total_requests": len(responses),
            "successful_requests": successful,
            "failed_requests": len(responses) - successful,
            "premium_requests": premium_count,
            "standard_requests": len(responses) - premium_count,
            "total_cost_usd": round(total_cost, 4),
            "avg_cost_per_request": round(total_cost / len(responses), 4) if responses else 0,
        }


# =============================================================================
# PROXY-BASED ACCESS (Alternative to Direct API)
# =============================================================================

class WebUnlockerProxy:
    """
    Web Unlocker via HTTPS proxy interface.
    
    Alternative to Direct API - uses proxy-based routing.
    Useful for existing proxy-based workflows.
    
    Usage:
        proxy = WebUnlockerProxy()
        # Use with requests or aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy.proxy_url) as resp:
                content = await resp.text()
    """
    
    def __init__(
        self,
        customer_id: Optional[str] = None,
        zone: Optional[str] = None,
        password: Optional[str] = None,
        country: str = "us",
    ):
        self.customer_id = customer_id or os.getenv("BRIGHTDATA_CUSTOMER_ID")
        self.zone = zone or os.getenv("BRIGHTDATA_UNLOCKER_ZONE", "web_unlocker1")
        self.password = password or os.getenv("BRIGHTDATA_UNLOCKER_PASSWORD")
        self.country = country.lower()
        
        if not all([self.customer_id, self.zone, self.password]):
            raise ValueError(
                "Customer ID, zone, and password required for proxy access. "
                "Set BRIGHTDATA_CUSTOMER_ID, BRIGHTDATA_UNLOCKER_ZONE, BRIGHTDATA_UNLOCKER_PASSWORD"
            )
    
    @property
    def proxy_url(self) -> str:
        """Get proxy URL with authentication."""
        user = f"brd-customer-{self.customer_id}-zone-{self.zone}"
        if self.country:
            user += f"-country-{self.country}"
        return f"http://{user}:{self.password}@brd.superproxy.io:33335"
    
    @property
    def proxy_dict(self) -> dict:
        """Get proxy dict for requests library."""
        return {
            "http": self.proxy_url,
            "https": self.proxy_url,
        }
