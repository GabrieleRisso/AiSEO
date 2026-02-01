"""
Proxy Layer Module - Two-Layer VPN-First Architecture

Layer 1: VPN (Always Active)
    - ProtonVPN via Gluetun containers (vpn-fr, vpn-de, etc.)
    - All traffic routes through VPN first
    - Provides base IP anonymization for selected country

Layer 2: Enhancement Mode (Optional)
    Applied on top of VPN for additional protection:
    
    - direct: VPN only (free, fastest)
    - residential: VPN + Bright Data residential IPs (~$8.40/GB)
    - unlocker: Bright Data Web Unlocker API (~$3-10/1000 req)
    - browser: Bright Data Scraping Browser (~$0.01-0.03/req)

Auto-Selection:
    - Google domains → unlocker
    - ChatGPT/Perplexity → browser
    - Social media → residential
    - Everything else → direct
"""

from .layers import (
    Layer2Mode,
    LAYER2_INFO,
    SUPPORTED_COUNTRIES,
    ProxyConfig,
    get_proxy_config,
    get_layer2_for_url,
    get_all_modes,
    get_supported_countries,
    get_modes_for_source,
    SOURCE_TYPE_MODES,
)

from .smart_scraper import (
    SmartScraper,
    ScrapeResult,
    smart_scrape,
    get_supported_calls,
    get_source_checklist,
)

# Optional imports (may not be available if dependencies missing)
try:
    from .unlocker import WebUnlockerClient, UnlockerResponse
except ImportError:
    WebUnlockerClient = None
    UnlockerResponse = None

try:
    from .residential import ResidentialProxyClient
except ImportError:
    ResidentialProxyClient = None

try:
    from .browser import ScrapingBrowserClient
except ImportError:
    ScrapingBrowserClient = None

__all__ = [
    # Layer config
    'Layer2Mode',
    'LAYER2_INFO',
    'SUPPORTED_COUNTRIES',
    'ProxyConfig',
    'get_proxy_config',
    'get_layer2_for_url',
    'get_all_modes',
    'get_supported_countries',
    'get_modes_for_source',
    'SOURCE_TYPE_MODES',
    # Smart scraper
    'SmartScraper',
    'ScrapeResult',
    'smart_scrape',
    'get_supported_calls',
    'get_source_checklist',
    # Clients
    'WebUnlockerClient',
    'UnlockerResponse',
    'ResidentialProxyClient',
    'ScrapingBrowserClient',
]
