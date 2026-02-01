"""
Bright Data Scraping Browser Scraper

Uses Bright Data's cloud-based Scraping Browser for sites that require
advanced anti-bot bypass (like Google). Features automatic CAPTCHA solving,
fingerprint management, and residential IP rotation.

Supports viewport profiles: phone, tablet, desktop for different extraction needs.
"""

import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from dataclasses import dataclass, asdict, field
from typing import Optional, Literal
import os

from ...utils.logger import Log, C

# Playwright is required for Scraping Browser
try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ============================================================================
# VIEWPORT PROFILES - Phone, Tablet, Desktop configurations
# ============================================================================

VIEWPORT_PROFILES = {
    # Mobile phones
    "iphone_14": {
        "type": "phone",
        "viewport": {"width": 390, "height": 844},
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
    },
    "iphone_15_pro": {
        "type": "phone",
        "viewport": {"width": 393, "height": 852},
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
    },
    "pixel_7": {
        "type": "phone",
        "viewport": {"width": 412, "height": 915},
        "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "device_scale_factor": 2.625,
        "is_mobile": True,
        "has_touch": True,
    },
    "samsung_s23": {
        "type": "phone",
        "viewport": {"width": 360, "height": 780},
        "user_agent": "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
    },
    
    # Tablets
    "ipad_pro_12": {
        "type": "tablet",
        "viewport": {"width": 1024, "height": 1366},
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "device_scale_factor": 2,
        "is_mobile": True,
        "has_touch": True,
    },
    "ipad_air": {
        "type": "tablet",
        "viewport": {"width": 820, "height": 1180},
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "device_scale_factor": 2,
        "is_mobile": True,
        "has_touch": True,
    },
    "galaxy_tab_s8": {
        "type": "tablet",
        "viewport": {"width": 800, "height": 1280},
        "user_agent": "Mozilla/5.0 (Linux; Android 14; SM-X700) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "device_scale_factor": 2,
        "is_mobile": True,
        "has_touch": True,
    },
    
    # Desktops
    "desktop_1080p": {
        "type": "desktop",
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
    },
    "desktop_1440p": {
        "type": "desktop",
        "viewport": {"width": 2560, "height": 1440},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
    },
    "macbook_pro_14": {
        "type": "desktop",
        "viewport": {"width": 1512, "height": 982},
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "device_scale_factor": 2,
        "is_mobile": False,
        "has_touch": False,
    },
    "macbook_air_13": {
        "type": "desktop",
        "viewport": {"width": 1470, "height": 956},
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "device_scale_factor": 2,
        "is_mobile": False,
        "has_touch": False,
    },
    "linux_desktop": {
        "type": "desktop",
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
    },
}

# Default profile for each device type
DEFAULT_PROFILES = {
    "phone": "iphone_14",
    "tablet": "ipad_air",
    "desktop": "desktop_1080p",
}


# ============================================================================
# COST ESTIMATION - Bright Data Scraping Browser pricing
# ============================================================================

COST_CONFIG = {
    "scraping_browser": {
        "per_gb_cost_usd": 9.50,  # $9.50/GB for Scraping Browser
        "base_request_cost_usd": 0.01,  # Estimated per-request overhead
        "avg_page_size_kb": 500,  # Average page size
        "captcha_solve_cost_usd": 0.02,  # Additional cost if CAPTCHA solved
    },
    "residential_proxy": {
        "per_gb_cost_usd": 8.40,  # Residential proxy per GB
    }
}


@dataclass
class Source:
    """A source citation."""
    title: str
    url: str
    date: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None


@dataclass
class CostEstimate:
    """Cost and time estimation for a scrape operation."""
    duration_seconds: float = 0.0
    data_transferred_kb: float = 0.0
    estimated_cost_usd: float = 0.0
    captcha_solved: bool = False
    profile_used: str = ""
    viewport_type: str = ""
    breakdown: dict = field(default_factory=dict)


@dataclass
class ScrapeResult:
    """Result of scraping."""
    query: str
    timestamp: str
    response_text: str
    sources: list[dict]
    source_count: int
    success: bool
    html_content: Optional[str] = None
    error: Optional[str] = None
    connectivity_info: Optional[dict] = None
    cost_estimate: Optional[dict] = None
    profile_info: Optional[dict] = None
    extraction_stats: Optional[dict] = None


