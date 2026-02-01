import os
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dataclasses import asdict

# Import scrapers from new organized structure
from src.scrapers.google import GoogleAIScraper
from src.scrapers.google.scraper import ScrapeResult
from src.scrapers.perplexity import PerplexityScraper
from src.scrapers.chatgpt import ChatGPTScraper
from src.scrapers.common.base import BaseScraper

try:
    from src.scrapers.common.brightdata_browser import BrightDataBrowserScraper, scrape_with_browser
    SCRAPING_BROWSER_AVAILABLE = True
except ImportError:
    SCRAPING_BROWSER_AVAILABLE = False

# BrightDataScraper is deprecated, use BrightDataBrowserScraper instead
BrightDataScraper = None
from src.lib.antidetect import AntiDetectLayer, AntiDetectConfig
from src.lib.profiles import ProfileManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scraper_api")

app = FastAPI(
    title="AiSEO Scraper API",
    description="""
    Scraper API service for AiSEO platform. Provides endpoints for executing web scraping jobs
    with support for multiple scrapers (Google AI, Perplexity, BrightData), anti-detection features,
    and proxy management.
    
    ## Features
    - Multiple scraper types (Google AI, Perplexity, BrightData)
    - Anti-detection browser fingerprinting
    - VPN and residential proxy support
    - Screenshot capture
    - Real-time scraping execution
    """,
    version="1.0.0",
    tags_metadata=[
        {
            "name": "health",
            "description": "Health check and service status endpoints",
        },
        {
            "name": "config",
            "description": "Configuration and system information endpoints",
        },
        {
            "name": "scraping",
            "description": "Web scraping execution endpoints",
        },
    ],
)

def get_scraper_class(scraper_type: str):
    """
    Factory function to get the appropriate scraper class.
    
    Args:
        scraper_type: Type of scraper to use. Options:
            - "google_ai": Google AI Overview scraper (default)
            - "perplexity": Perplexity AI scraper
            - "brightdata": BrightData residential proxy scraper
            - "chatgpt": ChatGPT scraper
    
    Returns:
        Scraper class matching the type, or GoogleAIScraper as default
    """
    scrapers = {
        "google_ai": GoogleAIScraper,
        "perplexity": PerplexityScraper,
        "chatgpt": ChatGPTScraper,
        # "brightdata" is now handled via BrightDataBrowserScraper
    }
    return scrapers.get(scraper_type, GoogleAIScraper)

class ScrapeRequest(BaseModel):
    """Request model for scraping operations"""
    query: str = Field(..., description="Search query to scrape", example="best seo tools")
    country: str = Field(default="us", description="Country code for geolocation", example="us")
    num_results: Optional[int] = Field(default=None, description="Number of results to return", example=10)
    scraper_type: str = Field(default="google_ai", description="Type of scraper to use", example="google_ai")
    anti_detect_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Anti-detection configuration for browser fingerprinting",
        example={
            "enabled": True,
            "target_country": "US",
            "device_type": "desktop",
            "os": "windows",
            "browser": "chrome",
            "human_typing": True,
            "human_mouse": True,
            "random_delays": True
        }
    )
    take_screenshot: bool = Field(default=False, description="Capture screenshot during scraping", example=False)
    headless: bool = Field(default=True, description="Run browser in headless mode", example=True)
    
    # Proxy Layer Selection
    proxy_layer: str = Field(
        default="auto",
        description="""Proxy layer to use. Options:
        - 'auto': Automatically select best layer for the target site (recommended)
        - 'vpn_direct': Layer 1 - VPN datacenter IP (cheapest, free after subscription)
        - 'residential': Layer 2 - VPN + Bright Data residential (~$8.40/GB)
        - 'web_unlocker': Layer 3 - Bright Data Web Unlocker API (~$3-10/1000 requests)
        - 'scraping_browser': Layer 4 - Cloud browser with CAPTCHA solving (~$0.01-0.03/request)
        """,
        example="auto"
    )
    use_residential_proxy: bool = Field(default=False, description="[DEPRECATED] Use proxy_layer='residential' instead", example=False)
    use_scraping_browser: bool = Field(default=False, description="[DEPRECATED] Use proxy_layer='scraping_browser' instead", example=False)
    use_web_unlocker: bool = Field(default=False, description="Use Bright Data Web Unlocker API for managed unlocking", example=False)
    human_behavior: bool = Field(default=True, description="Enable human-like behavior simulation", example=True)
    
    # Smart scraper settings
    prefer_cost: bool = Field(default=True, description="Prefer cheaper proxy layers when auto-selecting", example=True)
    enable_fallback: bool = Field(default=True, description="Enable fallback to more expensive layers on failure", example=True)
    
    # Viewport/Profile settings for Scraping Browser
    profile: str = Field(
        default="desktop_1080p", 
        description="""Device viewport profile for Scraping Browser. Options:
        - Types: 'phone', 'tablet', 'desktop' (uses default for that type)
        - Phones: 'iphone_14', 'iphone_15_pro', 'pixel_7', 'samsung_s23'
        - Tablets: 'ipad_pro_12', 'ipad_air', 'galaxy_tab_s8'  
        - Desktops: 'desktop_1080p', 'desktop_1440p', 'macbook_pro_14', 'macbook_air_13', 'linux_desktop'
        """,
        example="desktop_1080p"
    )
    custom_viewport: Optional[Dict[str, int]] = Field(
        default=None,
        description="Custom viewport dimensions (overrides profile). Format: {'width': int, 'height': int}",
        example={"width": 1920, "height": 1080}
    )
    scroll_full_page: bool = Field(
        default=True, 
        description="Scroll page to load all dynamic content for full text extraction",
        example=True
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "best seo tools",
                "country": "us",
                "num_results": 10,
                "scraper_type": "google_ai",
                "take_screenshot": False,
                "headless": True,
                "proxy_layer": "auto",
                "prefer_cost": True,
                "enable_fallback": True,
                "profile": "desktop_1080p",
                "scroll_full_page": True
            }
        }

