import os
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dataclasses import asdict
from src.scrapers.google_ai_scraper import GoogleAIScraper, ScrapeResult
from src.scrapers.perplexity_scraper import PerplexityScraper
from src.scrapers.brightdata_scraper import BrightDataScraper
from src.scrapers.chatgpt_scraper import ChatGPTScraper
from src.scrapers.base import BaseScraper
try:
    from src.scrapers.brightdata_browser_scraper import BrightDataBrowserScraper, scrape_with_browser
    SCRAPING_BROWSER_AVAILABLE = True
except ImportError:
    SCRAPING_BROWSER_AVAILABLE = False
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
        "brightdata": BrightDataScraper,
        "chatgpt": ChatGPTScraper
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
    use_residential_proxy: bool = Field(default=False, description="Use residential proxy instead of datacenter VPN", example=False)
    use_scraping_browser: bool = Field(default=False, description="Use Bright Data Scraping Browser (cloud browser with automatic CAPTCHA solving)", example=False)
    human_behavior: bool = Field(default=True, description="Enable human-like behavior simulation", example=True)
    
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
                "use_residential_proxy": False,
                "use_scraping_browser": True,
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
      2. Check for known sidecar proxies (e.g., Italy on port 8889)
      3. Fall back to datacenter VPN
    
    - Datacenter VPN (if use_residential=False):
      1. Check for PROXY_{COUNTRY} env var
      2. Use standard VPN container format: http://vpn-{country}:8888
    
    Args:
        country_code: Two-letter country code (lowercase, e.g., "us", "it")
        use_residential: If True, prefer residential proxy over datacenter VPN
    
    Returns:
        Proxy URL string (e.g., "http://vpn-us:8888") or None if not found
    
    Examples:
        >>> get_proxy_for_country("us")
        'http://vpn-us:8888'
        
        >>> get_proxy_for_country("it", use_residential=True)
        'http://vpn-it:8889'
    """
    country_code = country_code.lower()
    
    # Priority 1: Check if there's a specific env var override
    if use_residential:
        env_var_name = f"RESIDENTIAL_PROXY_{country_code.upper()}"
        if os.environ.get(env_var_name):
            proxy = os.environ.get(env_var_name)
            logger.info(f"Using Residential Proxy for {country_code}: {proxy} (Custom Env Var)")
            return proxy
            
        # Fallback to standard sidecar convention
        # We assume if a VPN exists for this country, we might have a sidecar on port 8889
        known_sidecars = ["it"] 
        if country_code in known_sidecars:
            proxy = f"http://vpn-{country_code}:8889"
            logger.info(f"Using Residential Proxy Sidecar for {country_code}: {proxy} (Matches VPN Country)")
            return proxy
            
        # If no sidecar, maybe fall back to standard VPN or fail?
        logger.warning(f"No residential sidecar found for {country_code}, falling back to datacenter VPN")

    # Priority 2: Standard Datacenter VPN (Gluetun)
    env_var_name = f"PROXY_{country_code.upper()}"
    proxy_url = os.environ.get(env_var_name)
    
    if not proxy_url:
        known_vpns = ["fr", "de", "nl", "it", "es", "us", "uk", "ch", "se"]
        if country_code in known_vpns:
            proxy_url = f"http://vpn-{country_code}:8888"
            
    if proxy_url:
        logger.info(f"Using Datacenter VPN Proxy for {country_code}: {proxy_url}")
    else:
        logger.warning(f"No proxy configuration found for {country_code}")
        
    return proxy_url

@app.get(
    "/config",
    tags=["config"],
    summary="Get scraper configuration",
    description="""
    Returns available system configuration including:
    - Supported scraper types (google_ai, perplexity, brightdata, chatgpt)
    - Available proxy countries
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
                        "proxies": ["ch", "de", "es", "fr", "it", "nl", "se", "uk"],
                        "default_scraper": "google_ai"
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
    - Configured proxy countries (ch, de, es, fr, it, nl, se, uk)
    - Default scraper selection (google_ai)
    
    Returns:
        dict: Configuration object with scrapers list, proxies list, and default scraper
    
    Example Response:
        {
            "scrapers": ["google_ai", "perplexity", "brightdata", "chatgpt"],
            "proxies": ["ch", "de", "es", "fr", "it", "nl", "se", "uk"],
            "default_scraper": "google_ai"
        }
    """
    # Read available proxies from environment variables
    proxies = []
    for k, v in os.environ.items():
        if k.startswith("PROXY_"):
            proxies.append(k.replace("PROXY_", "").lower())
    
    return {
        "scrapers": ["google_ai", "perplexity", "brightdata", "chatgpt"],
        "proxies": sorted(proxies),
        "default_scraper": "google_ai"
    }

def log_network_chain(country: str, vpn_proxy: str, use_residential: bool, use_scraping_browser: bool, profile: str):
    """
    Log the full network chain for traceability.
    
    Shows: Client → VPN → Proxy/Browser → Target
    """
    from src.utils.logger import Log, C
    import requests
    
    print(f"\n{C.CYAN}{C.BOLD}═══════════════════════════════════════════════════════════════{C.RST}")
    print(f"{C.CYAN}{C.BOLD}                    NETWORK CHAIN CONFIGURATION                 {C.RST}")
    print(f"{C.CYAN}{C.BOLD}═══════════════════════════════════════════════════════════════{C.RST}")
    
    # Layer 1: VPN
    vpn_country = country.upper()
    vpn_host = f"vpn-{country.lower()}"
    print(f"\n{C.YELLOW}[Layer 1: VPN]{C.RST}")
    print(f"  ├─ Provider:  ProtonVPN (via Gluetun)")
    print(f"  ├─ Target:    {vpn_country}")
    print(f"  ├─ Container: {vpn_host}")
    print(f"  └─ HTTP Proxy: {vpn_proxy or 'Not configured'}")
    
    # Verify VPN IP if proxy is available
    if vpn_proxy and not use_scraping_browser:
        try:
            resp = requests.get(
                "https://ipinfo.io/json",
                proxies={"http": vpn_proxy, "https": vpn_proxy},
                timeout=10
            )
            if resp.status_code == 200:
                geo = resp.json()
                vpn_ip = geo.get("ip", "Unknown")
                vpn_actual_country = geo.get("country", "Unknown")
                vpn_city = geo.get("city", "Unknown")
                print(f"\n{C.GREEN}[VPN IP Verified]{C.RST}")
                print(f"  ├─ IP:       {vpn_ip}")
                print(f"  ├─ Country:  {vpn_actual_country}")
                print(f"  └─ City:     {vpn_city}")
                
                if vpn_actual_country.upper() != vpn_country:
                    print(f"  {C.YELLOW}⚠ Warning: VPN country mismatch!{C.RST}")
        except Exception as e:
            print(f"  {C.YELLOW}⚠ VPN IP verification failed: {e}{C.RST}")
    
    # Layer 2: Proxy/Browser
    print(f"\n{C.YELLOW}[Layer 2: Proxy/Browser]{C.RST}")
    if use_scraping_browser:
        print(f"  ├─ Type:      Bright Data Scraping Browser (Cloud)")
        print(f"  ├─ Method:    CDP over WebSocket")
        print(f"  ├─ Country:   {vpn_country} (via -country-{country.lower()} flag)")
        print(f"  ├─ Features:  Auto CAPTCHA, Fingerprint Mgmt, Residential IPs")
        print(f"  └─ Endpoint:  wss://brd.superproxy.io:9222")
        print(f"\n  {C.CYAN}Note: Browser IP will be verified after connection{C.RST}")
    elif use_residential:
        print(f"  ├─ Type:      Bright Data Residential Proxy")
        print(f"  ├─ Method:    HTTP Proxy via gost sidecar")
        print(f"  ├─ Zone:      aiseo_1")
        print(f"  └─ Port:      8889 (via VPN tunnel)")
    else:
        print(f"  ├─ Type:      VPN Direct (Datacenter)")
        print(f"  ├─ Method:    HTTP Proxy")
        print(f"  └─ Port:      8888")
    
    # Layer 3: Device Profile
    print(f"\n{C.YELLOW}[Layer 3: Device Profile]{C.RST}")
    print(f"  └─ Profile:   {profile}")
    
    # Show the chain
    if use_scraping_browser:
        chain = f"Client → [Bright Data Browser ({vpn_country})] → Target"
    elif use_residential:
        chain = f"Client → [{vpn_host}] → [Bright Data Residential] → Target"
    else:
        chain = f"Client → [{vpn_host}] → Target"
    
    print(f"\n{C.GREEN}[Network Path]{C.RST}")
    print(f"  {chain}")
    print(f"{C.CYAN}═══════════════════════════════════════════════════════════════{C.RST}\n")


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
    logger.info(f"Received scrape request: {request.query} [{request.country}] type={request.scraper_type} residential={request.use_residential_proxy} scraping_browser={request.use_scraping_browser}")
    
    # 1. Resolve Proxy
    proxy_url = get_proxy_for_country(request.country, request.use_residential_proxy)
    if not proxy_url:
        logger.warning(f"No proxy found for country {request.country}, defaulting to None (direct connection)")
    else:
        logger.info(f"Using proxy: {proxy_url}")
    
    # Log the full network chain for traceability
    log_network_chain(
        country=request.country,
        vpn_proxy=proxy_url,
        use_residential=request.use_residential_proxy,
        use_scraping_browser=request.use_scraping_browser,
        profile=request.profile
    )

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
        # Check if Scraping Browser is requested (for Google with CAPTCHA bypass)
        if request.use_scraping_browser and SCRAPING_BROWSER_AVAILABLE:
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
                "profile": request.profile,
                "custom_viewport": request.custom_viewport,
                "scroll_full_page": request.scroll_full_page,
                "use_scraping_browser": request.use_scraping_browser,
                "use_residential_proxy": request.use_residential_proxy,
                "take_screenshot": request.take_screenshot,
                "headless": request.headless,
                "human_behavior": request.human_behavior,
            }
            
            # Build network chain info for traceability
            browser_geo = result.connectivity_info.get("browser_geo", {}) if result.connectivity_info else {}
            network_chain = {
                "layer_1_vpn": {
                    "provider": "ProtonVPN (Gluetun)",
                    "target_country": request.country.upper(),
                    "container": f"vpn-{request.country.lower()}",
                    "http_proxy": proxy_url,
                    "note": "VPN not used directly when using Scraping Browser"
                },
                "layer_2_browser": {
                    "type": "Bright Data Scraping Browser",
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
                "layer_3_profile": result.profile_info if result.profile_info else {
                    "profile_name": request.profile,
                    "device_type": "phone" if "phone" in request.profile or "iphone" in request.profile or "pixel" in request.profile or "samsung" in request.profile else "desktop",
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
        elif request.use_scraping_browser and not SCRAPING_BROWSER_AVAILABLE:
            logger.warning("Scraping Browser requested but playwright not available, falling back to standard scraper")
        
        ScraperClass = get_scraper_class(request.scraper_type)
        
        # NOTE: Removed automatic fallback logic as requested by user.
        # We rely on the configured proxy and scraper settings.
             
        # Assuming ScraperClass follows the BaseScraper interface or compatible signature
        # We pass headless from request, default to True if not specified in request (model default)
        with ScraperClass(headless=request.headless, proxy=proxy_url, antidetect=antidetect) as scraper:
            # IP Verification happens inside scraper if configured
            # Pass take_screenshot flag
            result = await scraper.scrape(request.query, take_screenshot=request.take_screenshot)
            
            # Enrich/Normalize metadata
            result_dict = {}
            if not isinstance(result, dict):
                # Handle dataclass result (legacy GoogleAIScraper)
                result_dict = {
                    "status": "success" if getattr(result, "success", True) else "failed",
                    "data": [asdict(d) for d in getattr(result, "sources", [])], # .sources for legacy
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
