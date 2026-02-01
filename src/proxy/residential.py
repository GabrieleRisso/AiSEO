"""
Bright Data Residential Proxy Client

Residential proxies provide real residential IPs that are:
- Harder to detect/block than datacenter IPs
- Available in 195+ countries
- Rotated automatically or with session persistence

Network Chain: Client → VPN (ProtonVPN) → GOST Sidecar → Bright Data Residential → Target

This gives double protection:
1. Your real IP is hidden by the VPN
2. Target sees a residential IP from Bright Data

Pricing (2025):
- Standard: $8.40/GB
- With geo-targeting: $8.40/GB

Best for:
- Sites that block datacenter IPs
- E-commerce scraping
- Social media data collection
"""

import os
import asyncio
import aiohttp
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class ResidentialConfig:
    """Configuration for residential proxy."""
    country: str = "us"
    
    # Bright Data credentials
    customer_id: Optional[str] = None
    zone: Optional[str] = None
    password: Optional[str] = None
    
    # Session settings
    session_id: Optional[str] = None  # For IP persistence
    session_duration: int = 0  # 0 = rotate each request
    
    # Geo-targeting
    city: Optional[str] = None
    state: Optional[str] = None
    
    # Performance
    timeout: int = 30
    retries: int = 3


@dataclass 
class ResidentialResponse:
    """Response from residential proxy request."""
    success: bool
    status_code: int
    content: str
    headers: Dict[str, str] = field(default_factory=dict)
    
    # Connection info
    ip_used: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    
    # Cost tracking
    data_transferred_kb: float = 0.0
    estimated_cost_usd: float = 0.0
    duration_seconds: float = 0.0
    
    # Error
    error: Optional[str] = None