def get_proxy_for_country(country_code: str, use_residential: bool = False) -> Optional[str]:
    """
    Get the proxy URL for a given country code.
    
    This function resolves the appropriate proxy URL based on:
    1. Country code (e.g., "us", "it", "fr")
    2. Proxy type preference (residential vs datacenter)
    
    Proxy Resolution Priority:
    - Residential Proxy (if use_residential=True):
      1. Check for custom RESIDENTIAL_PROXY_{COUNTRY} env var
      2. Use standard sidecar convention: http://vpn-{country}:8889
      3. Fall back to datacenter VPN if no residential available
    
    - Datacenter VPN (if use_residential=False):
      1. Check for PROXY_{COUNTRY} env var
      2. Use standard VPN container format: http://vpn-{country}:8888
    
    Network Chain:
    - Datacenter: Client → VPN Container (ProtonVPN) → Target
    - Residential: Client → VPN Container → GOST Sidecar → Bright Data Residential → Target
    
    Args:
        country_code: Two-letter country code (lowercase, e.g., "us", "it")
        use_residential: If True, prefer residential proxy over datacenter VPN
    
    Returns:
        Proxy URL string (e.g., "http://vpn-us:8888") or None if not found
    
    Examples:
        >>> get_proxy_for_country("fr")
        'http://vpn-fr:8888'
        
        >>> get_proxy_for_country("it", use_residential=True)
        'http://vpn-it:8889'
    """
    country_code = country_code.lower()
    
    # All supported countries with VPN + Residential proxy sidecars
    supported_countries = ["fr", "de", "nl", "it", "es", "uk", "ch", "se"]
    
    # Priority 1: Residential Proxy (VPN -> Bright Data chain)
    if use_residential:
        # Check for custom env var override first
        env_var_name = f"RESIDENTIAL_PROXY_{country_code.upper()}"
        if os.environ.get(env_var_name):
            proxy = os.environ.get(env_var_name)
            logger.info(f"Using Residential Proxy for {country_code}: {proxy} (Env Var)")
            return proxy
            
        # Use standard sidecar convention for all supported countries
        if country_code in supported_countries:
            proxy = f"http://vpn-{country_code}:8889"
            logger.info(f"Using Residential Proxy Sidecar for {country_code}: {proxy}")
            return proxy
            
        # If country not supported for residential, warn and fall back
        logger.warning(f"No residential sidecar for {country_code}, falling back to datacenter VPN")

    # Priority 2: Standard Datacenter VPN (Gluetun)
    env_var_name = f"PROXY_{country_code.upper()}"
    proxy_url = os.environ.get(env_var_name)
    
    if not proxy_url and country_code in supported_countries:
        proxy_url = f"http://vpn-{country_code}:8888"
            
    if proxy_url:
        logger.info(f"Using Datacenter VPN Proxy for {country_code}: {proxy_url}")
    else:
        logger.warning(f"No proxy configuration found for {country_code}")
        
    return proxy_url


def get_all_proxy_configs() -> dict:
    """
    Get all available proxy configurations.
    
    Returns a dict with:
    - datacenter: Dict of country -> VPN proxy URL
    - residential: Dict of country -> Residential proxy URL
    - supported_countries: List of all supported country codes
    """
    supported_countries = ["fr", "de", "nl", "it", "es", "uk", "ch", "se"]
    
    datacenter = {}
    residential = {}
    
    for cc in supported_countries:
        # Check env var or use default
        dc_env = f"PROXY_{cc.upper()}"
        res_env = f"RESIDENTIAL_PROXY_{cc.upper()}"
        
        datacenter[cc] = os.environ.get(dc_env, f"http://vpn-{cc}:8888")
        residential[cc] = os.environ.get(res_env, f"http://vpn-{cc}:8889")
    
    return {
        "datacenter": datacenter,
        "residential": residential,
        "supported_countries": supported_countries,
    }

