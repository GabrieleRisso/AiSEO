from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from src.lib.antidetect import AntiDetectLayer


@dataclass
class ProxyLayerConfig:
    """
    Two-layer proxy configuration for scrapers.
    
    Layer 1: VPN (Always Active)
        - All traffic routes through ProtonVPN first
        - Country-specific containers: vpn-{country}
        
    Layer 2: Enhancement Mode (Optional)
        - direct: VPN only (free)
        - residential: VPN + Bright Data residential
        - unlocker: Bright Data Web Unlocker API
        - browser: Bright Data Scraping Browser
    """
    country: str = "it"
    layer2_mode: str = "direct"  # direct, residential, unlocker, browser
    
    # Computed URLs
    vpn_proxy_url: Optional[str] = None
    residential_proxy_url: Optional[str] = None
    
    # Origin verification
    origin_ip: Optional[str] = None
    origin_city: Optional[str] = None
    origin_country: Optional[str] = None
    origin_verified: bool = False
    origin_warning: Optional[str] = None
    
    def __post_init__(self):
        cc = self.country.lower()
        self.vpn_proxy_url = f"http://vpn-{cc}:8888"
        self.residential_proxy_url = f"http://vpn-{cc}:8889"
    
    @property
    def active_proxy(self) -> Optional[str]:
        """Get the active proxy URL based on layer2 mode."""
        if self.layer2_mode == "residential":
            return self.residential_proxy_url
        elif self.layer2_mode in ("direct", "unlocker", "browser"):
            return self.vpn_proxy_url
        return self.vpn_proxy_url
    
    def to_dict(self) -> dict:
        return {
            "country": self.country,
            "layer2_mode": self.layer2_mode,
            "vpn_proxy_url": self.vpn_proxy_url,
            "residential_proxy_url": self.residential_proxy_url,
            "active_proxy": self.active_proxy,
            "origin": {
                "ip": self.origin_ip,
                "city": self.origin_city,
                "country": self.origin_country,
                "verified": self.origin_verified,
                "warning": self.origin_warning,
            },
        }


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    
    Supports two-layer proxy configuration:
    - Layer 1: VPN (always active via vpn-{country} containers)
    - Layer 2: Enhancement mode (direct, residential, unlocker, browser)
    """
    
    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[str] = None,
        antidetect: Optional['AntiDetectLayer'] = None,
        proxy_config: Optional[ProxyLayerConfig] = None,
    ):
        self.headless = headless
        self.antidetect = antidetect
        
        # Use proxy_config if provided, otherwise build from proxy string
        if proxy_config:
            self.proxy_config = proxy_config
            self.proxy = proxy_config.active_proxy
        else:
            self.proxy = proxy
            # Infer country from proxy URL if possible
            if proxy and "vpn-" in proxy:
                # Extract country from vpn-{country}:port
                import re
                match = re.search(r'vpn-([a-z]{2})', proxy)
                country = match.group(1) if match else "it"
                layer2 = "residential" if ":8889" in proxy else "direct"
                self.proxy_config = ProxyLayerConfig(country=country, layer2_mode=layer2)
            else:
                self.proxy_config = ProxyLayerConfig()

    @abstractmethod
    async def scrape(self, query: str, take_screenshot: bool = False) -> Dict[str, Any]:
        """
        Execute the scrape.
        Must return a dictionary with:
        - status: str
        - data: list
        - response_text: str
        - html_content: str (optional)
        - error: str (optional)
        - metadata: dict
        - proxy_info: dict (layer config and origin verification)
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