class ResidentialProxyClient:
    """
    Bright Data Residential Proxy Client.
    
    Provides residential IP proxying with:
    - Country/city geo-targeting
    - Session persistence (same IP for multiple requests)
    - Automatic rotation
    - VPN chaining support
    
    Two modes of operation:
    1. Direct to Bright Data: Use proxy_url property
    2. Via VPN sidecar: Use sidecar_url property (recommended)
    
    Usage (Direct):
        client = ResidentialProxyClient(country="it")
        response = await client.fetch("https://example.com")
    
    Usage (Via VPN Sidecar):
        client = ResidentialProxyClient(country="it", use_vpn_sidecar=True)
        response = await client.fetch("https://example.com")
    """
    
    BRIGHT_DATA_HOST = "brd.superproxy.io"
    BRIGHT_DATA_PORT = 22225  # Residential port
    
    # Cost per GB (USD)
    COST_PER_GB = 8.40
    
    # Supported countries with VPN sidecars
    VPN_SIDECAR_COUNTRIES = ["fr", "de", "nl", "it", "es", "uk", "ch", "se"]
    
    def __init__(
        self,
        country: str = "us",
        customer_id: Optional[str] = None,
        zone: Optional[str] = None,
        password: Optional[str] = None,
        session_id: Optional[str] = None,
        use_vpn_sidecar: bool = True,
        timeout: int = 30,
        retries: int = 3,
    ):
        """
        Initialize Residential Proxy client.
        
        Args:
            country: Target country code (e.g., "us", "it", "de")
            customer_id: Bright Data customer ID
            zone: Residential proxy zone name
            password: Zone password
            session_id: Session ID for IP persistence (None = rotate each request)
            use_vpn_sidecar: Route through VPN sidecar (recommended for extra privacy)
            timeout: Request timeout in seconds
            retries: Number of retry attempts
        """
        self.country = country.lower()
        self.customer_id = customer_id or os.getenv("BRIGHTDATA_CUSTOMER_ID", "hl_0d78e46f")
        self.zone = zone or os.getenv("BRIGHTDATA_RESIDENTIAL_ZONE", "aiseo_1")
        self.password = password or os.getenv("BRIGHT_DATA_PASSWORD")
        self.session_id = session_id
        self.use_vpn_sidecar = use_vpn_sidecar
        self.timeout = timeout
        self.retries = retries
        
        # Validate credentials for direct mode
        if not use_vpn_sidecar and not self.password:
            raise ValueError(
                "Password required for direct Bright Data access. "
                "Set BRIGHT_DATA_PASSWORD env var or use VPN sidecar mode."
            )
    
    @property
    def proxy_url(self) -> str:
        """
        Get direct Bright Data proxy URL.
        
        Format: http://user-country-XX:password@host:port
        """
        user = f"brd-customer-{self.customer_id}-zone-{self.zone}-country-{self.country}"
        if self.session_id:
            user += f"-session-{self.session_id}"
        return f"http://{user}:{self.password}@{self.BRIGHT_DATA_HOST}:{self.BRIGHT_DATA_PORT}"
    
    @property
    def sidecar_url(self) -> str:
        """
        Get VPN sidecar proxy URL.
        
        Traffic flow: Client → VPN → Sidecar → Bright Data → Target
        
        This provides extra privacy as your real IP is hidden by VPN,
        and the target sees a Bright Data residential IP.
        """
        if self.country not in self.VPN_SIDECAR_COUNTRIES:
            logger.warning(
                f"No VPN sidecar for {self.country}, using {self.VPN_SIDECAR_COUNTRIES[0]}"
            )
            return f"http://vpn-{self.VPN_SIDECAR_COUNTRIES[0]}:8889"
        return f"http://vpn-{self.country}:8889"
    
    @property
    def effective_proxy_url(self) -> str:
        """Get the proxy URL based on configuration."""
        if self.use_vpn_sidecar:
            return self.sidecar_url
        return self.proxy_url
    
    def _estimate_cost(self, data_bytes: int) -> float:
        """Estimate cost for data transferred."""
        gb = data_bytes / (1024 * 1024 * 1024)
        return gb * self.COST_PER_GB
    
    async def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        verify_ip: bool = False,
    ) -> ResidentialResponse:
        """
        Fetch a URL through residential proxy.
        
        Args:
            url: Target URL
            method: HTTP method
            headers: Custom headers
            body: Request body
            verify_ip: Verify the proxy IP before request
        
        Returns:
            ResidentialResponse with content and metadata
        """
        start_time = time.time()
        proxy = self.effective_proxy_url
        
        logger.info(f"Residential fetch: {url} via {proxy[:50]}...")
        
        # Optionally verify IP first
        ip_info = None
        if verify_ip:
            ip_info = await self._verify_ip(proxy)
        
        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession() as session:
                    kwargs = {
                        "proxy": proxy,
                        "timeout": aiohttp.ClientTimeout(total=self.timeout),
                        "headers": headers or {},
                    }
                    
                    if method == "POST" and body:
                        kwargs["data"] = body
                    
                    async with session.request(method, url, **kwargs) as resp:
                        content = await resp.text()
                        data_size = len(content.encode('utf-8'))
                        
                        return ResidentialResponse(
                            success=resp.status == 200,
                            status_code=resp.status,
                            content=content,
                            headers=dict(resp.headers),
                            ip_used=ip_info.get("ip") if ip_info else None,
                            country=ip_info.get("country") if ip_info else self.country.upper(),
                            city=ip_info.get("city") if ip_info else None,
                            data_transferred_kb=data_size / 1024,
                            estimated_cost_usd=self._estimate_cost(data_size),
                            duration_seconds=time.time() - start_time,
                        )
                        
            except aiohttp.ClientError as e:
                logger.warning(f"Residential request failed (attempt {attempt + 1}): {e}")
                if attempt < self.retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        return ResidentialResponse(
            success=False,
            status_code=0,
            content="",
            error="Request failed after retries",
            duration_seconds=time.time() - start_time,
        )
    
    async def _verify_ip(self, proxy: str) -> dict:
        """Verify the proxy IP using ipinfo.io."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://ipinfo.io/json",
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info(f"Proxy IP: {data.get('ip')} ({data.get('country')})")
                        return data
        except Exception as e:
            logger.warning(f"IP verification failed: {e}")
        return {}
    
    async def fetch_with_session(
        self,
        urls: List[str],
        headers: Optional[Dict[str, str]] = None,
    ) -> List[ResidentialResponse]:
        """
        Fetch multiple URLs with the same IP (session persistence).
        
        Creates a unique session ID to ensure all requests use the same IP.
        
        Args:
            urls: List of URLs to fetch
            headers: Custom headers for all requests
        
        Returns:
            List of ResidentialResponse objects
        """
        import uuid
        
        # Create a session ID for IP persistence
        original_session = self.session_id
        self.session_id = str(uuid.uuid4())[:8]
        
        try:
            responses = []
            for url in urls:
                resp = await self.fetch(url, headers=headers, verify_ip=(len(responses) == 0))
                responses.append(resp)
            return responses
        finally:
            self.session_id = original_session


def get_residential_proxy_for_country(country: str, use_vpn_sidecar: bool = True) -> str:
    """
    Quick helper to get residential proxy URL for a country.
    
    Args:
        country: Country code (e.g., "it", "de", "fr")
        use_vpn_sidecar: Whether to use VPN sidecar (recommended)
    
    Returns:
        Proxy URL string
    """
    client = ResidentialProxyClient(country=country, use_vpn_sidecar=use_vpn_sidecar)
    return client.effective_proxy_url