@app.get(
    "/config",
    tags=["config"],
    summary="Get scraper configuration",
    description="""
    Returns available system configuration including:
    - Supported scraper types (google_ai, perplexity, brightdata, chatgpt)
    - Available proxy countries (datacenter and residential)
    - Proxy type options
    - Default scraper type
    """,
    response_description="Configuration object with scrapers and proxies",
    responses={
        200: {
            "description": "Configuration retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "scrapers": ["google_ai", "perplexity", "brightdata", "chatgpt"],
                        "proxies": {
                            "datacenter": {"fr": "http://vpn-fr:8888", "...": "..."},
                            "residential": {"fr": "http://vpn-fr:8889", "...": "..."},
                            "supported_countries": ["fr", "de", "nl", "it", "es", "uk", "ch", "se"]
                        },
                        "default_scraper": "google_ai",
                        "scraping_browser_available": True
                    }
                }
            }
        }
    }
)
def get_config():
    """
    Get available scraper configuration.
    
    Returns information about:
    - Available scraper types (google_ai, perplexity, brightdata, chatgpt)
    - Configured proxy countries with both datacenter and residential options
    - Default scraper selection (google_ai)
    - Whether Scraping Browser is available
    
    Returns:
        dict: Configuration object with scrapers, proxies, and capabilities
    
    Example Response:
        {
            "scrapers": ["google_ai", "perplexity", "brightdata", "chatgpt"],
            "proxies": {
                "datacenter": {"fr": "http://vpn-fr:8888", ...},
                "residential": {"fr": "http://vpn-fr:8889", ...},
                "supported_countries": ["fr", "de", "nl", "it", "es", "uk", "ch", "se"]
            },
            "default_scraper": "google_ai",
            "scraping_browser_available": true
        }
    """
    proxy_configs = get_all_proxy_configs()
    
    return {
        "scrapers": ["google_ai", "perplexity", "brightdata", "chatgpt"],
        "proxies": proxy_configs,
        "default_scraper": "google_ai",
        "scraping_browser_available": SCRAPING_BROWSER_AVAILABLE,
        "proxy_types": {
            "datacenter": "VPN direct (ProtonVPN via Gluetun) - port 8888",
            "residential": "VPN + Bright Data residential chain - port 8889",
            "scraping_browser": "Bright Data cloud browser with auto-CAPTCHA"
        }
    }

def log_network_chain(country: str, layer2_mode: str, profile: str) -> dict:
    """
    Log the full network chain for traceability.
    
    Two-Layer Architecture:
    - Layer 1: VPN (always active)
    - Layer 2: Enhancement mode (direct, residential, unlocker, browser)
    
    Returns origin verification info.
    """
    from src.utils.logger import Log, C
    import requests
    
    vpn_country = country.upper()
    vpn_host = f"vpn-{country.lower()}"
    vpn_proxy = f"http://vpn-{country.lower()}:8888"
    
    origin_info = {
        "ip": None,
        "city": None,
        "country": None,
        "verified": False,
        "warning": None,
    }
    
    print(f"\n{C.CYAN}{C.BOLD}═══════════════════════════════════════════════════════════════{C.RST}")
    print(f"{C.CYAN}{C.BOLD}           TWO-LAYER PROXY CONFIGURATION                       {C.RST}")
    print(f"{C.CYAN}{C.BOLD}═══════════════════════════════════════════════════════════════{C.RST}")
    
    # Layer 1: VPN (Always Active)
    print(f"\n{C.YELLOW}[Layer 1: VPN - Always Active]{C.RST}")
    print(f"  ├─ Provider:  ProtonVPN (via Gluetun)")
    print(f"  ├─ Target:    {vpn_country}")
    print(f"  ├─ Container: {vpn_host}")
    print(f"  └─ HTTP Proxy: {vpn_proxy}")
    
    # Verify VPN IP (except for browser mode which verifies separately)
    if layer2_mode != "browser":
        try:
            resp = requests.get(
                "https://ipinfo.io/json",
                proxies={"http": vpn_proxy, "https": vpn_proxy},
                timeout=10
            )
            if resp.status_code == 200:
                geo = resp.json()
                origin_info["ip"] = geo.get("ip", "Unknown")
                origin_info["city"] = geo.get("city", "Unknown")
                origin_info["country"] = geo.get("country", "Unknown")
                
                print(f"\n{C.GREEN}[VPN Origin Verified]{C.RST}")
                print(f"  ├─ IP:       {origin_info['ip']}")
                print(f"  ├─ Country:  {origin_info['country']}")
                print(f"  └─ City:     {origin_info['city']}")
                
                # Check for Zurich (ProtonVPN HQ) - incorrect routing
                city_lower = origin_info["city"].lower() if origin_info["city"] else ""
                is_zurich = any(z in city_lower for z in ["zurich", "zürich", "zuerich"])
                
                if is_zurich and vpn_country != "CH":
                    origin_info["warning"] = f"⚠️ Origin is Zurich (ProtonVPN HQ) but target is {vpn_country}. VPN may not be routing correctly."
                    print(f"\n  {C.RED}{origin_info['warning']}{C.RST}")
                    print(f"  {C.RED}Check PROTONVPN_KEY_{vpn_country} in .env{C.RST}")
                elif origin_info["country"].upper() != vpn_country:
                    origin_info["warning"] = f"⚠️ Origin country is {origin_info['country']} but expected {vpn_country}. VPN key may be incorrect."
                    print(f"\n  {C.YELLOW}{origin_info['warning']}{C.RST}")
                else:
                    origin_info["verified"] = True
                    print(f"  {C.GREEN}✓ Origin verified for {vpn_country}{C.RST}")
                    
        except Exception as e:
            origin_info["warning"] = f"VPN IP verification failed: {e}"
            print(f"  {C.YELLOW}⚠ {origin_info['warning']}{C.RST}")
    
    # Layer 2: Enhancement Mode
    print(f"\n{C.YELLOW}[Layer 2: Enhancement Mode]{C.RST}")
    
    layer2_info = {
        "direct": ("VPN Only (Datacenter)", "Free", f"Client → [{vpn_host}] → Target"),
        "residential": ("Residential IP", "~$8.40/GB", f"Client → [{vpn_host}] → [Bright Data Residential] → Target"),
        "unlocker": ("Web Unlocker API", "~$3-10/1000 req", f"Client → [Bright Data Unlocker] → Target"),
        "browser": ("Cloud Browser", "~$0.01-0.03/req", f"Client → [Bright Data Browser ({vpn_country})] → Target"),
    }
    
    mode_name, mode_cost, chain = layer2_info.get(layer2_mode, layer2_info["direct"])
    
    print(f"  ├─ Mode:      {layer2_mode}")
    print(f"  ├─ Type:      {mode_name}")
    print(f"  └─ Cost:      {mode_cost}")
    
    # Device Profile
    print(f"\n{C.YELLOW}[Device Profile]{C.RST}")
    print(f"  └─ Profile:   {profile}")
    
    # Network Path
    print(f"\n{C.GREEN}[Network Path]{C.RST}")
    print(f"  {chain}")
    print(f"{C.CYAN}═══════════════════════════════════════════════════════════════{C.RST}\n")
    
    return origin_info


