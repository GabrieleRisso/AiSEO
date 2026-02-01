"""
Google AI Mode Scraper

Extracts AI-generated responses and source citations from Google AI Mode (udm=50).
Uses undetected-chromedriver to avoid bot detection.
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus
from dataclasses import dataclass, asdict
from typing import Optional, TYPE_CHECKING

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from ...utils.logger import Log, C, ChainConnectivityChecker
from ...utils.filename import sanitize_filename

if TYPE_CHECKING:
    from src.lib.antidetect import AntiDetectLayer


@dataclass
class Source:
    """A source citation from Google AI Mode."""
    title: str
    url: str
    date: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None


@dataclass
class ScrapeResult:
    """Result of scraping Google AI Mode."""
    query: str
    timestamp: str
    response_text: str
    sources: list[dict]
    source_count: int
    success: bool
    html_content: Optional[str] = None
    error: Optional[str] = None
    connectivity_info: Optional[dict] = None


class GoogleAIScraper:
    """Scrapes Google AI Mode using undetected-chromedriver."""

    BASE_URL = "https://www.google.com/search"

    def __init__(self, headless: bool = False, proxy: Optional[str] = None, antidetect: Optional['AntiDetectLayer'] = None, job_id: int = None):
        self.headless = headless
        self.proxy = proxy
        self.antidetect = antidetect
        self.job_id = job_id
        self._driver = None
        self.chain = ChainConnectivityChecker()
        # Set job ID for logging
        if job_id:
            Log.set_job(job_id)

    def __enter__(self):
        self._start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close_browser()

    def _start_browser(self):
        """Start undetected Chrome browser."""
        Log.step("Browser start", "browser")
        
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")

        if self.antidetect and self.antidetect.is_enabled:
            if self.antidetect.activate() and self.antidetect.profile:
                profile = self.antidetect.profile
                options.add_argument(f"--user-agent={profile.user_agent}")
                options.add_argument(f"--window-size={profile.screen_width},{profile.screen_height}")
                options.add_argument(f"--lang={profile.language}")
                Log.data("Profile", f"{profile.language}, {profile.screen_width}x{profile.screen_height}")
        else:
            options.add_argument("--window-size=1280,800")

        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")
            Log.data("Proxy", self.proxy[:50] + "..." if len(self.proxy) > 50 else self.proxy)

        if self.headless:
            options.add_argument("--headless=new")

        self._driver = uc.Chrome(options=options, use_subprocess=True, version_main=144)
        
        if self.antidetect and self.antidetect.is_enabled:
            for script in self.antidetect.get_stealth_scripts():
                try:
                    self._driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": script})
                except:
                    pass
                    
        Log.ok("Browser ready", "browser")
        time.sleep(2)

    def _close_browser(self):
        """Close the browser."""
        if self._driver:
            Log.step("Closing browser", "browser")
            self._driver.quit()
            Log.ok("Closed", "browser")

    def _screenshot(self, name: str = "debug"):
        """Take a screenshot."""
        try:
            # Use absolute path for Docker volume
            d = Path("/app/data/screenshots")
            d.mkdir(parents=True, exist_ok=True)
            # Sanitize filename to remove spaces and special characters
            sanitized_name = sanitize_filename(name)
            p = d / f"{sanitized_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self._driver.save_screenshot(str(p))
            Log.info(f"Screenshot: {p}")
            return str(p)
        except Exception as e:
            Log.warn(f"Screenshot failed: {e}")
            return None

    def _handle_cookie_consent(self):
        """Accept cookie consent if shown."""
        try:
            selectors = [
                "//button[contains(text(), 'Accept all')]",
                "//button[contains(text(), 'Accetta tutto')]",
                "//button[@aria-label='Accept all']",
                "//div[contains(text(), 'Accept all')]/ancestor::button",
            ]

            for selector in selectors:
                try:
                    accept_btn = WebDriverWait(self._driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    accept_btn.click()
                    Log.ok("Cookies accepted")
                    time.sleep(2)
                    return
                except:
                    continue

            # Fallback: JS click
            clicked = self._driver.execute_script("""
                var btns = document.querySelectorAll('button');
                for (var b of btns) {
                    var t = (b.textContent || '').toLowerCase();
                    if (t.includes('accept') || t.includes('accetta')) {
                        b.click(); return true;
                    }
                }
                return false;
            """)
            if clicked:
                Log.ok("Cookies accepted (JS)")
                time.sleep(1)
        except:
            pass

    def _wait_for_response(self, timeout: int = 60):
        """Wait for AI response to be ready."""
        Log.step("Waiting for AI response", "wait")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                page_text = self._driver.page_source

                # Check for CAPTCHA
                if "I'm not a robot" in page_text or "unusual traffic" in page_text.lower():
                    Log.warn("CAPTCHA detected!")
                    while "I'm not a robot" in self._driver.page_source:
                        time.sleep(1)
                    Log.ok("CAPTCHA resolved")
                    time.sleep(2)

                # Check if response is ready
                if "Thinking" not in page_text:
                    time.sleep(3)
                    Log.ok("Response ready", "wait")
                    return
            except:
                pass
            time.sleep(1)
        
        Log.warn("Timeout waiting for response")

    def _extract_response_text(self) -> str:
        """Extract the main AI response text."""
        try:
            response_parts = []

            for h in self._driver.find_elements(By.CSS_SELECTOR, "h2, h3"):
                text = h.text.strip()
                if text and 3 < len(text) < 200:
                    if not any(skip in text.lower() for skip in ['sign in', 'accessibility', 'filters']):
                        response_parts.append(f"## {text}")

            for li in self._driver.find_elements(By.TAG_NAME, "li"):
                text = li.text.strip()
                if text and len(text) > 30:
                    if not any(skip in text.lower() for skip in ['sign in', 'accessibility']):
                        response_parts.append(f"- {text}")

            for table in self._driver.find_elements(By.TAG_NAME, "table"):
                rows = []
                for tr in table.find_elements(By.TAG_NAME, "tr"):
                    cells = [td.text.strip() for td in tr.find_elements(By.CSS_SELECTOR, "th, td")]
                    if cells:
                        rows.append(" | ".join(cells))
                if rows:
                    response_parts.append("\n".join(rows))

            return "\n\n".join(response_parts)
        except Exception as e:
            Log.warn(f"Response extraction: {e}")
            return ""

    def _expand_sources(self):
        """Click button to expand all sources."""
        try:
            buttons = self._driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                try:
                    text = btn.text.strip()
                    if text and ('sites' in text.lower() or re.match(r'^\d+\s*$', text)):
                        if btn.is_displayed():
                            btn.click()
                            Log.info(f"Expanded sources: {text}")
                            time.sleep(3)
                            return True
                except:
                    continue

            sites_elements = self._driver.find_elements(By.XPATH, "//*[contains(text(), 'sites')]")
            for elem in sites_elements:
                try:
                    if elem.is_displayed() and elem.is_enabled():
                        elem.click()
                        time.sleep(3)
                        return True
                except:
                    continue
            return False
        except:
            return False

    def _extract_sources(self) -> list[Source]:
        """Extract source citations."""
        sources = []
        seen_urls = set()

        try:
            self._expand_sources()
            time.sleep(1)

            # Get links from dialog or page
            dialog_links = []
            try:
                dialogs = self._driver.find_elements(By.CSS_SELECTOR, "dialog, [role='dialog'], [aria-modal='true']")
                for dialog in dialogs:
                    if dialog.is_displayed():
                        for _ in range(5):
                            try:
                                self._driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                                time.sleep(0.5)
                            except:
                                break
                        dialog_links = dialog.find_elements(By.CSS_SELECTOR, "a[href^='http']")
                        break
            except:
                pass

            if not dialog_links:
                dialog_links = self._driver.find_elements(By.CSS_SELECTOR, "li a[href^='http']")

            if len(dialog_links) < 20:
                all_links = self._driver.find_elements(By.CSS_SELECTOR, "a[href^='http']")
                existing_hrefs = {l.get_attribute("href") for l in dialog_links}
                for link in all_links:
                    href = link.get_attribute("href")
                    if href and href not in existing_hrefs:
                        dialog_links.append(link)
                        existing_hrefs.add(href)

            for link in dialog_links:
                try:
                    url = link.get_attribute("href")
                    title = link.text.strip()
                    
                    if not title:
                        try:
                            title = link.find_element(By.XPATH, ".//div | .//span").text.strip()
                        except:
                            pass
                    if not title:
                        title = link.get_attribute("aria-label") or ""

                    if not url or url in seen_urls:
                        continue
                    if any(skip in url for skip in ['google.com', 'accounts.google', 'support.google', 'policies.google', 'g.co/', 'gstatic.com']):
                        continue

                    if not title:
                        try:
                            from urllib.parse import urlparse
                            path = urlparse(url).path
                            title = path.split("/")[-1].replace("-", " ").replace("_", " ").title()
                        except:
                            title = url

                    if len(title) < 10:
                        continue
                    if any(skip in title.lower() for skip in ['sign in', 'accessibility', 'privacy', 'terms', 'google apps']):
                        continue

                    seen_urls.add(url)

                    # Get metadata
                    date = None
                    description = None
                    try:
                        parent = link
                        for _ in range(4):
                            parent = parent.find_element(By.XPATH, "./..")
                            parent_text = parent.text

                            if not date:
                                date_match = re.search(
                                    r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}|'
                                    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
                                    parent_text, re.IGNORECASE
                                )
                                if date_match:
                                    date = date_match.group()

                            if not description and len(parent_text) > len(title) + 40:
                                desc = parent_text.replace(title, "")
                                if date:
                                    desc = desc.replace(date, "")
                                desc = re.sub(r'Opens in new tab|About this result', '', desc, flags=re.IGNORECASE).strip()
                                if len(desc) > 20:
                                    description = desc[:300]
                                    break
                    except:
                        pass

                    publisher = None
                    try:
                        from urllib.parse import urlparse
                        hostname = urlparse(url).hostname
                        if hostname:
                            publisher = hostname.replace("www.", "").split(".")[0].capitalize()
                    except:
                        pass

                    clean_title = re.sub(r'\.?\s*Opens in new tab\.?', '', title, flags=re.IGNORECASE).strip()

                    if clean_title:
                        sources.append(Source(
                            title=clean_title,
                            url=url,
                            date=date,
                            description=description,
                            publisher=publisher
                        ))
                except:
                    continue

            Log.ok(f"Extracted {len(sources)} sources")
        except Exception as e:
            Log.warn(f"Source extraction: {e}")

        return sources

    async def scrape(self, query: str, take_screenshot: bool = False) -> ScrapeResult:
        """Scrape Google AI Mode for a query."""
        Log.step(f"Scrape query=\"{query}\"", "scrape")
        
        timestamp = datetime.now(timezone.utc).isoformat()
        html_content = ""
        connectivity_info = {}

        try:
            # Get target country for verification
            target_country = None
            if self.antidetect and self.antidetect.is_enabled:
                target_country = getattr(self.antidetect.config, 'target_country', None)

            # Verify VPN layer
            vpn_result = self.chain.verify_vpn_layer(target_country)
            
            # Start browser
            self._start_browser()
            time.sleep(2)
            
            # Verify proxy layer via browser
            proxy_result = self.chain.verify_proxy_layer(self._driver, target_country)
            
            # Build connectivity info
            connectivity_info = {
                "vpn": vpn_result,
                "proxy": proxy_result,
                "chain_valid": vpn_result.get("ip") != proxy_result.get("ip") if vpn_result.get("ip") and proxy_result.get("ip") else proxy_result.get("success", False)
            }
            
            # Log chain status
            print()
            Log.result(vpn_result.get("success", False), f"VPN: {vpn_result.get('ip', 'N/A')} ({vpn_result.get('country_code', '?')})")
            Log.result(proxy_result.get("success", False), f"Proxy: {proxy_result.get('ip', 'N/A')} ({proxy_result.get('country_code', '?')})")
            if connectivity_info["chain_valid"]:
                Log.result(True, "Chain valid")
            print()

            if take_screenshot:
                self._screenshot("chain")

            # Build URL with AI Mode parameter
            encoded_query = quote_plus(query)
            url = f"{self.BASE_URL}?udm=50&q={encoded_query}"

            Log.step(f"Loading Google AI Mode", "nav")
            self._driver.get(url)
            time.sleep(2)

            self._handle_cookie_consent()
            self._wait_for_response()

            if take_screenshot:
                query_safe = sanitize_filename(query[:30])
                self._screenshot(f"google_ai_{query_safe}")

            try:
                html_content = self._driver.page_source
            except:
                pass

            Log.step("Extracting response", "extract")
            response_text = self._extract_response_text()
            
            if not response_text:
                page_text = self._driver.find_element(By.TAG_NAME, "body").text
                if "unusual traffic" in page_text.lower() or "robot" in page_text.lower():
                    raise Exception("Blocked by Google (CAPTCHA/Unusual Traffic)")

            Log.step("Extracting sources", "extract")
            sources = self._extract_sources()

            if take_screenshot:
                query_safe = sanitize_filename(query[:30])
                self._screenshot(f"google_ai_final_{query_safe}")

            Log.result(True, f"Done - {len(sources)} sources")

            return ScrapeResult(
                query=query,
                timestamp=timestamp,
                response_text=response_text,
                sources=[asdict(s) for s in sources],
                source_count=len(sources),
                success=True,
                html_content=html_content,
                connectivity_info=connectivity_info
            )

        except Exception as e:
            Log.fail(f"Scrape failed: {e}")
            
            # ALWAYS take screenshot on error for debugging
            error_screenshot = None
            if self._driver:
                # Sanitize query for filename
                query_safe = sanitize_filename(query[:30])
                error_screenshot = self._screenshot(f"error_{query_safe}")
            
            if not html_content and self._driver:
                try:
                    html_content = self._driver.page_source
                except:
                    pass
            
            # Log more details for debugging
            Log.warn(f"Error details: {str(e)}")
            if error_screenshot:
                Log.info(f"Error screenshot saved: {error_screenshot}")
                    
            return ScrapeResult(
                query=query,
                timestamp=timestamp,
                response_text="",
                sources=[],
                source_count=0,
                success=False,
                error=str(e),
                html_content=html_content,
                connectivity_info=connectivity_info
            )

    def save_result(self, result: ScrapeResult, output_dir: Path):
        """Save result to JSON file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = re.sub(r'[^\w\s-]', '', result.query.lower())
        filename = re.sub(r'[-\s]+', '_', filename)[:50]
        filename = f"{filename}.json"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, indent=2, ensure_ascii=False)

        Log.info(f"Saved: {filepath}")
        return filepath
