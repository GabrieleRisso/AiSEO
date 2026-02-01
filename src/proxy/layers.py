"""
Proxy Layer Configuration - Simplified Two-Layer System

Layer 1: VPN (Always Active)
    - All traffic routes through ProtonVPN first
    - Country-specific VPN containers (vpn-fr, vpn-de, etc.)
    - Provides base IP anonymization

Layer 2: VPN --> {direct, residential, unlocker, browser} Mode 
    - Applied on top of VPN for additional protection
    - Modes: direct, residential, unlocker, browser
"""

import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class Layer2Mode(str, Enum):
    """Layer 2 enhancement modes (applied on top of VPN)."""
    
    # Direct through VPN only - no additional layer
    DIRECT = "direct"
    
    # Residential IPs via Bright Data (VPN -> Bright Data Residential)
    RESIDENTIAL = "residential"
    
    # Web Unlocker API (managed unlocking with CAPTCHA solving)
    UNLOCKER = "unlocker"
    
    # Scraping Browser (full browser automation)
    BROWSER = "browser"


# Human-readable names and descriptions
LAYER2_INFO = {
    Layer2Mode.DIRECT: {
        "name": "VPN Only",
        "short": "direct",
        "description": "Traffic goes through VPN datacenter IP only",
        "cost": "Free (VPN subscription)",
        "cost_per_request": 0.0,
        "best_for": ["Simple sites", "High volume", "Non-protected content"],
        "success_rate": 0.70,
    },
    Layer2Mode.RESIDENTIAL: {
        "name": "Residential IP",
        "short": "residential", 
        "description": "VPN + Bright Data residential IP (looks like home user)",
        "cost": "~$8.40/GB",
        "cost_per_gb": 8.40,
        "best_for": ["Sites blocking datacenter IPs", "E-commerce", "Social media"],
        "success_rate": 0.85,
    },
    Layer2Mode.UNLOCKER: {
        "name": "Web Unlocker",
        "short": "unlocker",
        "description": "Bright Data managed unlocking with auto CAPTCHA solving",
        "cost": "~$3-10 per 1000 requests",
        "cost_per_1000_requests": {"standard": 3.0, "premium": 10.0},
        "best_for": ["Google", "Amazon", "LinkedIn", "Protected sites"],
        "success_rate": 0.95,
    },
    Layer2Mode.BROWSER: {
        "name": "Cloud Browser",
        "short": "browser",
        "description": "Full browser automation with fingerprint management",
        "cost": "~$0.01-0.03/request",
        "cost_per_request": 0.015,
        "best_for": ["JavaScript-heavy sites", "ChatGPT", "Complex automation"],
        "success_rate": 0.98,
    },
}


# =============================================================================
# SUPPORTED COUNTRIES
# =============================================================================

SUPPORTED_COUNTRIES = {
    "fr": {"name": "France", "flag": "🇫🇷", "vpn_port": 8001, "residential_port": 8101},
    "de": {"name": "Germany", "flag": "🇩🇪", "vpn_port": 8002, "residential_port": 8102},
    "nl": {"name": "Netherlands", "flag": "🇳🇱", "vpn_port": 8003, "residential_port": 8103},
    "it": {"name": "Italy", "flag": "🇮🇹", "vpn_port": 8004, "residential_port": 8104},
    "es": {"name": "Spain", "flag": "🇪🇸", "vpn_port": 8005, "residential_port": 8105},
    "uk": {"name": "United Kingdom", "flag": "🇬🇧", "vpn_port": 8006, "residential_port": 8106},
    "ch": {"name": "Switzerland", "flag": "🇨🇭", "vpn_port": 8007, "residential_port": 8107},
    "se": {"name": "Sweden", "flag": "🇸🇪", "vpn_port": 8008, "residential_port": 8108},
}

# =============================================================================
# SITE CLASSIFICATION - Auto-select Layer 2 mode
# =============================================================================

# Sites requiring Web Unlocker or Browser (protected)
PROTECTED_SITES = {
    "google.com": Layer2Mode.UNLOCKER,
    "google.co.uk": Layer2Mode.UNLOCKER,
    "google.de": Layer2Mode.UNLOCKER,
    "google.fr": Layer2Mode.UNLOCKER,
    "google.it": Layer2Mode.UNLOCKER,
    "google.es": Layer2Mode.UNLOCKER,
    "linkedin.com": Layer2Mode.UNLOCKER,
    "amazon.com": Layer2Mode.UNLOCKER,
    "amazon.co.uk": Layer2Mode.UNLOCKER,
    "amazon.de": Layer2Mode.UNLOCKER,
}

# Sites requiring browser automation (JS-heavy)
BROWSER_REQUIRED_SITES = [
    "chatgpt.com",
    "chat.openai.com",
    "perplexity.ai",
    "claude.ai",
    "bard.google.com",
]