def resolve_layer2_mode(request) -> str:
    """
    Resolve the Layer 2 mode from request parameters.
    
    Priority:
    1. Explicit proxy_layer parameter
    2. Legacy use_scraping_browser flag
    3. Legacy use_residential_proxy flag
    4. Auto-select based on scraper_type
    """
    # Handle explicit proxy_layer
    if request.proxy_layer and request.proxy_layer != "auto":
        # Map old names to new
        layer_map = {
            "vpn_direct": "direct",
            "web_unlocker": "unlocker",
            "scraping_browser": "browser",
        }
        return layer_map.get(request.proxy_layer, request.proxy_layer)
    
    # Handle legacy flags
    if request.use_scraping_browser:
        return "browser"
    if request.use_residential_proxy:
        return "residential"
    if request.use_web_unlocker:
        return "unlocker"
    
    # Auto-select based on scraper type
    scraper_modes = {
        "google_ai": "unlocker",  # Google requires CAPTCHA bypass
        "chatgpt": "browser",      # ChatGPT requires browser automation
        "perplexity": "browser",   # Perplexity requires browser automation
    }
    
    if request.proxy_layer == "auto":
        return scraper_modes.get(request.scraper_type, "direct")
    
    return "direct"


@app.post(
    "/scrape",
    tags=["scraping"],
    summary="Execute scraping job",
    description="""
    Execute a web scraping job with the specified configuration.
    
    ## Scraper Types
    - **google_ai**: Google AI Overview scraper (default)
    - **perplexity**: Perplexity AI scraper
    - **brightdata**: BrightData residential proxy scraper
    - **chatgpt**: ChatGPT scraper
    
    ## Proxy Options
    - **Datacenter VPN**: Standard VPN proxy (use_residential_proxy=false)
    - **Residential Proxy**: Residential IP proxy via sidecar (use_residential_proxy=true)
    
    ## Anti-Detection
    Configure browser fingerprinting to avoid detection:
    - Device type (desktop, mobile, tablet)
    - OS (windows, mac, linux, android, ios)
    - Browser (chrome, firefox, safari)
    - Human-like behavior (typing, mouse movements, delays)
    """,
    response_description="Scraping result with sources, metadata, and status",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Scraping completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": [
                            {
                                "url": "https://example.com/article",
                                "title": "Example Article",
                                "description": "Article description",
                                "publisher": "Example.com"
                            }
                        ],
                        "response_text": "Full AI response text...",
                        "metadata": {
                            "source_count": 10,
                            "timestamp": "2026-01-31T18:00:00",
                            "proxy_used": "http://vpn-us:8888",
                            "scraper_type": "google_ai",
                            "profile": {}
                        }
                    }
                }
            }
        },
        500: {
            "description": "Scraping failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Error message describing the failure"
                    }
                }
            }
        }
    }
)
async def run_scrape(request: ScrapeRequest):
    """
    Execute a scraping job synchronously.
    
    This endpoint runs a scraping operation and returns results immediately.
    For long-running or scheduled jobs, use the job management API instead.
    
    **Request Parameters:**
    - `query` (str): The search query to scrape (required)
    - `country` (str): Country code for geolocation (default: "us")
    - `scraper_type` (str): Type of scraper - google_ai, perplexity, brightdata, chatgpt (default: "google_ai")
    - `num_results` (int): Number of results to return (optional)
    - `use_residential_proxy` (bool): Use residential proxy instead of datacenter VPN (default: False)
    - `anti_detect_config` (dict): Browser fingerprinting configuration (optional)
    - `take_screenshot` (bool): Capture screenshot during scraping (default: False)
    - `headless` (bool): Run browser in headless mode (default: True)
    
    **Response Structure:**
    - `status` (str): "success" or "failed"
    - `data` (list): Array of scraped sources with url, title, description, publisher
    - `response_text` (str): Full AI response text
    - `metadata` (dict): Scraping metadata including:
        - `source_count`: Number of sources found
        - `timestamp`: When scraping occurred
        - `proxy_used`: Proxy URL used
        - `scraper_type`: Scraper used
        - `profile`: Anti-detection profile info (if enabled)
    
    **Example Request:**
        {
            "query": "best seo tools",
            "country": "us",
            "scraper_type": "google_ai",
            "num_results": 10
        }
    
    **Example Response:**
        {
            "status": "success",
            "data": [...],
            "response_text": "...",
            "metadata": {...}
        }
    """
    # Resolve Layer 2 mode
    layer2_mode = resolve_layer2_mode(request)
    
    logger.info(f"Scrape request: {request.query} [{request.country}] scraper={request.scraper_type} layer2={layer2_mode}")
    
    # Build proxy config
    from src.scrapers.common.base import ProxyLayerConfig
    proxy_config = ProxyLayerConfig(country=request.country, layer2_mode=layer2_mode)
    proxy_url = proxy_config.active_proxy
    
    logger.info(f"Layer 1 (VPN): {proxy_config.vpn_proxy_url}")
    logger.info(f"Layer 2 ({layer2_mode}): {proxy_url}")
    
    # Log and verify origin
    origin_info = log_network_chain(
        country=request.country,
        layer2_mode=layer2_mode,
        profile=request.profile
    )
    
    # Update proxy config with origin info
    proxy_config.origin_ip = origin_info.get("ip")
    proxy_config.origin_city = origin_info.get("city")
    proxy_config.origin_country = origin_info.get("country")
    proxy_config.origin_verified = origin_info.get("verified", False)
    proxy_config.origin_warning = origin_info.get("warning")

    # 2. Configure Anti-Detect
    ad_config = AntiDetectConfig()
    antidetect = None
    
    if request.anti_detect_config:
        # Update config from request
        for k, v in request.anti_detect_config.items():
            if hasattr(ad_config, k):
                setattr(ad_config, k, v)
        
        # Ensure target country matches
        ad_config.target_country = request.country.upper()
        # Explicitly enable if config passed
        ad_config.enabled = request.anti_detect_config.get("enabled", True)
        
        if ad_config.enabled:
            antidetect = AntiDetectLayer(ad_config)
    
    # 3. Run Scraper
    try:
        # Check if browser mode is requested
        use_browser = (layer2_mode == "browser") and SCRAPING_BROWSER_AVAILABLE
        
        if use_browser:
            logger.info(f"Using Bright Data Scraping Browser for {request.scraper_type}")
            logger.info(f"Profile: {request.profile}, Viewport: {request.custom_viewport}, Scroll: {request.scroll_full_page}")
            
            result = await scrape_with_browser(
                query=request.query,
                country=request.country,
                scraper_type=request.scraper_type,
                take_screenshot=request.take_screenshot,
                profile=request.profile,
                custom_viewport=request.custom_viewport,
                scroll_full_page=request.scroll_full_page,
            )
            
            # Build full request config for traceability
            request_config = {
                "query": request.query,
                "country": request.country,
                "scraper_type": request.scraper_type,
                "layer2_mode": layer2_mode,
                "profile": request.profile,
                "custom_viewport": request.custom_viewport,
                "scroll_full_page": request.scroll_full_page,
                "take_screenshot": request.take_screenshot,
                "headless": request.headless,
                "human_behavior": request.human_behavior,
            }
            
            # Build network chain info for traceability
            browser_geo = result.connectivity_info.get("browser_geo", {}) if result.connectivity_info else {}
            network_chain = {
                "layer1_vpn": {
                    "provider": "ProtonVPN (Gluetun)",
                    "target_country": request.country.upper(),
                    "container": f"vpn-{request.country.lower()}",
                    "proxy_url": proxy_config.vpn_proxy_url,
                    "note": "VPN container available but Browser uses Bright Data's network",
                },
                "layer2_mode": layer2_mode,
                "layer2_browser": {
                    "type": "Cloud Browser",
                    "method": "CDP over WebSocket",
                    "endpoint": "wss://brd.superproxy.io:9222",
                    "target_country": request.country.upper(),
                    "country_flag": f"-country-{request.country.lower()}",
                    "features": ["Auto CAPTCHA", "Fingerprint Management", "Residential IPs"],
                    "verified_ip": browser_geo.get("ip"),
                    "verified_country": browser_geo.get("country"),
                    "verified_city": browser_geo.get("city"),
                    "country_match": browser_geo.get("country_match", False),
                },
                "device_profile": result.profile_info if result.profile_info else {
                    "profile_name": request.profile,
                    "device_type": "phone" if any(x in request.profile for x in ["phone", "iphone", "pixel", "samsung"]) else "desktop",
                },
                "chain_path": f"Client → [Bright Data Browser ({request.country.upper()})] → Target"
            }
            
            # Convert result to dict format with full extraction data
            result_dict = {
                "status": "success" if result.success else "failed",
                "data": result.sources,
                "response_text": result.response_text,
                "html_content": result.html_content,
                "error": result.error,
                "metadata": {
                    "source_count": result.source_count,
                    "timestamp": result.timestamp,
                    "connectivity_info": result.connectivity_info,
                    "method": "scraping_browser",
                    "scraper_type": request.scraper_type,
                    "cost_estimate": result.cost_estimate,
                    "profile_info": result.profile_info,
                    "extraction_stats": result.extraction_stats,
                    "network_chain": network_chain,
                    "request_config": request_config,
                }
            }
            return result_dict
        elif layer2_mode == "browser" and not SCRAPING_BROWSER_AVAILABLE:
            logger.warning("Browser mode requested but playwright not available, falling back to direct")
        
        ScraperClass = get_scraper_class(request.scraper_type)
        
        # Pass proxy config to scraper
        with ScraperClass(headless=request.headless, proxy=proxy_url, antidetect=antidetect, proxy_config=proxy_config) as scraper:
            result = await scraper.scrape(request.query, take_screenshot=request.take_screenshot)
            
            # Enrich/Normalize metadata
            result_dict = {}
            if not isinstance(result, dict):
                # Handle dataclass result (legacy GoogleAIScraper)
                result_dict = {
                    "status": "success" if getattr(result, "success", True) else "failed",
                    "data": [asdict(d) for d in getattr(result, "sources", [])],
                    "response_text": getattr(result, "response_text", ""),
                    "html_content": getattr(result, "html_content", ""),
                    "error": getattr(result, "error", None),
                    "metadata": {
                        "source_count": getattr(result, "source_count", 0),
                        "timestamp": getattr(result, "timestamp", ""),
                    }
                }
            else:
                result_dict = result
            
            # Ensure metadata exists
            if "metadata" not in result_dict:
                result_dict["metadata"] = {}
            
            # Add proxy layer info
            result_dict["metadata"]["proxy_layer"] = {
                "layer1_vpn": {
                    "country": proxy_config.country.upper(),
                    "proxy_url": proxy_config.vpn_proxy_url,
                },
                "layer2_mode": layer2_mode,
                "active_proxy": proxy_url,
                "origin": {
                    "ip": proxy_config.origin_ip,
                    "city": proxy_config.origin_city,
                    "country": proxy_config.origin_country,
                    "verified": proxy_config.origin_verified,
                    "warning": proxy_config.origin_warning,
                },
            }

            # Add anti-detect metadata if active
            if antidetect and antidetect.is_active:
                result_dict["metadata"]["profile"] = antidetect.get_metadata()
            elif antidetect:
                 result_dict["metadata"]["profile"] = antidetect.check_status()
                
            result_dict["metadata"]["proxy_used"] = proxy_url
            result_dict["metadata"]["scraper_type"] = request.scraper_type
            
            return result_dict
        
    except Exception as e:
        logger.exception("Error during scraping")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/profiles",
    tags=["config"],
    summary="Get available viewport profiles",
    description="""
    Returns all available viewport profiles for Scraping Browser.
    
    Profiles are grouped by device type:
    - **phone**: Mobile phone viewports (iPhone, Pixel, Samsung)
    - **tablet**: Tablet viewports (iPad, Galaxy Tab)
    - **desktop**: Desktop viewports (1080p, 1440p, MacBook)
    """,
    response_description="Available viewport profiles grouped by device type",
)
async def get_profiles():
    """
    Get available viewport profiles for Scraping Browser.
    
    Returns profiles organized by device type with viewport dimensions.
    """
    if SCRAPING_BROWSER_AVAILABLE:
        from src.scrapers.brightdata_browser_scraper import get_available_profiles, get_cost_info
        return {
            "profiles": get_available_profiles(),
            "cost_info": get_cost_info(),
            "default_profiles": {
                "phone": "iphone_14",
                "tablet": "ipad_air", 
                "desktop": "desktop_1080p"
            }
        }
    else:
        return {
            "error": "Scraping Browser not available (playwright not installed)",
            "profiles": {},
            "cost_info": {}
        }


