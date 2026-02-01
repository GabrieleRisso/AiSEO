"""
ChatGPT Web Scraper - Reliable Implementation

This scraper accesses ChatGPT without login using OpenAI's instant access feature.
Key design decisions:
1. Uses chatgpt.com (not chat.openai.com) - the new domain with instant access
2. Uses mobile iPhone user agent for better access without login
3. Implements streaming response detection for reliable extraction
4. Handles various popups and consent dialogs

Note: Instant access is IP-based and may have regional availability.
For best results, use with a US/Canada IP or Bright Data Scraping Browser.
"""

import time
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from ..common.base import BaseScraper

# Try to import playwright for modern approach
try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Fallback to selenium/undetected-chromedriver
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class ChatGPTScraper(BaseScraper):
    """
    Scraper for ChatGPT web interface with instant access (no login required).
    
    Uses chatgpt.com with mobile user agent for best compatibility.
    Supports both Playwright (preferred) and Selenium backends.
    
    Key selectors (2026):
    - Input: #prompt-textarea
    - Send buttons: [data-testid="fruitjuice-send-button"], [data-testid="send-button"]
    - Assistant messages: div[data-message-author-role="assistant"]
    - Streaming indicator: .result-streaming
    - Thinking indicator: .result-thinking
    """
    
    # Use chatgpt.com - the new domain with instant access
    BASE_URL = "https://chatgpt.com"
    
    # Mobile user agent for better access without login
    MOBILE_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1"
    
    def __init__(self, headless: bool = True, proxy: str = None, antidetect = None):
        super().__init__(headless, proxy, antidetect)
        self._driver = None  # Selenium driver
        self._browser = None  # Playwright browser
        self._page = None  # Playwright page
        self._playwright = None
        self._use_playwright = PLAYWRIGHT_AVAILABLE
        self._message_count = 0
        self._last_message_id = None

    def _start_browser(self):
        """Start browser (Selenium fallback for sync context)."""
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Neither playwright nor selenium available. Install one.")
        
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        
        # Use mobile user agent for better instant access
        options.add_argument(f"--user-agent={self.MOBILE_USER_AGENT}")
        options.add_argument("--window-size=390,844")  # iPhone 14 viewport

        if self.antidetect and self.antidetect.is_enabled:
            print("Configuring Anti-Detect layer for ChatGPT...")
            if self.antidetect.activate() and self.antidetect.profile:
                profile = self.antidetect.profile
                options.add_argument(f"--lang={profile.language}")

        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")

        if self.headless:
            options.add_argument("--headless=new")

        self._driver = uc.Chrome(options=options, use_subprocess=True, version_main=131)
        
        if self.antidetect and self.antidetect.is_enabled:
            for script in self.antidetect.get_stealth_scripts():
                try:
                    self._driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": script})
                except Exception as e:
                    print(f"Failed to inject stealth script: {e}")
                    
        time.sleep(2)

    def _take_screenshot(self, name: str = "debug") -> Optional[str]:
        """Take a screenshot for debugging."""
        try:
            screenshot_dir = Path(__file__).parent.parent.parent / "data" / "screenshots"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            path = screenshot_dir / f"chatgpt_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self._driver.save_screenshot(str(path))
            print(f"  ○ Screenshot: {path.name}")
            return str(path)
        except Exception as e:
            print(f"  ⚠ Screenshot error: {e}")
            return None

    def _handle_cookie_consent(self) -> bool:
        """Handle cookie consent banner if shown."""
        try:
            cookie_selectors = [
                "//button[contains(text(), 'Accept')]",
                "//button[contains(text(), 'Accept all')]",
                "//button[contains(text(), 'Allow')]",
                "//button[@id='cookie-banner-accept']",
                "button[data-testid='cookie-banner-accept']",
            ]
            
            for selector in cookie_selectors:
                try:
                    if selector.startswith("//"):
                        btn = WebDriverWait(self._driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        btn = WebDriverWait(self._driver, 2).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    if btn.is_displayed():
                        btn.click()
                        print(f"  ✓ Cookie consent accepted")
                        time.sleep(1)
                        return True
                except:
                    continue
                    
        except Exception as e:
            pass
        
        return False

    def _handle_login_prompt(self) -> bool:
        """Handle login prompts - try to continue without login."""
        try:
            # Look for "Stay logged out" or similar buttons
            dismiss_selectors = [
                "//button[contains(text(), 'Stay logged out')]",
                "//button[contains(text(), 'Continue')]",
                "//button[contains(text(), 'Skip')]",
                "//button[contains(text(), 'Not now')]",
                "//button[contains(text(), 'Maybe later')]",
                "button[aria-label='Close']",
                "button[aria-label='close']",
            ]
            
            for selector in dismiss_selectors:
                try:
                    if selector.startswith("//"):
                        btn = self._driver.find_element(By.XPATH, selector)
                    else:
                        btn = self._driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if btn.is_displayed():
                        btn.click()
                        print(f"  ✓ Dismissed login prompt")
                        time.sleep(1)
                        return True
                except:
                    continue
                    
        except Exception as e:
            pass
        
        return False

    def _find_and_fill_input(self, query: str) -> bool:
        """Find the prompt textarea and fill it with the query."""
        try:
            # Wait for page to settle
            time.sleep(2)
            
            # Try to find prompt-textarea first (most reliable)
            try:
                textarea = WebDriverWait(self._driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#prompt-textarea"))
                )
                if textarea:
                    # Use JavaScript to set value (more reliable)
                    self._driver.execute_script(
                        f'document.querySelector("#prompt-textarea").value = "{query[:-1]}"'
                    )
                    # Type the last character to trigger input events
                    textarea.send_keys(query[-1])
                    print(f"  ✓ Input filled via #prompt-textarea")
                    return True
            except:
                pass
            
            # Fallback: try other selectors
            input_selectors = [
                "textarea[placeholder*='Message']",
                "textarea[placeholder*='message']",
                "textarea[data-id='root']",
                "textarea",
            ]
            
            for selector in input_selectors:
                try:
                    textarea = self._driver.find_element(By.CSS_SELECTOR, selector)
                    if textarea.is_displayed():
                        textarea.click()
                        time.sleep(0.5)
                        textarea.send_keys(query)
                        print(f"  ✓ Input filled via {selector}")
                        return True
                except:
                    continue
            
            # JavaScript fallback
            filled = self._driver.execute_script("""
                const ta = document.querySelector('#prompt-textarea') || document.querySelector('textarea');
                if (ta) {
                    ta.focus();
                    ta.value = arguments[0];
                    ta.dispatchEvent(new Event('input', { bubbles: true }));
                    return true;
                }
                return false;
            """, query)
            
            if filled:
                print(f"  ✓ Input filled via JavaScript")
                return True
                
            return False
            
        except Exception as e:
            print(f"  ✗ Input fill error: {e}")
            return False

    def _click_send_button(self) -> bool:
        """Click the send button to submit the query."""
        try:
            # Try fruitjuice-send-button first (newer UI)
            try:
                fruitjuice = self._driver.execute_script(
                    'return document.querySelector(\'[data-testid="fruitjuice-send-button"]\') !== null'
                )
                if fruitjuice:
                    self._driver.execute_script(
                        'document.querySelector(\'[data-testid="fruitjuice-send-button"]\').click()'
                    )
                    print(f"  ✓ Clicked fruitjuice-send-button")
                    return True
            except:
                pass
            
            # Try standard send-button
            try:
                send = self._driver.execute_script(
                    'return document.querySelector(\'[data-testid="send-button"]\') !== null'
                )
                if send:
                    self._driver.execute_script(
                        'document.querySelector(\'[data-testid="send-button"]\').click()'
                    )
                    print(f"  ✓ Clicked send-button")
                    return True
            except:
                pass
            
            # Fallback: press Enter
            textarea = self._driver.find_element(By.CSS_SELECTOR, "#prompt-textarea, textarea")
            textarea.send_keys(Keys.ENTER)
            print(f"  ✓ Submitted via Enter key")
            return True
            
        except Exception as e:
            print(f"  ✗ Send button error: {e}")
            return False

    def _wait_for_response(self, timeout: int = 60) -> str:
        """Wait for ChatGPT response to complete and extract it."""
        print("  → Waiting for response...")
        
        try:
            # Wait for initial response to appear
            start_time = time.time()
            initial_count = len(self._driver.find_elements(
                By.CSS_SELECTOR, 'div[data-message-author-role="assistant"]'
            ))
            
            # Wait for new message to appear
            while (time.time() - start_time) < timeout:
                messages = self._driver.find_elements(
                    By.CSS_SELECTOR, 'div[data-message-author-role="assistant"]'
                )
                if len(messages) > initial_count:
                    break
                time.sleep(0.3)
            
            if len(messages) <= initial_count:
                print("  ⚠ No new response detected")
                return ""
            
            # Wait for response to finish streaming
            last_message = messages[-1]
            previous_text = ""
            stable_count = 0
            
            while (time.time() - start_time) < timeout:
                # Check if still streaming
                try:
                    streaming = last_message.find_elements(By.CSS_SELECTOR, '.result-streaming')
                    thinking = last_message.find_elements(By.CSS_SELECTOR, '.result-thinking')
                    
                    if not streaming and not thinking:
                        # Check text stability
                        current_text = last_message.text
                        if current_text == previous_text:
                            stable_count += 1
                            if stable_count >= 3:  # Text stable for 0.9s
                                break
                        else:
                            stable_count = 0
                        previous_text = current_text
                except:
                    pass
                
                time.sleep(0.3)
            
            # Extract final response
            response_text = last_message.text
            print(f"  ✓ Response received: {len(response_text)} chars")
            return response_text
            
        except Exception as e:
            print(f"  ✗ Response extraction error: {e}")
            return ""

    def _verify_connectivity(self, take_screenshot: bool = False) -> dict:
        """Verify VPN and proxy connectivity before scraping."""
        import json
        result = {
            "vpn_working": False,
            "proxy_working": False,
            "ip_address": None,
            "country": None,
            "isp": None,
            "org": None
        }
        
        print("\n" + "="*60)
        print("           CONNECTIVITY VERIFICATION")
        print("="*60)
        
        try:
            self._driver.get("https://ipinfo.io/json")
            time.sleep(3)
            body_text = self._driver.find_element(By.TAG_NAME, "body").text
            
            try:
                ip_data = json.loads(body_text)
                result["ip_address"] = ip_data.get("ip", "unknown")
                result["country"] = ip_data.get("country", "unknown")
                result["isp"] = ip_data.get("org", "unknown")
                result["org"] = ip_data.get("org", "unknown")
                result["vpn_working"] = True
                result["proxy_working"] = True
                
                print(f"\n  IP:      {result['ip_address']}")
                print(f"  Country: {result['country']}")
                print(f"  ISP:     {result['isp']}")
                    
            except json.JSONDecodeError:
                print(f"  ⚠ Could not parse IP info")
                    
        except Exception as e:
            print(f"  ✗ Connectivity check failed: {e}")
        
        if take_screenshot:
            self._take_screenshot("connectivity_test")
        
        print("="*60 + "\n")
        
        return result

    async def scrape(self, query: str, take_screenshot: bool = False) -> Dict[str, Any]:
        """
        Scrape ChatGPT web interface.
        
        Uses instant access (no login) via chatgpt.com with mobile user agent.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        html_content = ""
        connectivity_info = {}
        
        print("\n" + "="*66)
        print("           ChatGPT Scrape (Instant Access)")
        print("="*66)
        print(f"\n  Query: {query[:60]}{'...' if len(query) > 60 else ''}")
        
        try:
            self._start_browser()
            print("  ✓ Browser started (mobile mode)")
            
            # Verify connectivity
            connectivity_info = self._verify_connectivity(take_screenshot)
            
            # Navigate to ChatGPT
            print(f"\n  → Navigating to {self.BASE_URL}")
            self._driver.get(self.BASE_URL)
            
            # Wait for page to load
            print("  → Waiting for page load...")
            time.sleep(5)
            
            if take_screenshot:
                self._take_screenshot("chatgpt_loaded")
            
            # Handle cookie consent
            self._handle_cookie_consent()
            
            # Handle login prompts
            self._handle_login_prompt()
            
            time.sleep(2)
            
            # Check if we can access without login
            page_content = self._driver.page_source
            login_required = any(ind in page_content for ind in [
                "Sign up", "Log in", "Create a free account", "Get started"
            ])
            
            if login_required:
                # Try to dismiss again
                self._handle_login_prompt()
                time.sleep(2)
                
                # Check again
                page_content = self._driver.page_source
                if any(ind in page_content for ind in ["Sign up", "Log in"]):
                    # Check if prompt textarea exists anyway (instant access)
                    has_input = self._driver.execute_script(
                        'return document.querySelector("#prompt-textarea") !== null'
                    )
                    if not has_input:
                        if take_screenshot:
                            self._take_screenshot("chatgpt_login_required")
                        raise Exception("ChatGPT requires login - instant access not available from this IP")
            
            print("  ✓ Instant access available")
            
            if take_screenshot:
                self._take_screenshot("chatgpt_ready")
            
            # Find and fill input
            print("\n  → Sending query...")
            if not self._find_and_fill_input(query):
                raise Exception("Could not find or fill chat input")
            
            time.sleep(1)
            
            # Click send button
            if not self._click_send_button():
                raise Exception("Could not submit query")
            
            # Wait for and extract response
            response_text = self._wait_for_response()
            
            if take_screenshot:
                self._take_screenshot("chatgpt_response")
            
            # Capture HTML
            try:
                html_content = self._driver.page_source
            except:
                pass
            
            success = bool(response_text)
            print(f"\n  {'✓' if success else '✗'} Scrape {'completed' if success else 'failed'}")
            
            return {
                "status": "success" if success else "failed",
                "data": [],
                "response_text": response_text,
                "html_content": html_content,
                "metadata": {
                    "source": "chatgpt",
                    "url": self.BASE_URL,
                    "proxy_used": self.proxy,
                    "timestamp": timestamp,
                    "connectivity": connectivity_info,
                    "method": "instant_access",
                    "user_agent": self.MOBILE_USER_AGENT[:50] + "...",
                }
            }
            
        except Exception as e:
            print(f"\n  ✗ Error: {e}")
            
            if take_screenshot and self._driver:
                self._take_screenshot("chatgpt_error")
            
            if not html_content and self._driver:
                try:
                    html_content = self._driver.page_source
                except:
                    pass
            
            return {
                "status": "failed",
                "data": [],
                "response_text": "",
                "html_content": html_content,
                "error": str(e),
                "metadata": {
                    "source": "chatgpt",
                    "url": self.BASE_URL,
                    "proxy_used": self.proxy,
                    "timestamp": timestamp,
                    "connectivity": connectivity_info,
                }
            }
        finally:
            if self._driver:
                self._driver.quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._driver:
            self._driver.quit()