class BrightDataBrowserScraper:
    """
    Scraper using Bright Data's Scraping Browser.
    
    Connects to Bright Data's cloud browser via CDP (Chrome DevTools Protocol).
    The cloud browser handles:
    - Automatic CAPTCHA solving
    - Browser fingerprint management
    - Residential IP rotation
    - Anti-bot bypass
    
    Supports viewport profiles for different devices:
    - phone: iphone_14, iphone_15_pro, pixel_7, samsung_s23
    - tablet: ipad_pro_12, ipad_air, galaxy_tab_s8
    - desktop: desktop_1080p, desktop_1440p, macbook_pro_14, macbook_air_13, linux_desktop
    """
    
    def __init__(
        self,
        customer_id: str = None,
        zone: str = None,
        password: str = None,
        country: str = "it",
        scraper_type: str = "google_ai",
        profile: str = "desktop_1080p",  # Device profile name or type (phone/tablet/desktop)
        custom_viewport: dict = None,  # Custom viewport override {"width": int, "height": int}
        scroll_full_page: bool = True,  # Whether to scroll to extract all content
    ):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("playwright is required. Install with: pip install playwright && playwright install")
        
        # Load from environment or use provided values
        self.customer_id = customer_id or os.getenv("BRIGHTDATA_CUSTOMER_ID", "hl_0d78e46f")
        self.zone = zone or os.getenv("BRIGHTDATA_BROWSER_ZONE", "scraping_browser1")
        # Use the Browser API password (different from residential proxy password)
        self.password = password or os.getenv("BRIGHTDATA_BROWSER_PASSWORD", "baguzb7exf2p")
        self.country = country.lower()
        self.scraper_type = scraper_type
        self.scroll_full_page = scroll_full_page
        
        # Resolve profile configuration
        self.profile_name, self.profile_config = self._resolve_profile(profile, custom_viewport)
        
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._playwright = None
        
        # Timing and cost tracking
        self._start_time: float = 0.0
        self._data_transferred_bytes: int = 0
        self._captcha_solved: bool = False
    
    def _resolve_profile(self, profile: str, custom_viewport: dict = None) -> tuple[str, dict]:
        """Resolve profile configuration from name or type."""
        # If custom viewport provided, use it with desktop defaults
        if custom_viewport:
            return "custom", {
                "type": "custom",
                "viewport": custom_viewport,
                "user_agent": VIEWPORT_PROFILES["desktop_1080p"]["user_agent"],
                "device_scale_factor": 1,
                "is_mobile": False,
                "has_touch": False,
            }
        
        # If profile is a device type (phone/tablet/desktop), use default for that type
        if profile in DEFAULT_PROFILES:
            profile = DEFAULT_PROFILES[profile]
        
        # Lookup profile by name
        if profile in VIEWPORT_PROFILES:
            return profile, VIEWPORT_PROFILES[profile].copy()
        
        # Fallback to desktop
        Log.warn(f"Unknown profile '{profile}', using desktop_1080p")
        return "desktop_1080p", VIEWPORT_PROFILES["desktop_1080p"].copy()
    
    @classmethod
    def list_profiles(cls, profile_type: str = None) -> dict:
        """List available viewport profiles, optionally filtered by type."""
        if profile_type:
            return {k: v for k, v in VIEWPORT_PROFILES.items() if v["type"] == profile_type}
        return VIEWPORT_PROFILES.copy()
    
    @property
    def auth(self) -> str:
        """Build authentication string for Bright Data with country targeting."""
        # Add country flag to username for geolocation targeting
        # Format: brd-customer-{id}-zone-{zone}-country-{code}:{password}
        return f"brd-customer-{self.customer_id}-zone-{self.zone}-country-{self.country}:{self.password}"
    
    @property
    def endpoint(self) -> str:
        """WebSocket endpoint for Scraping Browser."""
        return f"wss://{self.auth}@brd.superproxy.io:9222"
    
    async def _verify_browser_location(self, use_cdp: bool = True) -> dict:
        """
        Verify the browser's actual IP and location using JavaScript fetch.
        
        Args:
            use_cdp: If True, use CDP to make request (doesn't affect page state)
        """
        try:
            Log.step("Verifying browser location", "geo")
            
            # Make a simple JavaScript fetch request with timeout
            result = await asyncio.wait_for(
                self._page.evaluate("""
                    async () => {
                        try {
                            const controller = new AbortController();
                            const timeoutId = setTimeout(() => controller.abort(), 8000);
                            
                            const resp = await fetch('https://ipinfo.io/json', {
                                method: 'GET',
                                headers: { 'Accept': 'application/json' },
                                signal: controller.signal
                            });
                            clearTimeout(timeoutId);
                            return await resp.json();
                        } catch (e) {
                            return { error: e.message };
                        }
                    }
                """),
                timeout=15.0
            )
                
            if result and not result.get("error"):
                ip = result.get("ip", "Unknown")
                country = result.get("country", "Unknown")
                city = result.get("city", "Unknown")
                region = result.get("region", "")
                
                print(f"\n{C.GREEN}[Browser Location Verified]{C.RST}")
                print(f"  ├─ IP:       {ip}")
                print(f"  ├─ Country:  {country}")
                print(f"  ├─ City:     {city}")
                print(f"  └─ Region:   {region}")
                
                # Check if country matches expected
                expected = self.country.upper()
                actual = country.upper() if country else "UNKNOWN"
                
                if expected != actual and actual != "UNKNOWN":
                    Log.warn(f"Country mismatch: expected {expected}, got {actual}")
                else:
                    Log.ok(f"Country match: {actual}")
                
                return {
                    "ip": ip,
                    "country": country,
                    "city": city,
                    "region": region,
                    "country_match": expected == actual or actual == "UNKNOWN"
                }
            else:
                Log.warn(f"Geo fetch failed: {result.get('error', 'Unknown') if result else 'No result'}")
                return {"error": result.get("error", "Unknown") if result else "No result"}
            
        except asyncio.TimeoutError:
            Log.warn("Location verification timed out (15s)")
            return {"error": "timeout", "note": "Geo verification timed out, proceeding anyway"}
        except Exception as e:
            Log.warn(f"Location verification failed: {e}")
            return {"error": str(e)}
    
    def _estimate_cost(self, html_size_bytes: int) -> CostEstimate:
        """Estimate cost and provide timing breakdown."""
        duration = time.time() - self._start_time if self._start_time else 0.0
        
        # Calculate data transferred
        data_kb = html_size_bytes / 1024
        data_gb = data_kb / (1024 * 1024)
        
        # Calculate cost
        config = COST_CONFIG["scraping_browser"]
        bandwidth_cost = data_gb * config["per_gb_cost_usd"]
        base_cost = config["base_request_cost_usd"]
        captcha_cost = config["captcha_solve_cost_usd"] if self._captcha_solved else 0.0
        total_cost = bandwidth_cost + base_cost + captcha_cost
        
        return CostEstimate(
            duration_seconds=round(duration, 2),
            data_transferred_kb=round(data_kb, 2),
            estimated_cost_usd=round(total_cost, 6),
            captcha_solved=self._captcha_solved,
            profile_used=self.profile_name,
            viewport_type=self.profile_config.get("type", "unknown"),
            breakdown={
                "bandwidth_cost_usd": round(bandwidth_cost, 6),
                "base_request_cost_usd": base_cost,
                "captcha_cost_usd": captcha_cost,
                "data_gb": round(data_gb, 8),
            }
        )
    
    async def _connect(self):
        """Connect to Bright Data Scraping Browser with profile configuration."""
        self._start_time = time.time()
        
        print(f"\n{C.YELLOW}[Bright Data Connection]{C.RST}")
        print(f"  ├─ Service:  Scraping Browser (Cloud)")
        print(f"  ├─ Zone:     {self.zone}")
        print(f"  ├─ Customer: {self.customer_id}")
        print(f"  ├─ Protocol: CDP over WebSocket")
        print(f"  └─ Endpoint: wss://brd.superproxy.io:9222")
        
        print(f"\n{C.YELLOW}[Device Profile]{C.RST}")
        print(f"  ├─ Name:       {self.profile_name}")
        print(f"  ├─ Type:       {self.profile_config['type']}")
        print(f"  ├─ Viewport:   {self.profile_config['viewport']['width']}x{self.profile_config['viewport']['height']}")
        print(f"  ├─ Scale:      {self.profile_config.get('device_scale_factor', 1)}x")
        print(f"  ├─ Is Mobile:  {self.profile_config.get('is_mobile', False)}")
        print(f"  ├─ Has Touch:  {self.profile_config.get('has_touch', False)}")
        print(f"  └─ User Agent: {self.profile_config['user_agent'][:60]}...")
        
        self._playwright = await async_playwright().start()
        
        try:
            Log.step("Connecting via CDP", "browser")
            self._browser = await self._playwright.chromium.connect_over_cdp(
                self.endpoint,
                timeout=60000
            )
            Log.ok("Connected to Scraping Browser")
            
            # Create new page with viewport configuration
            context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context(
                viewport=self.profile_config["viewport"],
                user_agent=self.profile_config["user_agent"],
                device_scale_factor=self.profile_config.get("device_scale_factor", 1),
                is_mobile=self.profile_config.get("is_mobile", False),
                has_touch=self.profile_config.get("has_touch", False),
            )
            
            self._page = await context.new_page()
            self._page.set_default_timeout(120000)
            
            # Apply viewport to the page explicitly
            await self._page.set_viewport_size(self.profile_config["viewport"])
            
            print(f"\n{C.GREEN}[Connection Established]{C.RST}")
            print(f"  ├─ Country:  {self.country.upper()}")
            print(f"  ├─ Mobile:   {self.profile_config.get('is_mobile', False)}")
            print(f"  └─ Status:   Ready")
            
        except Exception as e:
            Log.fail(f"Connection failed: {e}")
            raise
    
    async def _disconnect(self):
        """Close browser connection."""
        if self._browser:
            Log.step("Closing browser", "browser")
            await self._browser.close()
            Log.ok("Closed")
        if self._playwright:
            await self._playwright.stop()
    
    async def _screenshot(self, name: str = "debug") -> Optional[str]:
        """Take a screenshot."""
        try:
            d = Path(__file__).parent.parent.parent / "data" / "screenshots"
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"sbb_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await self._page.screenshot(path=str(p))
            Log.info(f"Screenshot: {p.name}")
            return str(p)
        except Exception as e:
            Log.warn(f"Screenshot failed: {e}")
            return None
    
    async def _wait_for_captcha(self, timeout: int = 30000):
        """Wait for CAPTCHA to be solved (if present)."""
        try:
            # Use Bright Data's CDP extension for CAPTCHA
            client = await self._page.context.new_cdp_session(self._page)
            result = await client.send("Captcha.waitForSolve", {
                "detectTimeout": timeout
            })
            status = result.get("status", "not_detected")
            if status == "solved":
                Log.ok("CAPTCHA solved automatically")
            return status
        except Exception as e:
            # CAPTCHA detection may not be needed
            Log.info(f"CAPTCHA check: {e}")
            return "not_detected"
    
    async def _handle_cookie_consent(self):
        """Accept cookie consent if shown - supports multiple languages."""
        try:
            # First try JavaScript approach for better reliability
            try:
                clicked = await self._page.evaluate("""
                    () => {
                        // Google consent dialog specific - look for the popup iframe or dialog
                        const frames = document.querySelectorAll('iframe');
                        for (const f of frames) {
                            try {
                                const doc = f.contentDocument || f.contentWindow.document;
                                if (doc) {
                                    const btn = doc.querySelector('button');
                                    if (btn) { btn.click(); return 'iframe'; }
                                }
                            } catch(e) {}
                        }
                        
                        // Look for Google consent dialog by structure
                        // The consent dialog usually has specific structure
                        const dialogs = document.querySelectorAll('div[role="dialog"], div[aria-modal="true"], .consent-bump');
                        for (const dialog of dialogs) {
                            // Find buttons with accept-like text in any language
                            const buttons = dialog.querySelectorAll('button');
                            for (const btn of buttons) {
                                const text = (btn.textContent || '').toLowerCase();
                                // Accept patterns in multiple languages
                                if (text.includes('accept') || text.includes('elfogad') || 
                                    text.includes('accetta') || text.includes('akzept') ||
                                    text.includes('accepter') || text.includes('aceptar') ||
                                    text.includes('összes') || text.includes('all')) {
                                    btn.click();
                                    return 'dialog-' + text.substring(0, 20);
                                }
                            }
                            // If no text match, click the first visible button
                            if (buttons.length > 0) {
                                buttons[0].click();
                                return 'dialog-first';
                            }
                        }
                        
                        // Generic button search
                        const allButtons = document.querySelectorAll('button');
                        for (const btn of allButtons) {
                            const text = (btn.textContent || '').toLowerCase();
                            const rect = btn.getBoundingClientRect();
                            // Must be visible and have accept-like text
                            if (rect.width > 0 && rect.height > 0) {
                                if (text.includes('accept') || text.includes('elfogad') || 
                                    text.includes('accetta') || text.includes('akzept') ||
                                    text.includes('összes elfogadása')) {
                                    btn.click();
                                    return 'button-' + text.substring(0, 20);
                                }
                            }
                        }
                        
                        return false;
                    }
                """)
                if clicked:
                    Log.ok(f"Cookies: {clicked}")
                    await asyncio.sleep(2)
                    return True
            except Exception as e:
                Log.info(f"JS cookie: {e}")
            
            # Fallback to Playwright selectors
            selectors = [
                # Hungarian (seen in screenshot)
                "button:has-text('Az összes elfogadása')",
                "button:has-text('elfogadása')",
                "button:has-text('összes')",
                # English
                "button:has-text('Accept all')",
                "button:has-text('Accept')",
                # Italian
                "button:has-text('Accetta tutto')",
                # German
                "button:has-text('Alle akzeptieren')",
                # French
                "button:has-text('Tout accepter')",
                # Spanish
                "button:has-text('Aceptar todo')",
                # Dutch
                "button:has-text('Alles accepteren')",
                # Swedish
                "button:has-text('Acceptera alla')",
            ]
            
            for selector in selectors:
                try:
                    btn = self._page.locator(selector).first
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                        Log.ok(f"Cookies: {selector[:25]}")
                        await asyncio.sleep(2)
                        return True
                except:
                    continue
                
            return False
        except:
            return False
    
    async def _scroll_to_load_all(self, max_scrolls: int = 10) -> int:
        """Scroll the page to load all dynamic content. Returns total scroll height."""
        if not self.scroll_full_page:
            return 0
            
        Log.step("Scrolling to load all content", "scroll")
        
        try:
            last_height = 0
            scroll_count = 0
            
            for i in range(max_scrolls):
                # Get current scroll height
                current_height = await self._page.evaluate("document.documentElement.scrollHeight")
                
                if current_height == last_height:
                    break
                
                # Scroll to bottom
                await self._page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                await asyncio.sleep(0.5)  # Wait for content to load
                
                last_height = current_height
                scroll_count += 1
            
            # Scroll back to top for consistent extraction
            await self._page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.3)
            
            Log.ok(f"Scrolled {scroll_count} times, height: {last_height}px")
            return last_height
            
        except Exception as e:
            Log.warn(f"Scroll failed: {e}")
            return 0
    
    async def _extract_google_ai_response(self) -> tuple[str, list[Source], dict]:
        """
        Extract FULL response text and ALL sources from Google AI Mode.
        
        Returns:
            tuple: (response_text, sources, extraction_stats)
        """
        response_parts = []
        sources = []
        seen_urls = set()
        seen_texts = set()  # Avoid duplicate text blocks
        
        extraction_stats = {
            "headings_found": 0,
            "paragraphs_found": 0,
            "list_items_found": 0,
            "links_found": 0,
            "links_extracted": 0,
            "scroll_height": 0,
        }
        
        try:
            # Wait for initial content to load
            await asyncio.sleep(3)
            
            # Scroll to load all dynamic content
            extraction_stats["scroll_height"] = await self._scroll_to_load_all()
            
            # Use comprehensive JavaScript extraction - NO LIMITS
            content = await self._page.evaluate("""
                () => {
                    const result = {
                        headings: [],
                        paragraphs: [],
                        listItems: [],
                        links: [],
                        structuredContent: [],  // Preserve document order
                        metadata: {}
                    };
                    
                    // Get main content area
                    const main = document.querySelector('main') || document.body;
                    
                    // Track element positions for ordering
                    const getPosition = (el) => {
                        const rect = el.getBoundingClientRect();
                        return rect.top + window.scrollY;
                    };
                    
                    // Helper to check if text is meaningful
                    const isValidText = (text) => {
                        if (!text || text.length < 5) return false;
                        const lower = text.toLowerCase();
                        // Skip UI elements, sign-in prompts, etc.
                        const skipPatterns = [
                            'sign in', 'sign out', 'login', 'log out',
                            'filter', 'sort by', 'settings', 'more options',
                            'privacy', 'terms', 'google account', 'feedback'
                        ];
                        return !skipPatterns.some(p => lower.includes(p));
                    };
                    
                    // Extract ALL headings (h1-h6)
                    main.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
                        const text = h.innerText?.trim();
                        if (isValidText(text) && text.length < 500) {
                            const level = parseInt(h.tagName[1]);
                            result.headings.push({
                                text: text,
                                level: level,
                                position: getPosition(h)
                            });
                            result.structuredContent.push({
                                type: 'heading',
                                level: level,
                                text: text,
                                position: getPosition(h)
                            });
                        }
                    });
                    
                    // Extract ALL paragraphs and text blocks - NO LENGTH LIMIT
                    main.querySelectorAll('p, div[role="article"], article, [data-hveid], .BNeawe').forEach(el => {
                        // Skip if it's a container with block children
                        if (el.querySelector('p, h1, h2, h3, h4, h5, h6')) return;
                        
                        const text = el.innerText?.trim();
                        if (isValidText(text) && text.length >= 20) {
                            result.paragraphs.push({
                                text: text,
                                position: getPosition(el)
                            });
                            result.structuredContent.push({
                                type: 'paragraph',
                                text: text,
                                position: getPosition(el)
                            });
                        }
                    });
                    
                    // Extract ALL list items - capture full nested lists
                    main.querySelectorAll('ul, ol').forEach(list => {
                        const items = [];
                        list.querySelectorAll(':scope > li').forEach(li => {
                            const text = li.innerText?.trim();
                            if (isValidText(text) && text.length >= 10) {
                                items.push(text);
                                result.listItems.push({
                                    text: text,
                                    position: getPosition(li)
                                });
                            }
                        });
                        if (items.length > 0) {
                            result.structuredContent.push({
                                type: 'list',
                                items: items,
                                position: getPosition(list)
                            });
                        }
                    });
                    
                    // Extract ALL links with full context
                    main.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href;
                        if (!href) return;
                        
                        // Get the anchor text
                        let title = a.innerText?.trim() || '';
                        
                        // Try to get better title from nearby elements
                        if (title.length < 5) {
                            const img = a.querySelector('img');
                            if (img && img.alt) title = img.alt;
                        }
                        
                        // Get surrounding context
                        let context = '';
                        const parent = a.closest('p, li, div, td');
                        if (parent) {
                            context = parent.innerText?.trim().substring(0, 300) || '';
                        }
                        
                        // Skip internal Google links
                        const isExternal = !href.includes('google.com') && 
                                          !href.includes('accounts.google') &&
                                          !href.includes('gstatic.com') &&
                                          !href.startsWith('#') &&
                                          !href.startsWith('javascript:');
                        
                        if (isExternal && (title.length >= 1 || context.length > 20)) {
                            result.links.push({
                                url: href,
                                title: title || '[Link]',
                                context: context,
                                position: getPosition(a)
                            });
                        }
                    });
                    
                    // Get page metadata
                    result.metadata = {
                        title: document.title || '',
                        url: window.location.href,
                        language: document.documentElement.lang || '',
                        totalTextLength: main.innerText?.length || 0
                    };
                    
                    // Sort by position for document order
                    result.structuredContent.sort((a, b) => a.position - b.position);
                    result.links.sort((a, b) => a.position - b.position);
                    
                    return result;
                }
            """)
            
            # Build response text in document order
            for item in content.get('structuredContent', []):
                item_type = item.get('type')
                
                if item_type == 'heading':
                    level = item.get('level', 2)
                    prefix = '#' * level
                    text = item.get('text', '')
                    if text and text not in seen_texts:
                        seen_texts.add(text)
                        response_parts.append(f"{prefix} {text}")
                        extraction_stats["headings_found"] += 1
                
                elif item_type == 'paragraph':
                    text = item.get('text', '')
                    # Deduplicate similar paragraphs
                    if text and text not in seen_texts:
                        # Check for substantial overlap with existing
                        is_duplicate = any(
                            (text in existing or existing in text) 
                            for existing in seen_texts 
                            if len(existing) > 50
                        )
                        if not is_duplicate:
                            seen_texts.add(text)
                            response_parts.append(text)
                            extraction_stats["paragraphs_found"] += 1
                
                elif item_type == 'list':
                    items = item.get('items', [])
                    for li_text in items:
                        if li_text and li_text not in seen_texts:
                            seen_texts.add(li_text)
                            response_parts.append(f"- {li_text}")
                            extraction_stats["list_items_found"] += 1
            
            # Extract ALL sources from links - NO LIMIT
            extraction_stats["links_found"] = len(content.get('links', []))
            
            for link_data in content.get('links', []):
                url = link_data.get('url', '')
                title = link_data.get('title', '')
                context = link_data.get('context', '')
                
                if not url or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                
                # Get publisher from domain
                publisher = None
                try:
                    hostname = urlparse(url).hostname
                    if hostname:
                        publisher = hostname.replace("www.", "").split(".")[0].capitalize()
                except:
                    pass
                
                sources.append(Source(
                    title=title if title and title != '[Link]' else context[:100] if context else url[:50],
                    url=url,
                    publisher=publisher,
                    description=context[:500] if context else None
                ))
                extraction_stats["links_extracted"] += 1
            
            Log.ok(f"Extracted {len(sources)} sources, {len(response_parts)} content blocks")
            Log.data("Stats", f"H:{extraction_stats['headings_found']} P:{extraction_stats['paragraphs_found']} L:{extraction_stats['list_items_found']} Links:{extraction_stats['links_extracted']}")
            
        except Exception as e:
            Log.warn(f"Extraction error: {e}")
        
        return "\n\n".join(response_parts), sources, extraction_stats
    
    async def scrape_google_ai(self, query: str, take_screenshot: bool = False) -> ScrapeResult:
        """
        Scrape Google AI Mode using Scraping Browser.
        
        Supports different viewport profiles (phone, tablet, desktop) and
        extracts FULL content with ALL links and sources.
        
        Screenshots:
        - Only takes FINAL screenshot on success (if take_screenshot=True)
        - Always takes screenshot on ERROR for debugging
        
        Returns ScrapeResult with:
        - Full extracted text
        - All sources with URLs
        - Cost and time estimation
        - Profile information
        - Extraction statistics
        """
        print(f"\n{C.CYAN}{C.BOLD}══════════════════════════════════════════════════════════════════{C.RST}")
        print(f"{C.CYAN}{C.BOLD}           Google AI Scrape (Bright Data Scraping Browser)         {C.RST}")
        print(f"{C.CYAN}{C.BOLD}══════════════════════════════════════════════════════════════════{C.RST}")
        
        # Log query and profile
        print(f"\n{C.YELLOW}[Request]{C.RST}")
        print(f"  ├─ Query:    {query}")
        print(f"  ├─ Profile:  {self.profile_name} ({self.profile_config['type']})")
        print(f"  ├─ Viewport: {self.profile_config['viewport']['width']}x{self.profile_config['viewport']['height']}")
        print(f"  ├─ Mobile:   {self.profile_config.get('is_mobile', False)}")
        print(f"  └─ Target Country: {self.country.upper()}")
        
        timestamp = datetime.now(timezone.utc).isoformat()
        html_content = ""
        extraction_stats = {}
        browser_geo = {}
        
        try:
            await self._connect()
            
            # Build Google AI Mode URL with language hint for target country
            encoded_query = quote_plus(query)
            # Add hl (host language) and gl (geolocation) parameters for correct localization
            lang_map = {
                "it": "it", "fr": "fr", "de": "de", "es": "es", 
                "uk": "en-GB", "nl": "nl", "ch": "de", "se": "sv",
                "us": "en", "pt": "pt", "pl": "pl", "ro": "ro"
            }
            hl = lang_map.get(self.country, "en")
            url = f"https://www.google.com/search?udm=50&q={encoded_query}&hl={hl}&gl={self.country}"
            
            Log.step(f"Loading Google AI Mode", "nav")
            Log.data("URL", f"google.com/search?hl={hl}&gl={self.country}")
            await self._page.goto(url, timeout=120000)
            await asyncio.sleep(3)  # Wait for page to settle
            
            # Verify browser location (uses JS fetch, doesn't navigate)
            browser_geo = await self._verify_browser_location(use_cdp=True)
            
            # Handle cookie consent FIRST (before anything else)
            Log.step("Handling cookie consent", "cookies")
            cookie_handled = await self._handle_cookie_consent()
            if cookie_handled:
                await asyncio.sleep(2)
            
            # No screenshot here - only on final or error
            
            # Wait for and handle CAPTCHA if present
            Log.step("Checking for CAPTCHA", "captcha")
            captcha_status = await self._wait_for_captcha()
            self._captcha_solved = (captcha_status == "solved")
            Log.data("CAPTCHA", captcha_status)
            
            # Check for cookie consent again (sometimes appears after CAPTCHA)
            await self._handle_cookie_consent()
            
            # Wait for AI response to generate
            Log.step("Waiting for AI response", "wait")
            try:
                # Wait for "Thinking" to disappear or content to appear
                await asyncio.sleep(5)
                for _ in range(30):  # Max 30 seconds
                    # Try to dismiss any dialogs
                    await self._handle_cookie_consent()
                    
                    content = await self._page.content()
                    if "Thinking" not in content:
                        break
                    await asyncio.sleep(1)
                Log.ok("Response ready")
            except:
                Log.warn("Response wait timeout")
            
            # No screenshot here - only on final or error
            
            # Get HTML content
            html_content = await self._page.content()
            
            # Check for blocks
            if "unusual traffic" in html_content.lower() or "I'm not a robot" in html_content:
                raise Exception("Blocked by Google despite Scraping Browser")
            
            # Extract content with full text and all links
            Log.step("Extracting FULL content", "extract")
            response_text, sources, extraction_stats = await self._extract_google_ai_response()
            
            # Take FINAL screenshot only on success (if requested)
            if take_screenshot:
                await self._screenshot("google_ai_final")
            
            # Calculate cost estimate
            cost_estimate = self._estimate_cost(len(html_content.encode('utf-8')))
            
            Log.result(True, f"Done - {len(sources)} sources")
            Log.data("Cost", f"${cost_estimate.estimated_cost_usd:.4f} USD")
            Log.data("Duration", f"{cost_estimate.duration_seconds:.1f}s")
            
            return ScrapeResult(
                query=query,
                timestamp=timestamp,
                response_text=response_text,
                sources=[asdict(s) for s in sources],
                source_count=len(sources),
                success=True,
                html_content=html_content,
                connectivity_info={
                    "method": "scraping_browser",
                    "captcha": captcha_status,
                    "target_country": self.country.upper(),
                    "browser_geo": browser_geo,
                    "country_verified": browser_geo.get("country_match", False),
                },
                cost_estimate=asdict(cost_estimate),
                profile_info={
                    "profile_name": self.profile_name,
                    "device_type": self.profile_config.get("type"),
                    "viewport": self.profile_config.get("viewport"),
                    "is_mobile": self.profile_config.get("is_mobile", False),
                    "user_agent": self.profile_config.get("user_agent", "")[:100] + "..."
                },
                extraction_stats=extraction_stats
            )
            
        except Exception as e:
            Log.fail(f"Scrape failed: {e}")
            
            # ALWAYS take screenshot on error for debugging
            if self._page:
                await self._screenshot("google_ai_error")
                try:
                    html_content = await self._page.content()
                except:
                    pass
            
            # Still calculate cost estimate even on failure
            cost_estimate = self._estimate_cost(len(html_content.encode('utf-8')) if html_content else 0)
            
            return ScrapeResult(
                query=query,
                timestamp=timestamp,
                response_text="",
                sources=[],
                source_count=0,
                success=False,
                error=str(e),
                html_content=html_content,
                connectivity_info={
                    "method": "scraping_browser",
                    "target_country": self.country.upper(),
                    "browser_geo": browser_geo if browser_geo else {},
                    "error": str(e),
                },
                cost_estimate=asdict(cost_estimate),
                profile_info={
                    "profile_name": self.profile_name,
                    "device_type": self.profile_config.get("type"),
                    "viewport": self.profile_config.get("viewport"),
                }
            )
        
        finally:
            await self._disconnect()
    
    async def scrape_chatgpt(self, query: str, take_screenshot: bool = False) -> ScrapeResult:
        """
        Scrape ChatGPT using Bright Data Scraping Browser.
        
        Uses chatgpt.com (not chat.openai.com) for instant access without login.
        The Scraping Browser handles CAPTCHAs and anti-bot detection automatically.
        
        Key features:
        - Uses mobile user agent for better instant access
        - Handles cookie consent and login prompts
        - Waits for streaming response to complete
        - Extracts full response text
        
        Screenshots:
        - Only takes FINAL screenshot on success (if take_screenshot=True)
        - Always takes screenshot on ERROR for debugging
        
        Returns ScrapeResult with full response.
        """
        print(f"\n{C.CYAN}{C.BOLD}══════════════════════════════════════════════════════════════════{C.RST}")
        print(f"{C.CYAN}{C.BOLD}           ChatGPT Scrape (Bright Data Scraping Browser)           {C.RST}")
        print(f"{C.CYAN}{C.BOLD}══════════════════════════════════════════════════════════════════{C.RST}")
        
        # Log query and profile
        print(f"\n{C.YELLOW}[Request]{C.RST}")
        print(f"  ├─ Query:    {query[:60]}{'...' if len(query) > 60 else ''}")
        print(f"  ├─ Profile:  {self.profile_name} ({self.profile_config['type']})")
        print(f"  ├─ Viewport: {self.profile_config['viewport']['width']}x{self.profile_config['viewport']['height']}")
        print(f"  ├─ Mobile:   {self.profile_config.get('is_mobile', False)}")
        print(f"  └─ Target Country: {self.country.upper()}")
        
        timestamp = datetime.now(timezone.utc).isoformat()
        html_content = ""
        browser_geo = {}
        captcha_status = "not_detected"
        
        try:
            await self._connect()
            
            # Navigate to ChatGPT (use chatgpt.com for instant access)
            Log.step("Loading ChatGPT", "nav")
            Log.data("URL", "chatgpt.com")
            # Use domcontentloaded instead of networkidle - ChatGPT has constant WebSocket activity
            await self._page.goto("https://chatgpt.com", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Wait for page to settle
            
            # Verify browser location
            browser_geo = await self._verify_browser_location(use_cdp=True)
            
            # Wait for and handle CAPTCHA if present
            Log.step("Checking for CAPTCHA", "captcha")
            captcha_status = await self._wait_for_captcha()
            self._captcha_solved = (captcha_status == "solved")
            Log.data("CAPTCHA", captcha_status)
            
            # Handle cookie consent
            Log.step("Handling cookie consent", "cookies")
            await self._handle_chatgpt_consent()
            
            # Handle login prompts
            Log.step("Checking for login prompts", "auth")
            await self._handle_chatgpt_login_prompt()
            
            await asyncio.sleep(2)
            
            # Check if we have instant access (prompt textarea visible)
            Log.step("Checking instant access", "access")
            has_input = await self._page.evaluate(
                'document.querySelector("#prompt-textarea") !== null'
            )
            
            if not has_input:
                # Try handling cookie consent again (might have appeared late)
                Log.step("Retrying consent/popup handling", "cookies")
                await self._handle_chatgpt_consent()
                await asyncio.sleep(1)
                await self._handle_chatgpt_login_prompt()
                await asyncio.sleep(2)
                
                has_input = await self._page.evaluate(
                    'document.querySelector("#prompt-textarea") !== null || document.querySelector("textarea") !== null'
                )
            
            # One more retry if still no input
            if not has_input:
                Log.step("Final consent retry", "cookies")
                await self._handle_chatgpt_consent()
                await asyncio.sleep(2)
                
                has_input = await self._page.evaluate(
                    'document.querySelector("#prompt-textarea") !== null || document.querySelector("textarea") !== null'
                )
            
            if has_input:
                Log.ok("Instant access available")
            else:
                # Check page content for login indicators
                page_content = await self._page.content()
                if any(ind in page_content for ind in ["Sign up", "Log in", "Create a free account"]):
                    await self._screenshot("chatgpt_needs_auth")
                    raise Exception("ChatGPT requires login - instant access not available from this IP/region")
            
            # Handle any remaining popups before finding input
            await self._handle_chatgpt_consent()
            await asyncio.sleep(1)
            
            # Find and fill the input
            Log.step("Finding chat input", "input")
            self._current_query = query  # Store for detection later
            input_found = await self._find_chatgpt_input(query)
            
            if not input_found:
                await self._screenshot("chatgpt_no_input")
                raise Exception("Could not find chat input - page structure may have changed")
            
            # Dismiss the "By messaging ChatGPT" popup if present (before submission)
            Log.step("Dismissing popups", "popup")
            await self._dismiss_chatgpt_popup()
            await asyncio.sleep(0.5)
            
            # Submit the query
            Log.step("Submitting query", "submit")
            await self._submit_chatgpt_query()
            
            # Wait for response (with increased timeout for slow responses)
            Log.step("Waiting for response", "wait")
            response_text = await self._wait_for_chatgpt_response(query=query, timeout=120)
            
            # Get HTML content
            html_content = await self._page.content()
            
            # Take FINAL screenshot only on success
            if take_screenshot:
                await self._screenshot("chatgpt_final")
            
            # Calculate cost estimate
            cost_estimate = self._estimate_cost(len(html_content.encode('utf-8')))
            
            success = bool(response_text)
            Log.result(success, f"Done - {len(response_text)} chars")
            Log.data("Cost", f"${cost_estimate.estimated_cost_usd:.4f} USD")
            Log.data("Duration", f"{cost_estimate.duration_seconds:.1f}s")
            
            return ScrapeResult(
                query=query,
                timestamp=timestamp,
                response_text=response_text,
                sources=[],  # ChatGPT doesn't provide source links
                source_count=0,
                success=success,
                html_content=html_content,
                connectivity_info={
                    "method": "scraping_browser",
                    "captcha": captcha_status,
                    "target_country": self.country.upper(),
                    "browser_geo": browser_geo,
                    "country_verified": browser_geo.get("country_match", False),
                    "instant_access": True,
                    "url": "https://chatgpt.com",
                },
                cost_estimate=asdict(cost_estimate),
                profile_info={
                    "profile_name": self.profile_name,
                    "device_type": self.profile_config.get("type"),
                    "viewport": self.profile_config.get("viewport"),
                    "is_mobile": self.profile_config.get("is_mobile", False),
                    "user_agent": self.profile_config.get("user_agent", "")[:100] + "..."
                },
            )
            
        except Exception as e:
            Log.fail(f"Scrape failed: {e}")
            
            # ALWAYS take screenshot on error
            if self._page:
                await self._screenshot("chatgpt_error")
                try:
                    html_content = await self._page.content()
                except:
                    pass
            
            cost_estimate = self._estimate_cost(len(html_content.encode('utf-8')) if html_content else 0)
            
            return ScrapeResult(
                query=query,
                timestamp=timestamp,
                response_text="",
                sources=[],
                source_count=0,
                success=False,
                error=str(e),
                html_content=html_content,
                connectivity_info={
                    "method": "scraping_browser",
                    "target_country": self.country.upper(),
                    "browser_geo": browser_geo if browser_geo else {},
                    "error": str(e),
                    "url": "https://chatgpt.com",
                },
                cost_estimate=asdict(cost_estimate),
                profile_info={
                    "profile_name": self.profile_name,
                    "device_type": self.profile_config.get("type"),
                    "viewport": self.profile_config.get("viewport"),
                }
            )
        
        finally:
            await self._disconnect()
    
    async def _dismiss_chatgpt_popup(self):
        """
        Dismiss the 'By messaging ChatGPT...' popup and any other overlays.
        This popup appears at the bottom of the screen on mobile/desktop.
        """
        try:
            dismissed = await self._page.evaluate("""
                () => {
                    let dismissed = [];
                    
                    // Look for the "By messaging ChatGPT" terms popup (has X close button)
                    // The popup contains text about terms and privacy policy
                    const termsPopupTexts = [
                        'by messaging chatgpt',
                        'agree to our terms',
                        'privacy policy',
                        'don\\'t share sensitive info',
                        'chats may be reviewed',
                        'messaggiando chatgpt',  // Italian
                        'en envoyant un message',  // French
                        'durch das senden',  // German
                        'al enviar un mensaje',  // Spanish
                    ];
                    
                    // Find all potential popup containers
                    const allElements = document.querySelectorAll('div, aside, section');
                    for (const el of allElements) {
                        const text = (el.textContent || '').toLowerCase();
                        const rect = el.getBoundingClientRect();
                        
                        // Skip tiny or invisible elements
                        if (rect.width < 100 || rect.height < 50) continue;
                        
                        // Check if this looks like the terms popup
                        const isTermsPopup = termsPopupTexts.some(t => text.includes(t));
                        if (isTermsPopup) {
                            // Look for X/close button within this element
                            const closeBtn = el.querySelector('button[aria-label*="close"], button[aria-label*="Close"], button:has(svg)');
                            if (closeBtn) {
                                const btnRect = closeBtn.getBoundingClientRect();
                                if (btnRect.width > 0 && btnRect.height > 0) {
                                    closeBtn.click();
                                    dismissed.push('terms popup X');
                                    continue;
                                }
                            }
                            
                            // Try clicking an X that might be nearby
                            const allButtons = el.querySelectorAll('button');
                            for (const btn of allButtons) {
                                const btnText = (btn.textContent || '').trim();
                                if (btnText === '×' || btnText === 'x' || btnText === 'X') {
                                    btn.click();
                                    dismissed.push('terms popup X text');
                                    break;
                                }
                                // Check for SVG close icon
                                if (btn.querySelector('svg') && !btn.textContent.trim()) {
                                    const btnRect = btn.getBoundingClientRect();
                                    if (btnRect.width < 50 && btnRect.height < 50) {
                                        btn.click();
                                        dismissed.push('terms popup SVG close');
                                        break;
                                    }
                                }
                            }
                        }
                    }
                    
                    // Also look for standalone close buttons
                    const standaloneClose = document.querySelectorAll('button[aria-label="Close"], button[aria-label="Dismiss"]');
                    for (const btn of standaloneClose) {
                        const rect = btn.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            btn.click();
                            dismissed.push('standalone close');
                        }
                    }
                    
                    return dismissed.length > 0 ? dismissed.join(', ') : false;
                }
            """)
            
            if dismissed:
                Log.ok(f"Popup dismissed: {dismissed}")
                await asyncio.sleep(1)
                return True
            return False
        except Exception as e:
            Log.warn(f"Popup dismiss error: {e}")
            return False
    
    async def _handle_chatgpt_consent(self):
        """Handle ChatGPT cookie consent and initial dialogs in multiple languages."""
        try:
            # Try JavaScript approach first - more reliable for ChatGPT's cookie dialog
            clicked = await self._page.evaluate("""
                () => {
                    // Look for the specific "We use cookies" dialog
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        const text = (btn.textContent || '').toLowerCase().trim();
                        const rect = btn.getBoundingClientRect();
                        
                        // Skip invisible buttons
                        if (rect.width === 0 || rect.height === 0) continue;
                        
                        // Accept patterns - exact matches first
                        if (text === 'accept all' || text === 'accept' || 
                            text === 'accetta tutto' || text === 'accetta' ||
                            text === 'alle akzeptieren' || text === 'tout accepter' ||
                            text === 'aceptar todo' || text === 'allow' || 
                            text === 'ok' || text === 'agree' || text === 'got it') {
                            btn.click();
                            return 'exact: ' + text;
                        }
                        
                        // Partial matches
                        if (text.includes('accept all') || text.includes('accept cookies') ||
                            text.includes('accetta') || text.includes('akzept')) {
                            btn.click();
                            return 'partial: ' + text;
                        }
                    }
                    
                    // Also try X/close button on dialogs
                    const closeSelectors = [
                        'div[role="dialog"] button[aria-label="Close"]',
                        'div[role="dialog"] button[aria-label="close"]',
                        'div[role="dialog"] button:has(svg)',
                        'button[aria-label="Close"]',
                        'button[aria-label="close"]'
                    ];
                    for (const sel of closeSelectors) {
                        const closeBtn = document.querySelector(sel);
                        if (closeBtn) {
                            const rect = closeBtn.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                closeBtn.click();
                                return 'close button';
                            }
                        }
                    }
                    
                    return false;
                }
            """)
            
            if clicked:
                Log.ok(f"Consent: {clicked}")
                await asyncio.sleep(2)
                return True
            
            # Fallback to Playwright locators
            consent_selectors = [
                # English
                "button:has-text('Accept all')",
                "button:has-text('Accept')",
                "button:has-text('Allow')",
                "button:has-text('OK')",
                # Italian
                "button:has-text('Accetta tutto')",
                "button:has-text('Accetta')",
                # German
                "button:has-text('Alle akzeptieren')",
                # French
                "button:has-text('Tout accepter')",
                # Spanish
                "button:has-text('Aceptar todo')",
                # Close buttons
                "div[role='dialog'] button[aria-label='Close']",
                "button[aria-label='Close']",
                # Other
                "button[data-testid='cookie-banner-accept']",
            ]
            
            for selector in consent_selectors:
                try:
                    btn = self._page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        Log.ok(f"Consent: {selector[:30]}")
                        await asyncio.sleep(2)
                        return True
                except:
                    continue
                
            return False
        except:
            return False
    
    async def _handle_chatgpt_login_prompt(self):
        """Dismiss login prompts, terms popups, and continue without auth (instant access)."""
        try:
            # Try JavaScript approach to dismiss any overlays
            dismissed = await self._page.evaluate("""
                () => {
                    // Find and click any X/close buttons on popups
                    const closeButtons = document.querySelectorAll('button');
                    for (const btn of closeButtons) {
                        const rect = btn.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0) continue;
                        
                        // Check for X icon (SVG close button)
                        const svg = btn.querySelector('svg');
                        const ariaLabel = btn.getAttribute('aria-label') || '';
                        const text = (btn.textContent || '').toLowerCase().trim();
                        
                        // Close/dismiss patterns
                        if (ariaLabel.toLowerCase().includes('close') || 
                            ariaLabel.toLowerCase().includes('dismiss') ||
                            text === 'x' || text === '×' ||
                            text.includes('stay logged out') ||
                            text.includes('not now') ||
                            text.includes('skip') ||
                            text.includes('maybe later')) {
                            btn.click();
                            return 'clicked: ' + (ariaLabel || text || 'close button');
                        }
                    }
                    
                    // Also try to dismiss any modal/dialog overlays
                    const overlays = document.querySelectorAll('[role="dialog"], [aria-modal="true"]');
                    for (const overlay of overlays) {
                        const closeBtn = overlay.querySelector('button[aria-label*="close"], button[aria-label*="Close"]');
                        if (closeBtn) {
                            closeBtn.click();
                            return 'clicked: dialog close';
                        }
                    }
                    
                    return false;
                }
            """)
            
            if dismissed:
                Log.ok(f"Dismissed: {dismissed}")
                await asyncio.sleep(1)
                return True
            
            # Fallback to Playwright locators
            dismiss_selectors = [
                "button:has-text('Stay logged out')",
                "button:has-text('Continue')",
                "button:has-text('Skip')",
                "button:has-text('Not now')",
                "button:has-text('Maybe later')",
                "button:has-text('Try it first')",
                "button[aria-label='Close']",
                "button[aria-label='close']",
                "button[aria-label='Dismiss']",
            ]
            
            for selector in dismiss_selectors:
                try:
                    btn = self._page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        Log.ok(f"Dismissed: {selector[:25]}")
                        await asyncio.sleep(1)
                        return True
                except:
                    continue
            return False
        except:
            return False
    
    async def _find_chatgpt_input(self, query: str) -> bool:
        """
        Find and fill the ChatGPT input field.
        
        Uses multiple strategies:
        1. Keyboard typing (most reliable for React inputs)
        2. Playwright type() method
        3. JavaScript with native setter for fallback
        """
        try:
            # Wait a bit for page to fully load and dismiss any remaining popups
            await asyncio.sleep(2)
            
            # First, dismiss any remaining overlays that might block input
            await self._page.evaluate("""
                () => {
                    // Click any X buttons on overlays
                    const closeButtons = document.querySelectorAll('button[aria-label*="close"], button[aria-label*="Close"], button[aria-label*="dismiss"]');
                    closeButtons.forEach(btn => {
                        const rect = btn.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) btn.click();
                    });
                }
            """)
            await asyncio.sleep(1)
            
            # Strategy 1: Try #prompt-textarea with keyboard typing (most reliable)
            try:
                textarea = self._page.locator('#prompt-textarea').first
                if await textarea.is_visible(timeout=5000):
                    # Click to focus
                    await textarea.click()
                    await asyncio.sleep(0.5)
                    
                    # Use type() instead of fill() - types character by character
                    # This is more reliable for React controlled inputs and contenteditable
                    await textarea.type(query, delay=30)  # 30ms delay between keys
                    await asyncio.sleep(0.5)
                    
                    # Verify the text was entered - handle both textarea and contenteditable
                    try:
                        # Try input_value first (for textarea)
                        value = await textarea.input_value()
                    except:
                        # Fallback for contenteditable div
                        value = await textarea.evaluate('el => el.innerText || el.textContent || ""')
                    
                    if value and len(value.strip()) >= len(query) - 5:  # Allow small tolerance
                        Log.ok(f"Input found: #prompt-textarea ({len(value.strip())} chars)")
                        return True
                    else:
                        Log.warn(f"Text verification: got {len(value) if value else 0} chars, expected ~{len(query)}")
            except Exception as e:
                Log.warn(f"Playwright type failed: {e}")
            
            # Strategy 2: Try with press_sequentially (keyboard simulation)
            try:
                textarea = self._page.locator('#prompt-textarea').first
                if await textarea.is_visible(timeout=3000):
                    await textarea.click()
                    await asyncio.sleep(0.3)
                    
                    # Clear first using keyboard
                    await self._page.keyboard.press("Control+a")
                    await asyncio.sleep(0.1)
                    await self._page.keyboard.press("Backspace")
                    await asyncio.sleep(0.2)
                    
                    # Type using keyboard
                    await self._page.keyboard.type(query, delay=25)
                    await asyncio.sleep(0.5)
                    
                    # Verify - handle both textarea and contenteditable
                    try:
                        value = await textarea.input_value()
                    except:
                        value = await textarea.evaluate('el => el.innerText || el.textContent || ""')
                    
                    if value and len(value.strip()) >= len(query) - 5:
                        Log.ok(f"Input found: keyboard typing ({len(value.strip())} chars)")
                        return True
            except Exception as e:
                Log.warn(f"Keyboard typing failed: {e}")
            
            # Strategy 3: Try JavaScript with native setter (for React controlled inputs)
            filled_js = await self._page.evaluate("""
                (query) => {
                    const ta = document.querySelector('#prompt-textarea') || document.querySelector('textarea');
                    if (ta) {
                        // Focus the element
                        ta.focus();
                        ta.click();
                        
                        // Use native setter for React controlled inputs
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLTextAreaElement.prototype, 'value'
                        ).set;
                        
                        // Clear first
                        nativeInputValueSetter.call(ta, '');
                        ta.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                        
                        // Set the new value
                        nativeInputValueSetter.call(ta, query);
                        
                        // Dispatch events that React listens to
                        ta.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                        ta.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                        
                        // Also trigger React's synthetic events
                        const reactKey = Object.keys(ta).find(k => k.startsWith('__reactProps$'));
                        if (reactKey && ta[reactKey] && ta[reactKey].onChange) {
                            ta[reactKey].onChange({ target: ta });
                        }
                        
                        return { filled: true, length: ta.value.length, actual: ta.value.substring(0, 50) };
                    }
                    return { filled: false };
                }
            """, query)
            
            if filled_js and filled_js.get('filled') and filled_js.get('length', 0) >= len(query) - 5:
                Log.ok(f"Input found: JS native setter ({filled_js.get('length', 0)} chars)")
                return True
            
            # Strategy 4: Playwright locators for various input patterns
            input_selectors = [
                "#prompt-textarea",
                "textarea[placeholder*='Message']",
                "textarea[placeholder*='message']",
                "textarea[placeholder*='Send a message']",
                "textarea[data-id='root']",
                "div[contenteditable='true'][data-placeholder]",
                "div.ProseMirror[contenteditable='true']",
                "div[contenteditable='true']",
                "textarea",
            ]
            
            for selector in input_selectors:
                try:
                    element = self._page.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        await element.click()
                        await asyncio.sleep(0.5)
                        
                        # Try fill first
                        try:
                            await element.fill(query)
                        except:
                            # Fallback to type
                            await element.type(query, delay=30)
                        
                        Log.ok(f"Input found: {selector[:30]}")
                        return True
                except:
                    continue
            
            # Strategy 3: Full JavaScript fallback
            filled = await self._page.evaluate("""
                (query) => {
                    // Try any textarea
                    let ta = document.querySelector('textarea');
                    if (ta) {
                        ta.focus();
                        ta.value = query;
                        ta.dispatchEvent(new Event('input', { bubbles: true }));
                        return 'textarea';
                    }
                    
                    // Try contenteditable divs
                    const ce = document.querySelector('div[contenteditable="true"]');
                    if (ce) {
                        ce.focus();
                        ce.textContent = query;
                        ce.dispatchEvent(new Event('input', { bubbles: true }));
                        return 'contenteditable';
                    }
                    
                    return false;
                }
            """, query)
            
            if filled:
                Log.ok(f"Input found (JS: {filled})")
                return True
            
            return False
            
        except Exception as e:
            Log.warn(f"Input find error: {e}")
            return False
    
    async def _submit_chatgpt_query(self):
        """
        Submit the ChatGPT query.
        
        Tries multiple send button selectors:
        1. fruitjuice-send-button (newer UI)
        2. send-button (standard)
        3. Enter key (fallback)
        """
        try:
            # Try fruitjuice-send-button first (newer UI)
            try:
                has_fruitjuice = await self._page.evaluate(
                    'document.querySelector(\'[data-testid="fruitjuice-send-button"]\') !== null'
                )
                if has_fruitjuice:
                    await self._page.click('[data-testid="fruitjuice-send-button"]')
                    Log.ok("Query submitted (fruitjuice-send-button)")
                    return True
            except:
                pass
            
            # Try standard send-button
            try:
                has_send = await self._page.evaluate(
                    'document.querySelector(\'[data-testid="send-button"]\') !== null'
                )
                if has_send:
                    await self._page.click('[data-testid="send-button"]')
                    Log.ok("Query submitted (send-button)")
                    return True
            except:
                pass
            
            # Try Playwright locators
            send_selectors = [
                "button[data-testid='send-button']",
                "button[data-testid='fruitjuice-send-button']",
                "button[aria-label='Send message']",
                "button:has-text('Send')",
            ]
            
            for selector in send_selectors:
                try:
                    btn = self._page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        Log.ok(f"Query submitted ({selector[:30]})")
                        return True
                except:
                    continue
            
            # Fallback: press Enter
            await self._page.keyboard.press("Enter")
            Log.ok("Query submitted (Enter)")
            return True
            
        except Exception as e:
            Log.warn(f"Submit error: {e}")
            # Try Enter as last resort
            await self._page.keyboard.press("Enter")
            return True
    
    async def _wait_for_chatgpt_response(self, query: str, timeout: int = 90) -> str:
        """
        Wait for ChatGPT response to complete and extract it.
        
        Args:
            query: The query we sent (used to match user message)
            timeout: Maximum seconds to wait
        
        Detection strategy:
        1. Wait for user message to appear (confirming our query was submitted)
        2. Wait for new assistant message to appear after user message
        3. Watch for streaming indicator (.result-streaming) to disappear
        4. Watch for thinking indicator (.result-thinking) to disappear
        5. Verify text stability (no changes for 1 second)
        """
        try:
            # Get initial counts and identify which messages exist
            initial_state = await self._page.evaluate("""
                () => {
                    const userMsgs = document.querySelectorAll('div[data-message-author-role="user"]');
                    const assistantMsgs = document.querySelectorAll('div[data-message-author-role="assistant"]');
                    
                    // Get the last user message text (if any) to detect new message
                    let lastUserText = '';
                    if (userMsgs.length > 0) {
                        lastUserText = userMsgs[userMsgs.length - 1].innerText || '';
                    }
                    
                    return {
                        userCount: userMsgs.length,
                        assistantCount: assistantMsgs.length,
                        lastUserText: lastUserText.substring(0, 200)
                    };
                }
            """)
            
            initial_user_count = initial_state.get('userCount', 0)
            initial_assistant_count = initial_state.get('assistantCount', 0)
            initial_last_user_text = initial_state.get('lastUserText', '')
            
            Log.data("Initial state", f"user:{initial_user_count} assistant:{initial_assistant_count}")
            
            # Wait for OUR user message to appear (confirms query was sent)
            # Check both count increase AND text match
            start_time = asyncio.get_event_loop().time()
            user_message_appeared = False
            query = getattr(self, '_current_query', '')  # Get query from instance
            our_query_short = query[:50] if query else ''  # First 50 chars for matching
            
            while (asyncio.get_event_loop().time() - start_time) < 30:  # 30s for user message
                current_state = await self._page.evaluate("""
                    (queryMatch) => {
                        const userMsgs = document.querySelectorAll('div[data-message-author-role="user"]');
                        let foundOurMsg = false;
                        let lastUserText = '';
                        
                        if (userMsgs.length > 0) {
                            lastUserText = userMsgs[userMsgs.length - 1].innerText || '';
                            // Check if our query appears in any user message
                            for (const msg of userMsgs) {
                                if ((msg.innerText || '').includes(queryMatch)) {
                                    foundOurMsg = true;
                                    break;
                                }
                            }
                        }
                        
                        return {
                            count: userMsgs.length,
                            foundOurMsg: foundOurMsg,
                            lastUserText: lastUserText.substring(0, 100)
                        };
                    }
                """, our_query_short)
                
                current_count = current_state.get('count', 0)
                found_our_msg = current_state.get('foundOurMsg', False)
                
                if found_our_msg or (current_count > initial_user_count and our_query_short in current_state.get('lastUserText', '')):
                    user_message_appeared = True
                    Log.ok(f"User message sent ({current_count} user messages)")
                    break
                
                await asyncio.sleep(0.3)
            
            if not user_message_appeared:
                Log.warn("User message not detected - query may not have been sent")
            
            # Now wait for assistant response (after our user message)
            # The key is to wait for a REAL response, not just a greeting
            new_message_appeared = False
            greeting_patterns = ['hey', "what's up", 'how can i help', 'hello', 'hi there', 'i\'m here', 'what can i help']
            
            # Give more time for the response to start generating
            Log.data("Waiting for response to start", "5s")
            await asyncio.sleep(5)
            
            # Dismiss any popups that appeared during initial wait
            await self._dismiss_chatgpt_popup()
            
            loop_count = 0
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                current_state = await self._page.evaluate("""
                    (queryMatch) => {
                        const assistantMsgs = document.querySelectorAll('div[data-message-author-role="assistant"]');
                        const userMsgs = document.querySelectorAll('div[data-message-author-role="user"]');
                        
                        // Get all message texts in order
                        const allMsgs = [];
                        const container = document.querySelector('main') || document.body;
                        container.querySelectorAll('div[data-message-author-role]').forEach((msg, idx) => {
                            allMsgs.push({
                                role: msg.getAttribute('data-message-author-role'),
                                text: msg.innerText || '',
                                index: idx
                            });
                        });
                        
                        // Find the user message that contains our query
                        let ourUserMsgIdx = -1;
                        for (let i = allMsgs.length - 1; i >= 0; i--) {
                            if (allMsgs[i].role === 'user' && allMsgs[i].text.includes(queryMatch)) {
                                ourUserMsgIdx = i;
                                break;
                            }
                        }
                        
                        // Fall back to last user message if not found
                        if (ourUserMsgIdx === -1) {
                            for (let i = allMsgs.length - 1; i >= 0; i--) {
                                if (allMsgs[i].role === 'user') {
                                    ourUserMsgIdx = i;
                                    break;
                                }
                            }
                        }
                        
                        // Get assistant message AFTER our user message
                        let responseText = '';
                        let hasStreaming = false;
                        let hasThinking = false;
                        let isGenerating = false;
                        
                        for (let i = ourUserMsgIdx + 1; i < allMsgs.length; i++) {
                            if (allMsgs[i].role === 'assistant') {
                                responseText = allMsgs[i].text;
                                break;
                            }
                        }
                        
                        // Check for various loading indicators
                        // Look for the "stop" button which appears during generation
                        const stopBtn = document.querySelector('button[aria-label*="Stop"]');
                        isGenerating = stopBtn !== null;
                        
                        // Check for streaming/thinking indicators in any assistant message
                        const loadingDot = document.querySelector('.animate-pulse, [class*="typing"], [class*="loading"]');
                        
                        if (assistantMsgs.length > 0) {
                            const lastAssistant = assistantMsgs[assistantMsgs.length - 1];
                            hasStreaming = lastAssistant.querySelector('.result-streaming') !== null;
                            hasThinking = lastAssistant.querySelector('.result-thinking') !== null;
                        }
                        
                        return {
                            assistantCount: assistantMsgs.length,
                            userCount: userMsgs.length,
                            responseText: responseText,
                            hasStreaming: hasStreaming,
                            hasThinking: hasThinking,
                            isGenerating: isGenerating,
                            hasLoadingIndicator: loadingDot !== null,
                            ourUserMsgIdx: ourUserMsgIdx,
                            totalMsgs: allMsgs.length
                        };
                    }
                """, our_query_short)
                
                current_count = current_state.get('assistantCount', 0)
                response_text = current_state.get('responseText', '')
                has_streaming = current_state.get('hasStreaming', False)
                has_thinking = current_state.get('hasThinking', False)
                is_generating = current_state.get('isGenerating', False)
                has_loading = current_state.get('hasLoadingIndicator', False)
                our_msg_idx = current_state.get('ourUserMsgIdx', -1)
                
                # Check if we have a real response (not just a greeting)
                is_greeting = any(p in response_text.lower() for p in greeting_patterns) and len(response_text) < 100
                
                # Still generating - wait
                if is_generating or has_streaming or has_thinking or has_loading:
                    if len(response_text) > 0:
                        Log.data("Generating", f"{len(response_text)} chars...")
                    await asyncio.sleep(1)
                    continue
                
                # Check if we have a real response after OUR message
                if our_msg_idx >= 0 and response_text and not is_greeting:
                    new_message_appeared = True
                    Log.ok(f"Response detected ({len(response_text)} chars)")
                    break
                elif current_count > initial_assistant_count and response_text and not is_greeting:
                    # Fallback check
                    new_message_appeared = True
                    Log.ok(f"New response detected ({current_count} assistant messages, {len(response_text)} chars)")
                    break
                elif is_greeting:
                    # We have a message but it's a greeting, keep waiting
                    pass
                
                await asyncio.sleep(0.5)
            
            if not new_message_appeared:
                # If we timed out but have a response, use it
                if response_text:
                    Log.warn(f"Timeout but have response: {len(response_text)} chars")
                    new_message_appeared = True
                else:
                    # Try one more extraction attempt - maybe the content is there
                    final_check = await self._page.evaluate("""
                        () => {
                            const assistantMsgs = document.querySelectorAll('[data-message-author-role="assistant"]');
                            if (assistantMsgs.length > 0) {
                                const last = assistantMsgs[assistantMsgs.length - 1];
                                const text = last.innerText || '';
                                // Only return if we have actual content (not loading dots)
                                if (text.length > 5 && !text.match(/^[●•.\\s]+$/)) {
                                    return text;
                                }
                            }
                            
                            // Also check for prose/markdown content
                            const prose = document.querySelectorAll('.markdown, .prose');
                            if (prose.length > 0) {
                                const text = prose[prose.length - 1].innerText || '';
                                if (text.length > 5) return text;
                            }
                            
                            return '';
                        }
                    """)
                    
                    if final_check and len(final_check) > 5:
                        Log.warn(f"Found response in final check: {len(final_check)} chars")
                        return final_check
                    
                    Log.warn("No assistant response found within timeout")
                    return ""
            
            # Wait for response to complete (streaming indicator disappears)
            previous_text = ""
            stable_count = 0
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                # Check for streaming/thinking indicators
                status = await self._page.evaluate("""
                    () => {
                        const messages = document.querySelectorAll('div[data-message-author-role="assistant"]');
                        if (messages.length === 0) return { streaming: false, thinking: false, text: '' };
                        
                        const last = messages[messages.length - 1];
                        return {
                            streaming: last.querySelector('.result-streaming') !== null,
                            thinking: last.querySelector('.result-thinking') !== null,
                            text: last.innerText || ''
                        };
                    }
                """)
                
                is_streaming = status.get('streaming', False)
                is_thinking = status.get('thinking', False)
                current_text = status.get('text', '')
                
                # Log progress occasionally
                if len(current_text) > 0 and len(current_text) % 500 < 50:
                    Log.data("Progress", f"{len(current_text)} chars, streaming={is_streaming}")
                
                # Check if done
                if not is_streaming and not is_thinking:
                    if current_text == previous_text:
                        stable_count += 1
                        if stable_count >= 4:  # Text stable for 2 seconds
                            break
                    else:
                        stable_count = 0
                    previous_text = current_text
                else:
                    stable_count = 0
                    previous_text = current_text
                
                await asyncio.sleep(0.5)
            
            # Give a bit more time for final render
            await asyncio.sleep(1)
            
            # Extract final response - get the assistant message AFTER the last user message
            response = await self._page.evaluate("""
                () => {
                    const container = document.querySelector('main') || document.body;
                    const allMsgs = container.querySelectorAll('div[data-message-author-role]');
                    
                    // Convert to array and find indices
                    const msgArray = Array.from(allMsgs);
                    
                    // Find the last user message index
                    let lastUserIdx = -1;
                    for (let i = msgArray.length - 1; i >= 0; i--) {
                        if (msgArray[i].getAttribute('data-message-author-role') === 'user') {
                            lastUserIdx = i;
                            break;
                        }
                    }
                    
                    // Get assistant message AFTER the last user message
                    for (let i = lastUserIdx + 1; i < msgArray.length; i++) {
                        if (msgArray[i].getAttribute('data-message-author-role') === 'assistant') {
                            return msgArray[i].innerText || '';
                        }
                    }
                    
                    // Fallback: get the last assistant message
                    const assistantMsgs = document.querySelectorAll('[data-message-author-role="assistant"]');
                    if (assistantMsgs.length > 0) {
                        return assistantMsgs[assistantMsgs.length - 1].innerText || '';
                    }
                    
                    // Fallback: find markdown/prose content
                    const prose = document.querySelectorAll('.markdown, .prose');
                    if (prose.length > 0) {
                        return prose[prose.length - 1].innerText || '';
                    }
                    
                    return '';
                }
            """)
            
            Log.data("Response", f"{len(response)} chars")
            return response
            
        except Exception as e:
            Log.warn(f"Response extraction error: {e}")
            return ""
    
    async def scrape(self, query: str, take_screenshot: bool = False) -> ScrapeResult:
        """Main scrape method - routes to appropriate scraper type."""
        if self.scraper_type == "google_ai":
            return await self.scrape_google_ai(query, take_screenshot)
        elif self.scraper_type == "chatgpt":
            return await self.scrape_chatgpt(query, take_screenshot)
        else:
            raise ValueError(f"Unsupported scraper type: {self.scraper_type}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_available_profiles() -> dict:
    """
    Get all available viewport profiles.
    
    Returns:
        dict with profile configurations grouped by type (phone, tablet, desktop)
    """
    profiles_by_type = {"phone": {}, "tablet": {}, "desktop": {}}
    for name, config in VIEWPORT_PROFILES.items():
        device_type = config.get("type", "unknown")
        if device_type in profiles_by_type:
            profiles_by_type[device_type][name] = {
                "viewport": config["viewport"],
                "is_mobile": config.get("is_mobile", False),
            }
    return profiles_by_type


def get_cost_info() -> dict:
    """
    Get Bright Data pricing information.
    
    Returns:
        dict with cost configuration for estimation
    """
    return {
        "scraping_browser": {
            "price_per_gb_usd": COST_CONFIG["scraping_browser"]["per_gb_cost_usd"],
            "base_request_usd": COST_CONFIG["scraping_browser"]["base_request_cost_usd"],
            "captcha_solve_usd": COST_CONFIG["scraping_browser"]["captcha_solve_cost_usd"],
            "avg_page_kb": COST_CONFIG["scraping_browser"]["avg_page_size_kb"],
        },
        "estimated_cost_per_scrape": {
            "min_usd": 0.01,  # Base cost only
            "typical_usd": 0.015,  # Base + average bandwidth
            "with_captcha_usd": 0.035,  # Base + bandwidth + CAPTCHA
        },
        "monthly_estimates": {
            "100_scrapes_usd": 1.50,
            "1000_scrapes_usd": 15.00,
            "10000_scrapes_usd": 150.00,
        }
    }


async def scrape_with_browser(
    query: str,
    country: str = "it",
    scraper_type: str = "google_ai",
    take_screenshot: bool = False,
    profile: str = "desktop_1080p",
    custom_viewport: dict = None,
    scroll_full_page: bool = True,
) -> ScrapeResult:
    """
    Convenience function to scrape using Bright Data Scraping Browser.
    
    Args:
        query: Search query
        country: Target country code (it, fr, de, nl, es, uk, ch, se)
        scraper_type: Type of scraper (google_ai, etc.)
        take_screenshot: Whether to capture screenshots
        profile: Device profile name or type. Options:
            - Types: "phone", "tablet", "desktop" (uses default for type)
            - Phones: "iphone_14", "iphone_15_pro", "pixel_7", "samsung_s23"
            - Tablets: "ipad_pro_12", "ipad_air", "galaxy_tab_s8"
            - Desktops: "desktop_1080p", "desktop_1440p", "macbook_pro_14", 
                        "macbook_air_13", "linux_desktop"
        custom_viewport: Custom viewport override {"width": int, "height": int}
        scroll_full_page: Whether to scroll to load all dynamic content
    
    Returns:
        ScrapeResult with:
        - response_text: Full extracted text content
        - sources: All links/sources with URLs
        - cost_estimate: Time and cost breakdown
        - profile_info: Device profile used
        - extraction_stats: Content extraction statistics
    
    Example:
        # Desktop scrape
        result = await scrape_with_browser("best pasta brands", profile="desktop")
        
        # iPhone scrape
        result = await scrape_with_browser("best pasta brands", profile="iphone_14")
        
        # Custom viewport
        result = await scrape_with_browser(
            "best pasta brands",
            custom_viewport={"width": 800, "height": 600}
        )
    """
    scraper = BrightDataBrowserScraper(
        country=country,
        scraper_type=scraper_type,
        profile=profile,
        custom_viewport=custom_viewport,
        scroll_full_page=scroll_full_page,
    )
    return await scraper.scrape(query, take_screenshot)