@app.get(
    "/proxies",
    tags=["config"],
    summary="Get all proxy configurations",
    description="""
    Returns detailed proxy configuration for all supported countries.
    
    For each country, provides:
    - VPN Direct proxy URL (datacenter IP via ProtonVPN)
    - Residential proxy URL (VPN + Bright Data chain)
    - External ports for host access
    - Internal Docker network URLs
    """,
    response_description="Proxy configurations by country",
)
async def get_proxies():
    """
    Get all proxy configurations with detailed information.
    
    Returns proxy URLs for both internal Docker network access and
    external host access for each supported country.
    """
    proxy_configs = get_all_proxy_configs()
    
    detailed = {}
    port_base = {
        'fr': 1, 'de': 2, 'nl': 3, 'it': 4, 
        'es': 5, 'uk': 6, 'ch': 7, 'se': 8
    }
    
    for cc in proxy_configs['supported_countries']:
        base = port_base.get(cc, 0)
        detailed[cc] = {
            "country_name": {
                'fr': 'France', 'de': 'Germany', 'nl': 'Netherlands', 'it': 'Italy',
                'es': 'Spain', 'uk': 'United Kingdom', 'ch': 'Switzerland', 'se': 'Sweden'
            }.get(cc, cc.upper()),
            "datacenter": {
                "internal": proxy_configs['datacenter'].get(cc),
                "external": f"http://localhost:{8000 + base}",
                "description": "VPN direct (ProtonVPN datacenter IP)"
            },
            "residential": {
                "internal": proxy_configs['residential'].get(cc),
                "external": f"http://localhost:{8100 + base}",
                "description": "VPN + Bright Data residential chain"
            },
            "control_port": 9000 + base,
        }
    
    return {
        "proxies": detailed,
        "usage": {
            "internal": "Use internal URLs when calling from Docker containers",
            "external": "Use external URLs when calling from host machine",
            "residential": "Use residential for sites that block datacenter IPs",
            "scraping_browser": "Use scraping_browser for Google/sites with CAPTCHA"
        }
    }


