"""
Bright Data Scraping Browser Client

The Scraping Browser provides a cloud-based browser with:
- Automatic CAPTCHA solving
- Browser fingerprint management
- Residential IP rotation
- Full CDP (Chrome DevTools Protocol) control
- JavaScript rendering

Best for:
- Complex JavaScript-heavy sites
- Sites requiring browser automation
- ChatGPT, Google AI Mode, etc.

Pricing (2025):
- $9.50/GB data transfer
- ~$0.01 base cost per request
- ~$0.02 additional for CAPTCHA solving
"""

import os
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal
import logging

logger = logging.getLogger(__name__)

# Check for Playwright
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@dataclass
class BrowserConfig:
    """Configuration for Scraping Browser."""
    country: str = "us"
    
    # Bright Data credentials
    customer_id: Optional[str] = None
    zone: Optional[str] = None
    password: Optional[str] = None
    
    # Viewport settings
    viewport_width: int = 1920
    viewport_height: int = 1080
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    has_touch: bool = False
    user_agent: Optional[str] = None
    
    # Behavior
    timeout_ms: int = 120000
    wait_for_idle: bool = True
    scroll_page: bool = True


@dataclass
class BrowserResponse:
    """Response from Scraping Browser."""
    success: bool
    content: str
    url: str
    
    # Browser info
    final_url: Optional[str] = None
    title: Optional[str] = None
    
    # Connection info
    ip_used: Optional[str] = None
    country: Optional[str] = None
    country_match: bool = False
    
    # Screenshots
    screenshot_path: Optional[str] = None
    
    # Cost tracking
    data_transferred_kb: float = 0.0
    estimated_cost_usd: float = 0.0
    duration_seconds: float = 0.0
    captcha_solved: bool = False
    
    # Error
    error: Optional[str] = None


