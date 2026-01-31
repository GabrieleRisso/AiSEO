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

from ..utils.logger import Log, C

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
    
    async def scrape(self, query: str, take_screenshot: bool = False) -> ScrapeResult:
        """Main scrape method - routes to appropriate scraper type."""
        if self.scraper_type == "google_ai":
            return await self.scrape_google_ai(query, take_screenshot)
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