@app.get(
    "/layers",
    tags=["config"],
    summary="Get proxy layer information",
    description="""
    Returns information about the two-layer proxy system.
    
    ## Layer 1: VPN (Always Active)
    All traffic routes through ProtonVPN first for the selected country.
    
    ## Layer 2: Enhancement Mode (Optional)
    Applied on top of VPN for additional protection:
    - **direct**: VPN only (free)
    - **residential**: VPN + Bright Data residential IPs (~$8.40/GB)
    - **unlocker**: Bright Data Web Unlocker API (~$3-10/1000 req)
    - **browser**: Bright Data Scraping Browser (~$0.01-0.03/req)
    """,
)
async def get_layers():
    """Get information about proxy layers."""
    try:
        from src.proxy.layers import LAYER2_INFO, Layer2Mode, SUPPORTED_COUNTRIES
        
        layer2_modes = {}
        for mode in Layer2Mode:
            info = LAYER2_INFO.get(mode, {})
            layer2_modes[mode.value] = {
                "name": info.get("name"),
                "description": info.get("description"),
                "cost": info.get("cost"),
                "best_for": info.get("best_for", []),
                "success_rate": info.get("success_rate", 0),
            }
        
        return {
            "layer1": {
                "name": "VPN",
                "description": "ProtonVPN - always active for selected country",
                "countries": list(SUPPORTED_COUNTRIES.keys()),
            },
            "layer2_modes": layer2_modes,
            "auto_selection": {
                "google": "unlocker",
                "chatgpt": "browser",
                "perplexity": "browser",
                "generic": "direct",
            },
        }
    except ImportError:
        return {"error": "Proxy layers module not available"}