class ScrapingBrowserClient:
    """
    Bright Data Scraping Browser Client.
    
    Provides full browser automation with:
    - Automatic anti-bot bypass
    - CAPTCHA solving
    - Residential IPs
    - JavaScript rendering
    
    Usage:
        async with ScrapingBrowserClient(country="it") as browser:
            response = await browser.navigate("https://google.com/search?q=test")
            print(response.content)
    """
    
    # Cost configuration
    COST_PER_GB = 9.50
    COST_PER_REQUEST = 0.01
    COST_PER_CAPTCHA = 0.02
    
    # Country code mapping for Bright Data
    COUNTRY_CODES = {
        "uk": "gb",  # Bright Data uses ISO codes
    }
    
    def __init__(
        self,
        country: str = "us",
        customer_id: Optional[str] = None,
        zone: Optional[str] = None,
        password: Optional[str] = None,
        viewport: str = "desktop",  # desktop, tablet, phone
        timeout_ms: int = 120000,
    ):
        """
        Initialize Scraping Browser client.
        
        Args:
            country: Target country code
            customer_id: Bright Data customer ID
            zone: Scraping Browser zone name
            password: Zone password
            viewport: Viewport preset (desktop, tablet, phone)
            timeout_ms: Navigation timeout in milliseconds
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright required for Scraping Browser. "
                "Install with: pip install playwright && playwright install"
            )
        
        self.country = self.COUNTRY_CODES.get(country.lower(), country.lower())
        self.customer_id = customer_id or os.getenv("BRIGHTDATA_CUSTOMER_ID", "hl_0d78e46f")
        self.zone = zone or os.getenv("BRIGHTDATA_BROWSER_ZONE", "scraping_browser1")
        self.password = password or os.getenv("BRIGHTDATA_BROWSER_PASSWORD")
        self.timeout_ms = timeout_ms
        
        # Set viewport based on preset
        self.viewport_config = self._get_viewport_config(viewport)
        
        # Browser state
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        # Cost tracking
        self._start_time: float = 0.0
        self._captcha_solved: bool = False
        
        if not self.password:
            raise ValueError(
                "Browser password required. Set BRIGHTDATA_BROWSER_PASSWORD env var."
            )
    
    def _get_viewport_config(self, preset: str) -> dict:
        """Get viewport configuration for preset."""
        presets = {
            "desktop": {
                "width": 1920, "height": 1080,
                "device_scale_factor": 1, "is_mobile": False, "has_touch": False,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            },
            "tablet": {
                "width": 820, "height": 1180,
                "device_scale_factor": 2, "is_mobile": True, "has_touch": True,
                "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1"
            },
            "phone": {
                "width": 390, "height": 844,
                "device_scale_factor": 3, "is_mobile": True, "has_touch": True,
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1"
            },
        }
        return presets.get(preset, presets["desktop"])
    
    @property
    def auth(self) -> str:
        """Build authentication string."""
        return f"brd-customer-{self.customer_id}-zone-{self.zone}-country-{self.country}:{self.password}"
    
    @property
    def endpoint(self) -> str:
        """WebSocket endpoint for CDP connection."""
        return f"wss://{self.auth}@brd.superproxy.io:9222"
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self):
        """Connect to Scraping Browser."""
        self._start_time = time.time()
        
        logger.info(f"Connecting to Scraping Browser (country={self.country})")
        
        self._playwright = await async_playwright().start()
        
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(
                self.endpoint,
                timeout=60000
            )
            
            # Get or create context with viewport settings
            if self._browser.contexts:
                self._context = self._browser.contexts[0]
            else:
                self._context = await self._browser.new_context(
                    viewport={
                        "width": self.viewport_config["width"],
                        "height": self.viewport_config["height"]
                    },
                    user_agent=self.viewport_config["user_agent"],
                    device_scale_factor=self.viewport_config["device_scale_factor"],
                    is_mobile=self.viewport_config["is_mobile"],
                    has_touch=self.viewport_config["has_touch"],
                )
            
            self._page = await self._context.new_page()
            self._page.set_default_timeout(self.timeout_ms)
            
            logger.info("Connected to Scraping Browser")
            
        except Exception as e:
            logger.error(f"Failed to connect to Scraping Browser: {e}")
            await self.disconnect()
            raise
    
    async def disconnect(self):
        """Disconnect from Scraping Browser."""
        if self._browser:
            try:
                await self._browser.close()
            except:
                pass
            self._browser = None
        
        if self._playwright:
            try:
                await self._playwright.stop()
            except:
                pass
            self._playwright = None
        
        logger.info("Disconnected from Scraping Browser")
    
    async def navigate(
        self,
        url: str,
        wait_for: str = "networkidle",
        screenshot: bool = False,
        screenshot_path: Optional[str] = None,
        verify_location: bool = True,
    ) -> BrowserResponse:
        """
        Navigate to a URL.
        
        Args:
            url: Target URL
            wait_for: Wait condition (networkidle, domcontentloaded, load)
            screenshot: Take screenshot
            screenshot_path: Custom screenshot path
            verify_location: Verify browser IP location
        
        Returns:
            BrowserResponse with page content
        """
        if not self._page:
            raise RuntimeError("Not connected. Use 'async with' or call connect() first.")
        
        start_time = time.time()
        ip_info = {}
        
        try:
            # Navigate to URL
            logger.info(f"Navigating to: {url}")
            await self._page.goto(url, wait_until=wait_for, timeout=self.timeout_ms)
            
            # Verify location if requested
            if verify_location:
                ip_info = await self._verify_location()
            
            # Wait for CAPTCHA if present
            captcha_status = await self._handle_captcha()
            self._captcha_solved = (captcha_status == "solved")
            
            # Get page content
            content = await self._page.content()
            title = await self._page.title()
            final_url = self._page.url
            
            # Take screenshot if requested
            ss_path = None
            if screenshot:
                ss_path = await self._take_screenshot(screenshot_path)
            
            # Calculate cost
            data_kb = len(content.encode('utf-8')) / 1024
            cost = self._calculate_cost(data_kb, self._captcha_solved)
            
            return BrowserResponse(
                success=True,
                content=content,
                url=url,
                final_url=final_url,
                title=title,
                ip_used=ip_info.get("ip"),
                country=ip_info.get("country"),
                country_match=ip_info.get("country", "").upper() == self.country.upper(),
                screenshot_path=ss_path,
                data_transferred_kb=data_kb,
                estimated_cost_usd=cost,
                duration_seconds=time.time() - start_time,
                captcha_solved=self._captcha_solved,
            )
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            
            # Try to get screenshot on error
            ss_path = None
            if self._page:
                try:
                    ss_path = await self._take_screenshot(f"error_{int(time.time())}.png")
                except:
                    pass
            
            return BrowserResponse(
                success=False,
                content="",
                url=url,
                error=str(e),
                screenshot_path=ss_path,
                duration_seconds=time.time() - start_time,
            )
    
    async def _verify_location(self) -> dict:
        """Verify browser IP location."""
        try:
            result = await asyncio.wait_for(
                self._page.evaluate("""
                    async () => {
                        try {
                            const resp = await fetch('https://ipinfo.io/json');
                            return await resp.json();
                        } catch (e) {
                            return { error: e.message };
                        }
                    }
                """),
                timeout=15.0
            )
            
            if result and not result.get("error"):
                logger.info(f"Browser IP: {result.get('ip')} ({result.get('country')})")
                return result
                
        except Exception as e:
            logger.warning(f"Location verification failed: {e}")
        
        return {}
    
    async def _handle_captcha(self) -> str:
        """Handle CAPTCHA if present."""
        try:
            client = await self._page.context.new_cdp_session(self._page)
            result = await client.send("Captcha.waitForSolve", {
                "detectTimeout": 30000
            })
            status = result.get("status", "not_detected")
            if status == "solved":
                logger.info("CAPTCHA solved automatically")
            return status
        except Exception as e:
            logger.debug(f"CAPTCHA check: {e}")
            return "not_detected"
    
    async def _take_screenshot(self, path: Optional[str] = None) -> str:
        """Take a screenshot."""
        from pathlib import Path
        from datetime import datetime
        from ...utils.filename import sanitize_filename
        
        if not path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"screenshot_{timestamp}.png"
        else:
            # Sanitize path if provided
            path = sanitize_filename(path) + ".png" if not path.endswith('.png') else sanitize_filename(path[:-4]) + ".png"
        
        # Ensure directory exists
        ss_dir = Path(__file__).parent.parent.parent / "data" / "screenshots"
        ss_dir.mkdir(parents=True, exist_ok=True)
        
        full_path = ss_dir / path
        await self._page.screenshot(path=str(full_path))
        
        logger.info(f"Screenshot saved: {full_path}")
        return str(full_path)
    
    def _calculate_cost(self, data_kb: float, captcha_solved: bool) -> float:
        """Calculate estimated cost."""
        data_gb = data_kb / (1024 * 1024)
        
        cost = self.COST_PER_REQUEST
        cost += data_gb * self.COST_PER_GB
        
        if captcha_solved:
            cost += self.COST_PER_CAPTCHA
        
        return round(cost, 6)
    
    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript in the page."""
        if not self._page:
            raise RuntimeError("Not connected")
        return await self._page.evaluate(script)
    
    async def click(self, selector: str):
        """Click an element."""
        if not self._page:
            raise RuntimeError("Not connected")
        await self._page.click(selector)
    
    async def type(self, selector: str, text: str, delay: int = 50):
        """Type text into an element."""
        if not self._page:
            raise RuntimeError("Not connected")
        await self._page.type(selector, text, delay=delay)
    
    async def wait_for_selector(self, selector: str, timeout: int = 30000):
        """Wait for a selector to appear."""
        if not self._page:
            raise RuntimeError("Not connected")
        await self._page.wait_for_selector(selector, timeout=timeout)


async def scrape_with_browser(
    url: str,
    country: str = "us",
    viewport: str = "desktop",
    screenshot: bool = False,
) -> BrowserResponse:
    """
    Convenience function to scrape a URL with Scraping Browser.
    
    Args:
        url: Target URL
        country: Target country code
        viewport: Viewport preset (desktop, tablet, phone)
        screenshot: Take screenshot
    
    Returns:
        BrowserResponse with page content
    """
    async with ScrapingBrowserClient(country=country, viewport=viewport) as browser:
        return await browser.navigate(url, screenshot=screenshot)
