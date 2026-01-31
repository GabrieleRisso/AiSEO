import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base import BaseScraper

class ChatGPTScraper(BaseScraper):
    """Scraper for ChatGPT web interface."""
    
    BASE_URL = "https://chat.openai.com"
    
    def __init__(self, headless: bool = True, proxy: str = None, antidetect = None):
        super().__init__(headless, proxy, antidetect)
        self._driver = None

    def _start_browser(self):
        """Start undetected Chrome browser."""
        options = uc.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")

        if self.antidetect and self.antidetect.is_enabled:
            print("Configuring Anti-Detect layer for ChatGPT...")
            if self.antidetect.activate() and self.antidetect.profile:
                profile = self.antidetect.profile
                options.add_argument(f"--user-agent={profile.user_agent}")
                options.add_argument(f"--window-size={profile.screen_width},{profile.screen_height}")
                options.add_argument(f"--lang={profile.language}")
        else:
            options.add_argument("--window-size=1280,800")

        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")

        if self.headless:
            options.add_argument("--headless=new")

        self._driver = uc.Chrome(options=options, use_subprocess=True, version_main=144)
        
        if self.antidetect and self.antidetect.is_enabled:
            for script in self.antidetect.get_stealth_scripts():
                try:
                    self._driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": script})
                except Exception as e:
                    print(f"Failed to inject stealth script: {e}")
                    
        time.sleep(2)

    def _take_screenshot(self, name: str = "debug"):
        """Take a screenshot for debugging."""
        try:
            screenshot_dir = Path(__file__).parent.parent.parent / "data" / "screenshots"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            path = screenshot_dir / f"chatgpt_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self._driver.save_screenshot(str(path))
            print(f"Screenshot saved: {path}")
            return str(path)
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None

    def _handle_cookie_consent(self):
        """Handle cookie consent banner if shown."""
        try:
            print("Checking for cookie consent banner...")
            time.sleep(2)
            
            # Look for cookie consent buttons
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
                        btn = WebDriverWait(self._driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        btn = WebDriverWait(self._driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    if btn.is_displayed():
                        btn.click()
                        print(f"Clicked cookie consent button: {selector}")
                        time.sleep(2)
                        return True
                except:
                    continue
                    
        except Exception as e:
            print(f"Cookie consent handling error: {e}")
        
        return False

    def _handle_login_popup(self):
        """Handle login popups or modals."""
        try:
            print("Checking for login popups...")
            time.sleep(1)
            
            close_selectors = [
                "button[aria-label='Close']",
                "button[aria-label='close']",
                "button[data-testid='close-button']",
                "//button[contains(text(), 'Skip')]",
                "//button[contains(text(), 'Not now')]",
                "//button[contains(text(), 'Maybe later')]",
            ]
            
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        btn = self._driver.find_element(By.XPATH, selector)
                    else:
                        btn = self._driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if btn.is_displayed():
                        btn.click()
                        print(f"Closed popup with selector: {selector}")
                        time.sleep(1)
                        return True
                except:
                    continue
                    
        except Exception as e:
            print(f"Login popup handling error: {e}")
        
        return False

    def _navigate_to_chat(self):
        """Navigate to the chat interface."""
        try:
            print("Navigating to chat interface...")
            
            # Check if we're already on chat page
            current_url = self._driver.current_url
            if "/chat" in current_url or "chat.openai.com" in current_url:
                print("Already on chat page")
                return True
            
            # Look for "New chat" or chat button
            chat_selectors = [
                "//a[contains(text(), 'New chat')]",
                "//a[contains(@href, '/chat')]",
                "//button[contains(text(), 'New chat')]",
                "a[href*='/chat']",
                "button[data-testid='new-chat-button']",
            ]
            
            for selector in chat_selectors:
                try:
                    if selector.startswith("//"):
                        element = self._driver.find_element(By.XPATH, selector)
                    else:
                        element = self._driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if element.is_displayed():
                        element.click()
                        print(f"Clicked chat navigation: {selector}")
                        time.sleep(3)
                        return True
                except:
                    continue
            
            # Fallback: navigate directly to chat URL
            try:
                self._driver.get(f"{self.BASE_URL}/chat")
                time.sleep(3)
                print("Navigated directly to chat URL")
                return True
            except Exception as e:
                print(f"Failed to navigate to chat: {e}")
                return False
                
        except Exception as e:
            print(f"Error navigating to chat: {e}")
            return False

    def _find_chat_input(self):
        """Find the chat input textarea."""
        try:
            # Common selectors for ChatGPT input
            input_selectors = [
                "#prompt-textarea",
                "textarea[placeholder*='Message']",
                "textarea[placeholder*='message']",
                "textarea[data-id='root']",
                "textarea",
            ]
            
            for selector in input_selectors:
                try:
                    if selector.startswith("#") or selector.startswith("["):
                        textarea = self._driver.find_element(By.CSS_SELECTOR, selector)
                    else:
                        textareas = self._driver.find_elements(By.TAG_NAME, "textarea")
                        for ta in textareas:
                            if ta.is_displayed():
                                return ta
                        return None
                    
                    if textarea.is_displayed():
                        print(f"Found chat input with selector: {selector}")
                        return textarea
                except:
                    continue
            
            # Fallback: find any visible textarea
            textareas = self._driver.find_elements(By.TAG_NAME, "textarea")
            for ta in textareas:
                if ta.is_displayed():
                    print("Found chat input (fallback)")
                    return ta
                    
        except Exception as e:
            print(f"Error finding chat input: {e}")
        
        return None

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
        print("CONNECTIVITY VERIFICATION")
        print("="*60)
        
        # Step 1: Test basic connectivity with a simple HTTP request
        print("\n[Step 1] Testing basic connectivity...")
        try:
            self._driver.get("http://httpbin.org/ip")
            time.sleep(3)
            body_text = self._driver.find_element(By.TAG_NAME, "body").text
            print(f"  httpbin.org response: {body_text}")
            if "origin" in body_text.lower():
                result["proxy_working"] = True
                print("  ✓ Proxy connection established")
        except Exception as e:
            print(f"  ✗ Basic connectivity failed: {e}")
        
        # Step 2: Get detailed IP information
        print("\n[Step 2] Getting detailed IP information...")
        try:
            self._driver.get("http://ip-api.com/json")
            time.sleep(3)
            body_text = self._driver.find_element(By.TAG_NAME, "body").text
            print(f"  ip-api.com response: {body_text}")
            
            try:
                ip_data = json.loads(body_text)
                result["ip_address"] = ip_data.get("query", "unknown")
                result["country"] = ip_data.get("countryCode", "unknown")
                result["isp"] = ip_data.get("isp", "unknown")
                result["org"] = ip_data.get("org", "unknown")
                
                print(f"\n  IP Address: {result['ip_address']}")
                print(f"  Country: {result['country']}")
                print(f"  ISP: {result['isp']}")
                print(f"  Organization: {result['org']}")
                
                if result["country"]:
                    result["vpn_working"] = True
                    print(f"\n  ✓ VPN/Proxy routing confirmed to {result['country']}")
                    
            except json.JSONDecodeError:
                print(f"  ⚠ Could not parse IP info")
                    
        except Exception as e:
            print(f"  ✗ IP verification failed: {e}")
        
        if take_screenshot:
            self._take_screenshot("connectivity_test")
        
        print("\n" + "="*60)
        print(f"VERIFICATION SUMMARY:")
        print(f"  VPN Working: {'✓ Yes' if result['vpn_working'] else '✗ No'}")
        print(f"  Proxy Working: {'✓ Yes' if result['proxy_working'] else '✗ No'}")
        print(f"  IP: {result['ip_address']} ({result['country']})")
        print("="*60 + "\n")
        
        return result

    async def scrape(self, query: str, take_screenshot: bool = False) -> Dict[str, Any]:
        """Scrape ChatGPT web interface."""
        timestamp = datetime.now(timezone.utc).isoformat()
        html_content = ""
        connectivity_info = {}
        
        try:
            self._start_browser()
            
            # Allow browser to fully initialize
            print("Waiting for browser initialization...")
            time.sleep(3)
            
            # Verify VPN and Proxy connectivity
            connectivity_info = self._verify_connectivity(take_screenshot)
            
            # Navigate to ChatGPT
            print(f"\nNavigating to {self.BASE_URL}...")
            self._driver.get(self.BASE_URL)
            
            # Give more time for page to load through proxy
            print("Waiting for page to load...")
            time.sleep(5)
            
            if take_screenshot:
                self._take_screenshot("chatgpt_home")
            
            # Handle cookie consent
            self._handle_cookie_consent()
            
            # Handle login popups
            self._handle_login_popup()
            
            # Navigate to chat interface
            self._navigate_to_chat()
            
            time.sleep(3)
            
            if take_screenshot:
                self._take_screenshot("chatgpt_chat")
            
            # Find and use chat input
            textarea = self._find_chat_input()
            
            if not textarea:
                raise Exception("Could not find chat input")
            
            # Send query
            print(f"Sending query: {query[:50]}...")
            textarea.click()
            time.sleep(1)
            textarea.send_keys(query)
            time.sleep(1)
            textarea.send_keys(Keys.ENTER)
            print("Query submitted...")
            
            # Wait for response
            print("Waiting for response...")
            time.sleep(5)
            
            # Wait for response to appear
            try:
                WebDriverWait(self._driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-message-author-role='assistant']"))
                )
            except:
                pass
            
            # Allow time for response to complete
            time.sleep(10)
            
            if take_screenshot:
                self._take_screenshot(f"chatgpt_result_{query[:10]}")
            
            # Capture HTML
            try:
                html_content = self._driver.page_source
            except:
                pass
            
            # Extract response text
            response_text = ""
            try:
                # Find assistant messages
                assistant_messages = self._driver.find_elements(
                    By.CSS_SELECTOR, 
                    "[data-message-author-role='assistant']"
                )
                if assistant_messages:
                    # Get the last (most recent) assistant message
                    response_text = assistant_messages[-1].text
                else:
                    # Fallback: look for message content
                    message_divs = self._driver.find_elements(By.CSS_SELECTOR, ".markdown, .prose")
                    if message_divs:
                        response_text = message_divs[-1].text
            except Exception as e:
                print(f"Error extracting response text: {e}")
            
            return {
                "status": "success",
                "data": [],
                "response_text": response_text,
                "html_content": html_content,
                "metadata": {
                    "source": "chatgpt",
                    "proxy_used": self.proxy,
                    "timestamp": timestamp,
                    "connectivity": connectivity_info
                }
            }
            
        except Exception as e:
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
                    "proxy_used": self.proxy,
                    "timestamp": timestamp,
                    "connectivity": connectivity_info if 'connectivity_info' in dir() else {}
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