@app.get(
    "/source-checklist",
    tags=["config"],
    summary="Get supported modes for each source type",
    description="Returns which Layer 2 modes work for each scraper/source type.",
)
async def get_source_checklist():
    """Get checklist of supported modes for each source type."""
    try:
        from src.proxy.smart_scraper import get_source_checklist
        return get_source_checklist()
    except ImportError:
        return {
            "google_ai": {"browser": True, "unlocker": True, "notes": "Requires CAPTCHA bypass"},
            "perplexity": {"browser": True, "notes": "Requires browser automation"},
            "chatgpt": {"browser": True, "notes": "Requires browser automation"},
        }


@app.post(
    "/smart-scrape",
    tags=["scraping"],
    summary="Smart scrape with VPN-first routing",
    description="""
    Scrape a URL with automatic layer selection.
    
    **Layer 1 (VPN)**: Always routes through ProtonVPN for selected country
    **Layer 2 (Enhancement)**: Auto-selected based on URL, or specify manually
    
    ## Layer 2 Modes
    - `direct`: VPN only (free, fastest)
    - `residential`: VPN + residential IPs (for sites blocking datacenter)
    - `unlocker`: Web Unlocker API (for Google, Amazon, LinkedIn)
    - `browser`: Full browser (for ChatGPT, Perplexity)
    
    ## Auto-Selection
    - Google domains → unlocker
    - ChatGPT/Perplexity → browser
    - Social media → residential
    - Everything else → direct
    """,
)
async def smart_scrape_endpoint(
    url: str,
    country: str = "it",
    layer2: Optional[str] = None,
    enable_fallback: bool = True,
):
    """
    Smart scrape with VPN-first routing.
    
    Args:
        url: Target URL to scrape
        country: Country code (fr, de, nl, it, es, uk, ch, se)
        layer2: Layer 2 mode (direct, residential, unlocker, browser) or None for auto
        enable_fallback: Enable fallback to more expensive modes on failure
    """
    try:
        from src.proxy.smart_scraper import SmartScraper
        from dataclasses import asdict
        
        scraper = SmartScraper(
            country=country,
            enable_fallback=enable_fallback,
            verify_origin=True,
        )
        
        result = await scraper.scrape(url, layer2=layer2)
        
        # Build response
        response = {
            "success": result.success,
            "url": result.url,
            "content_length": len(result.content) if result.content else 0,
            
            # Layer info
            "layer1_vpn": {
                "country": result.country.upper(),
                "proxy": f"http://vpn-{result.country}:8888",
            },
            "layer2_mode": result.layer2_mode,
            
            # Origin verification
            "origin": {
                "ip": result.origin_ip,
                "city": result.origin_city,
                "country": result.origin_country,
                "verified": result.origin_verified,
                "warning": result.origin_warning,
            },
            
            # Performance
            "performance": {
                "duration_seconds": result.duration_seconds,
                "data_kb": result.data_kb,
                "estimated_cost_usd": result.estimated_cost_usd,
                "attempts": result.attempts,
                "fallback_used": result.fallback_used,
            },
            
            "error": result.error,
        }
        
        # Include content if not too large
        if result.content and len(result.content) < 100000:
            response["content"] = result.content
        elif result.content:
            response["content"] = result.content[:100000] + "...[truncated]"
        else:
            response["content"] = ""
        
        return response
        
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Smart scraper not available: {e}")
    except Exception as e:
        logger.exception("Error during smart scrape")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/unlock",
    tags=["scraping"],
    summary="Web Unlocker API (for protected sites)",
    description="""
    Fetch a URL using Bright Data's Web Unlocker API.
    
    Best for: Google, Amazon, LinkedIn, and other protected sites.
    
    **Note**: This bypasses VPN and goes directly to Bright Data.
    Use /smart-scrape with layer2='unlocker' to route through VPN first.
    """,
)
async def unlock_url(
    url: str,
    country: str = "us",
):
    """Unlock a URL using Web Unlocker API."""
    try:
        from src.proxy.unlocker import WebUnlockerClient
        
        client = WebUnlockerClient(default_country=country)
        response = await client.unlock(url=url, country=country)
        
        return {
            "success": response.success,
            "status_code": response.status_code,
            "content": response.content[:100000] if response.content else "",
            "content_length": len(response.content) if response.content else 0,
            "country": response.country_used,
            "is_premium_domain": response.is_premium,
            "estimated_cost_usd": response.estimated_cost_usd,
            "error": response.error,
        }
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Web Unlocker not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api-reference",
    tags=["config"],
    summary="Get API reference with examples",
    description="Returns list of all supported API calls with examples.",
)
async def get_api_reference():
    """Get API reference with valid call examples."""
    try:
        from src.proxy.smart_scraper import get_supported_calls
        return {
            "calls": get_supported_calls(),
            "countries": ["fr", "de", "nl", "it", "es", "uk", "ch", "se"],
            "layer2_modes": ["direct", "residential", "unlocker", "browser"],
            "scraper_types": ["google_ai", "perplexity", "chatgpt"],
        }
    except ImportError:
        return {
            "calls": [],
            "countries": ["fr", "de", "nl", "it", "es", "uk", "ch", "se"],
        }


@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Check if the scraper API service is running and healthy.",
    response_description="Service status",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {"status": "ok"}
                }
            }
        }
    }
)
async def health_check():
    """
    Health check endpoint.
    
    Returns the current health status of the scraper API service.
    Use this endpoint to verify the service is running before making scraping requests.
    """
    return {"status": "ok"}