# Sites requiring residential IPs
RESIDENTIAL_SITES = [
    "yelp.com",
    "tripadvisor.com",
    "glassdoor.com",
    "indeed.com",
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
]

# Sites that work with VPN direct
DIRECT_SITES = [
    "wikipedia.org",
    "github.com",
    "stackoverflow.com",
    "reddit.com",
    "news.ycombinator.com",
    "medium.com",
]


def get_layer2_for_url(url: str, prefer_cost: bool = True) -> Layer2Mode:
    """
    Auto-select Layer 2 mode based on URL.
    
    Args:
        url: Target URL
        prefer_cost: If True, prefer cheaper modes when possible
    
    Returns:
        Recommended Layer2Mode
    """
    url_lower = url.lower()
    
    # Check browser-required sites first
    for site in BROWSER_REQUIRED_SITES:
        if site in url_lower:
            return Layer2Mode.BROWSER
    
    # Check protected sites
    for domain, mode in PROTECTED_SITES.items():
        if domain in url_lower:
            return mode
    
    # Check residential sites
    for site in RESIDENTIAL_SITES:
        if site in url_lower:
            return Layer2Mode.RESIDENTIAL
    
    # Check direct-friendly sites
    for site in DIRECT_SITES:
        if site in url_lower:
            return Layer2Mode.DIRECT
    
    # Default based on preference
    if prefer_cost:
        return Layer2Mode.DIRECT
    return Layer2Mode.RESIDENTIAL


@dataclass
class ProxyConfig:
    """Complete proxy configuration."""
    country: str
    layer2_mode: Layer2Mode = Layer2Mode.DIRECT
    
    # Computed URLs (filled by get_proxy_config)
    vpn_proxy_url: Optional[str] = None
    residential_proxy_url: Optional[str] = None
    
    # Origin verification
    origin_city: Optional[str] = None
    origin_verified: bool = False
    
    def __post_init__(self):
        cc = self.country.lower()
        self.vpn_proxy_url = f"http://vpn-{cc}:8888"
        self.residential_proxy_url = f"http://vpn-{cc}:8889"


def get_proxy_config(country: str, layer2_mode: Optional[Layer2Mode] = None, url: Optional[str] = None) -> ProxyConfig:
    """
    Get proxy configuration for a country.
    
    Args:
        country: Country code (e.g., "it", "fr", "de")
        layer2_mode: Explicit Layer 2 mode, or None for auto-select
        url: Target URL for auto-selection
    
    Returns:
        ProxyConfig with all URLs set
    """
    cc = country.lower()
    
    if cc not in SUPPORTED_COUNTRIES:
        logger.warning(f"Country {cc} not supported, defaulting to 'it'")
        cc = "it"
    
    # Auto-select Layer 2 if not specified
    if layer2_mode is None and url:
        layer2_mode = get_layer2_for_url(url)
    elif layer2_mode is None:
        layer2_mode = Layer2Mode.DIRECT
    
    return ProxyConfig(country=cc, layer2_mode=layer2_mode)


def get_all_modes() -> List[dict]:
    """Get all Layer 2 modes with their info."""
    return [
        {
            "mode": mode.value,
            **info
        }
        for mode, info in LAYER2_INFO.items()
    ]


def get_supported_countries() -> dict:
    """Get all supported countries with their info."""
    return SUPPORTED_COUNTRIES.copy()


# =============================================================================
# SOURCE TYPE TO MODE MAPPING (for frontend)
# =============================================================================

SOURCE_TYPE_MODES = {
    "google_ai": {
        "recommended": Layer2Mode.UNLOCKER,
        "supported": [Layer2Mode.UNLOCKER, Layer2Mode.BROWSER],
        "description": "Google AI Overview - requires unlocker or browser for CAPTCHA bypass",
    },
    "perplexity": {
        "recommended": Layer2Mode.BROWSER,
        "supported": [Layer2Mode.BROWSER],
        "description": "Perplexity AI - requires browser automation",
    },
    "chatgpt": {
        "recommended": Layer2Mode.BROWSER, 
        "supported": [Layer2Mode.BROWSER],
        "description": "ChatGPT - requires browser automation",
    },
    "bing": {
        "recommended": Layer2Mode.DIRECT,
        "supported": [Layer2Mode.DIRECT, Layer2Mode.RESIDENTIAL, Layer2Mode.UNLOCKER],
        "description": "Bing Search - works with most modes",
    },
    "generic": {
        "recommended": Layer2Mode.DIRECT,
        "supported": [Layer2Mode.DIRECT, Layer2Mode.RESIDENTIAL, Layer2Mode.UNLOCKER, Layer2Mode.BROWSER],
        "description": "Generic websites - all modes supported",
    },
}


def get_modes_for_source(source_type: str) -> dict:
    """Get recommended and supported modes for a source type."""
    return SOURCE_TYPE_MODES.get(source_type, SOURCE_TYPE_MODES["generic"])
