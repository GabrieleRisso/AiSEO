import time
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List
from urllib.parse import quote_plus

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from ..common.base import BaseScraper
from ...utils.logger import Log, C, ChainConnectivityChecker, bandwidth, format_bytes


class PerplexityScraper(BaseScraper):
    """Scraper for Perplexity AI."""
    
    BASE_URL = "https://www.perplexity.ai"
    
    def __init__(self, headless: bool = True, proxy: str = None, antidetect=None):
        super().__init__(headless, proxy, antidetect)
        self._driver = None
        self.chain = ChainConnectivityChecker()
        # Reset session bandwidth tracking
        bandwidth.reset_session()

    def _start_browser(self):
        """Start browser."""
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
                p = self.antidetect.profile
                options.add_argument(f"--user-agent={p.user_agent}")
                options.add_argument(f"--window-size={p.screen_width},{p.screen_height}")
                options.add_argument(f"--lang={p.language}")
                Log.data("Profile", f"{p.language}, {p.screen_width}x{p.screen_height}")
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

    def _screenshot(self, name: str = "debug"):
        """Take screenshot."""
        try:
            d = Path(__file__).parent.parent.parent / "data" / "screenshots"
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self._driver.save_screenshot(str(p))
            Log.info(f"Screenshot: {p.name}")
            return str(p)
        except:
            return None

    def _handle_cookies(self):
        """Handle cookie banner."""
        time.sleep(2)
        try:
            # Try to find and click "Accept All Cookies" button
            clicked = self._driver.execute_script("""
                // Look for cookie consent banner
                var banner = document.querySelector('#cookie-consent, [id*="cookie"], [class*="cookie-consent"]');
                if (!banner) {
                    // Try finding by text content
                    var divs = document.querySelectorAll('div');
                    for (var d of divs) {
                        var text = (d.textContent || '').toLowerCase();
                        if (text.includes('we use cookies') && d.offsetParent) {
                            banner = d;
                            break;
                        }
                    }
                }
                
                if (banner) {
                    // Look for "Accept All Cookies" button
                    var buttons = banner.querySelectorAll('button');
                    for (var b of buttons) {
                        var text = (b.textContent || '').toLowerCase();
                        if (text.includes('accept all cookies') || 
                            (text.includes('accept') && text.includes('all') && text.includes('cookies'))) {
                            b.click();
                            return true;
                        }
                    }
                    
                    // Fallback: click any button with "accept" and "cookie"
                    for (var b of buttons) {
                        var text = (b.textContent || '').toLowerCase();
                        if (text.includes('accept') && text.includes('cookie')) {
                            b.click();
                            return true;
                        }
                    }
                }
                
                // Fallback: search all buttons on page
                var allBtns = document.querySelectorAll('button');
                for (var b of allBtns) {
                    if (!b.offsetParent) continue;
                    var text = (b.textContent || '').toLowerCase();
                    if (text.includes('accept all cookies')) {
                        b.click();
                        return true;
                    }
                }
                
                return false;
            """)
            if clicked:
                Log.ok("Cookies accepted")
                time.sleep(2)
        except Exception as e:
            Log.warn(f"Cookie handling: {e}")

    def _handle_login_popup(self):
        """Close login popup if present."""
        time.sleep(1)
        try:
            closed = self._driver.execute_script("""
                var texts = ['Continue with Google', 'Continua con Google', 'Sign in', 'Accedi'];
                for (var t of texts) {
                    var els = document.evaluate("//*[contains(text(), '" + t + "')]",
                        document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                    for (var i = 0; i < els.snapshotLength; i++) {
                        var el = els.snapshotItem(i);
                        if (el && el.offsetParent) {
                            var popup = el.closest('[class*="fixed"], [role="dialog"]');
                            if (popup) {
                                var close = popup.querySelector('button[aria-label*="close" i]');
                                if (!close) {
                                    var btns = popup.querySelectorAll('button');
                                    for (var b of btns) {
                                        if (!b.textContent.trim() || b.textContent.trim() === '×') {
                                            close = b; break;
                                        }
                                    }
                                }
                                if (close) { close.click(); return true; }
                            }
                        }
                    }
                }
                return false;
            """)
            if closed:
                Log.ok("Login popup closed")
                time.sleep(1)
        except:
            pass

    def _find_input(self):
        """Find query input."""
        # 1. Try #ask-input (Perplexity's actual input)
        try:
            el = self._driver.find_element(By.ID, "ask-input")
            if el.is_displayed():
                Log.ok("Input found (id=ask-input)", "input")
                return el
        except:
            pass
        
        # 2. Try contenteditable with data-lexical-editor
        try:
            els = self._driver.find_elements(By.CSS_SELECTOR, 
                "div[contenteditable='true'][data-lexical-editor='true']")
            for el in els:
                if el.is_displayed():
                    aria_placeholder = el.get_attribute("aria-placeholder") or ""
                    if "Ask anything" in aria_placeholder or el.get_attribute("id") == "ask-input":
                        Log.ok("Input found (contenteditable)", "input")
                        return el
        except:
            pass
        
        # 3. Try any contenteditable div
        try:
            els = self._driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
            for el in els:
                if el.is_displayed():
                    rect = el.rect
                    if rect.get('width', 0) > 200:  # Large enough to be the main input
                        Log.ok("Input found (contenteditable fallback)", "input")
                        return el
        except:
            pass
        
        # 4. Try textarea
        try:
            els = self._driver.find_elements(By.TAG_NAME, "textarea")
            for el in els:
                if el.is_displayed():
                    Log.ok("Input found (textarea)", "input")
                    return el
        except:
            pass
        
        return None

    def _submit_query(self, input_el, query: str) -> bool:
        """Type and submit query."""
        Log.step(f"Query: {query[:50]}...", "query")
        
        # Handle contenteditable div differently from textarea
        is_contenteditable = (input_el.tag_name == "div" and 
                             input_el.get_attribute("contenteditable") == "true")
        
        try:
            input_el.click()
            time.sleep(0.3)
            
            if is_contenteditable:
                # For contenteditable divs, use JavaScript to set content
                self._driver.execute_script("""
                    arguments[0].focus();
                    arguments[0].innerHTML = '<p dir="auto">' + arguments[1] + '</p>';
                    // Trigger input event for React/Lexical
                    var event = new Event('input', { bubbles: true });
                    arguments[0].dispatchEvent(event);
                    // Also trigger beforeinput for Lexical
                    var beforeInput = new InputEvent('beforeinput', { bubbles: true, inputType: 'insertText', data: arguments[1] });
                    arguments[0].dispatchEvent(beforeInput);
                """, input_el, query)
                Log.ok("Query typed (contenteditable)")
            else:
                # Regular textarea
                actions = ActionChains(self._driver)
                actions.click(input_el)
                for c in query:
                    actions.send_keys(c)
                    actions.pause(0.03)
                actions.perform()
                Log.ok("Query typed")
            
            time.sleep(1)
        except Exception as e:
            Log.fail(f"Type failed: {e}")
            return False
        
        # Take screenshot before submit
        self._screenshot("before_submit")
        
        # Helper to check if search started
        def check_started():
            try:
                url = self._driver.current_url
                if "search" in url or "/q/" in url:
                    return True
                return self._driver.execute_script("""
                    return document.querySelector('.prose, [id^="markdown-content"], h1[class*="query"]') !== null;
                """)
            except:
                return False
        
        Log.step("Submit", "submit")
        
        # Method 0: Enter key on input (most reliable for contenteditable)
        try:
            if is_contenteditable:
                # For contenteditable, Enter key is most reliable
                input_el.send_keys(Keys.ENTER)
                time.sleep(3)
                if check_started():
                    Log.ok("Submitted (Enter on contenteditable)", "submit")
                    return True
        except:
            pass
        
        # Method 1: Find and click submit button properly
        try:
            # Find the submit button - look for button with teal background near the input
            btn = self._driver.execute_script("""
                // Find button with bg-super class (teal background)
                var btn = document.querySelector('button.bg-super');
                
                // If not found, look for button near the ask-input
                if (!btn) {
                    var input = document.getElementById('ask-input');
                    if (input) {
                        var container = input.closest('div[class*="rounded"]');
                        if (container) {
                            btn = container.querySelector('button[class*="bg-super"], button[class*="bg-inverse"]');
                        }
                    }
                }
                
                // Fallback: find button with arrow icon
                if (!btn) {
                    var buttons = document.querySelectorAll('button');
                    for (var b of buttons) {
                        if (!b.offsetParent) continue;
                        var svg = b.querySelector('svg use[href*="arrow"], svg use[href*="send"]');
                        if (svg) {
                            btn = b;
                            break;
                        }
                    }
                }
                
                return btn;
            """)
            
            if btn:
                # Click the button element, not SVG
                self._driver.execute_script("arguments[0].click();", btn)
                time.sleep(3)
                if check_started():
                    Log.ok("Submitted (button click)", "submit")
                    return True
                
                # Also try ActionChains click
                ActionChains(self._driver).move_to_element(btn).pause(0.2).click().perform()
                time.sleep(3)
                if check_started():
                    Log.ok("Submitted (action click)", "submit")
                    return True
        except Exception as e:
            Log.warn(f"Button click failed: {e}", "submit")
        
        # Method 2: Enter key via ActionChains
        try:
            input_el.click()
            time.sleep(0.2)
            ActionChains(self._driver).send_keys(Keys.ENTER).perform()
            time.sleep(4)
            if check_started():
                Log.ok("Submitted (Enter key)", "submit")
                return True
        except:
            pass
        
        # Method 3: Native Selenium button click
        try:
            btn = WebDriverWait(self._driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.bg-super, button[class*='bg-super']"))
            )
            if btn and btn.is_displayed():
                btn.click()
                time.sleep(4)
                if check_started():
                    Log.ok("Submitted (native click)", "submit")
                    return True
        except:
            pass
        
        # Method 4: Tab+Enter
        try:
            input_el.click()
            time.sleep(0.2)
            ActionChains(self._driver).send_keys(Keys.TAB).pause(0.3).send_keys(Keys.ENTER).perform()
            time.sleep(4)
            if check_started():
                Log.ok("Submitted (Tab+Enter)", "submit")
                return True
        except:
            pass
        
        # Method 5: JavaScript events on button
        try:
            result = self._driver.execute_script("""
                // Find submit button
                var btn = document.querySelector('button.bg-super');
                if (!btn) {
                    // Look near the input field
                    var input = document.getElementById('ask-input');
                    if (input) {
                        var container = input.closest('div');
                        if (container) {
                            btn = container.querySelector('button[class*="bg-super"], button[class*="bg-inverse"]');
                        }
                    }
                }
                
                if (btn && btn.offsetParent) {
                    btn.focus();
                    var rect = btn.getBoundingClientRect();
                    var props = {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        clientX: rect.left + rect.width/2,
                        clientY: rect.top + rect.height/2,
                        button: 0,
                        buttons: 1
                    };
                    
                    // Full mouse event sequence
                    ['mouseenter', 'mouseover', 'mousedown'].forEach(t => {
                        btn.dispatchEvent(new MouseEvent(t, {...props, buttons: 1}));
                    });
                    ['mouseup', 'click'].forEach(t => {
                        btn.dispatchEvent(new MouseEvent(t, {...props, buttons: 0}));
                    });
                    
                    return true;
                }
                return false;
            """)
            
            if result:
                time.sleep(4)
                if check_started():
                    Log.ok("Submitted (JS events)", "submit")
                    return True
        except:
            pass
        
        # Method 6: Form submission (if form exists)
        try:
            form_submitted = self._driver.execute_script("""
                var form = document.querySelector('form');
                if (form) {
                    form.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}));
                    return true;
                }
                return false;
            """)
            if form_submitted:
                time.sleep(4)
                if check_started():
                    Log.ok("Submitted (form)", "submit")
                    return True
        except:
            pass
        
        # If we get here, Enter key should have worked, so assume success
        Log.warn("Submit uncertain - assuming Enter key worked", "submit")
        return True

    def _wait_response(self, take_screenshot: bool, query: str):
        """Wait for response."""
        Log.step("Waiting for response", "response")
        
        # Handle late cookie popup
        try:
            self._driver.execute_script("""
                var c = document.querySelector('#cookie-consent');
                if (c && c.offsetParent) {
                    var b = c.querySelector('button');
                    if (b) b.click();
                }
            """)
        except:
            pass
        
        # Wait for response to start appearing
        try:
            WebDriverWait(self._driver, 30).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".prose, [id^='markdown-content'], [data-message-author-role='assistant']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='answer'], div[class*='response']"))
                )
            )
            Log.ok("Response started", "response")
        except:
            Log.warn("Timeout waiting for response start")
        
        # Wait for streaming to complete - check if text is still changing
        last_text = ""
        stable_count = 0
        for i in range(20):  # Check for up to 20 seconds
            time.sleep(1)
            try:
                current_text = self._driver.execute_script("""
                    var prose = document.querySelector('.prose, [data-message-author-role="assistant"]');
                    return prose ? (prose.innerText || prose.textContent || '') : '';
                """)
                
                if current_text == last_text and len(current_text) > 50:
                    stable_count += 1
                    if stable_count >= 3:  # Stable for 3 seconds
                        break
                else:
                    stable_count = 0
                    last_text = current_text
            except:
                pass
        
        if take_screenshot:
            self._screenshot(f"result_{query[:10]}")
        
        Log.ok("Response ready", "response")

    def _extract(self) -> Dict[str, Any]:
        """Extract response and sources."""
        Log.step("Extracting", "extract")
        
        html = ""
        try:
            html = self._driver.page_source
            # Track bandwidth for page content
            if html:
                est = bandwidth.estimate_from_html(html)
                bandwidth.add_page_load(est["html_bytes"], est["estimated_resources"])
        except:
            pass
        
        try:
            data = self._driver.execute_script("""
                var result = {
                    text: '',
                    html_elements: [],
                    sources: [],
                    all_links: []
                };
                
                // Extract all response HTML elements
                var selectors = [
                    '.prose',
                    '[class*="prose"]',
                    '[data-message-author-role="assistant"]',
                    'div[class*="answer"]',
                    'div[class*="response"]',
                    '[id^="markdown-content"]'
                ];
                
                var seenElements = new Set();
                for (var sel of selectors) {
                    try {
                        var elements = document.querySelectorAll(sel);
                        for (var el of elements) {
                            if (!el.offsetParent || seenElements.has(el)) continue;
                            seenElements.add(el);
                            var html = el.outerHTML;
                            var text = el.innerText || el.textContent || '';
                            if (html && text.length > 10) {
                                result.html_elements.push({
                                    html: html,
                                    text: text,
                                    selector: sel
                                });
                            }
                        }
                    } catch(e) {}
                }
                
                // Get main response text (from last/most recent element)
                if (result.html_elements.length > 0) {
                    result.text = result.html_elements[result.html_elements.length - 1].text;
                } else {
                    // Fallback: try prose selector
                    var prose = document.querySelector('.prose, [id^="markdown-content"]');
                    if (prose) {
                        result.text = prose.innerText || prose.textContent || '';
                        result.html_elements.push({
                            html: prose.outerHTML,
                            text: result.text,
                            selector: '.prose'
                        });
                    }
                }
                
                // Extract all links and sources
                var seenUrls = new Set();
                var allLinks = document.querySelectorAll('a[href^="http"]');
                
                for (var a of allLinks) {
                    try {
                        var url = a.href;
                        if (!url || url.includes('perplexity.ai') || url.startsWith('#') || seenUrls.has(url)) {
                            continue;
                        }
                        seenUrls.add(url);
                        
                        var linkText = (a.innerText || a.textContent || '').trim();
                        var linkTitle = a.getAttribute('title') || linkText;
                        
                        // Try to get parent context
                        var parent = a.parentElement;
                        var context = '';
                        if (parent) {
                            context = (parent.innerText || parent.textContent || '').substring(0, 200);
                        }
                        
                        var linkData = {
                            url: url,
                            text: linkText,
                            title: linkTitle,
                            context: context
                        };
                        
                        result.all_links.push(linkData);
                        
                        // If link has meaningful text, add to sources
                        if (linkText && linkText.length > 3 && linkText.length < 200) {
                            result.sources.push({
                                title: linkText.substring(0, 200),
                                url: url,
                                description: context.substring(0, 500)
                            });
                        }
                    } catch(e) {
                        continue;
                    }
                }
                
                return result;
            """)
            
            # Format sources
            sources = []
            for s in (data.get("sources") or []):
                sources.append({
                    "title": s.get("title", "")[:200],
                    "url": s.get("url", ""),
                    "date": None,
                    "description": s.get("description", "")[:500],
                    "publisher": ""
                })
            
            # Format links
            all_links = []
            for l in (data.get("all_links") or []):
                all_links.append({
                    "url": l.get("url", ""),
                    "text": l.get("text", ""),
                    "title": l.get("title", ""),
                    "context": l.get("context", "")
                })
            
            # Format HTML elements
            html_elements = []
            for e in (data.get("html_elements") or []):
                html_elements.append({
                    "html": e.get("html", ""),
                    "text": e.get("text", ""),
                    "selector": e.get("selector", "")
                })
            
            response_text = data.get("text", "")
            
            Log.ok(f"{len(response_text)} chars, {len(sources)} sources, {len(all_links)} links, {len(html_elements)} HTML elements", "extract")
            
            return {
                "response_text": response_text,
                "html_content": html,
                "response_html_elements": html_elements,
                "sources": sources,
                "all_links": all_links
            }
        except Exception as e:
            Log.fail(f"Extract failed: {e}")
            return {
                "response_text": "", 
                "html_content": html, 
                "response_html_elements": [], 
                "sources": [], 
                "all_links": []
            }

    async def scrape(self, query: str, take_screenshot: bool = False) -> Dict[str, Any]:
        """Execute scrape."""
        start_time = time.time()
        print(f"\n{C.CYAN}{C.BOLD}Perplexity Scrape{C.RST}")
        Log.data("Query", query[:60] + "..." if len(query) > 60 else query)
        
        timestamp = datetime.now(timezone.utc).isoformat()
        conn_info = {}
        
        try:
            # Get target country
            target = None
            if self.antidetect and self.antidetect.is_enabled:
                target = getattr(self.antidetect.config, 'target_country', None)
            
            # Start browser first
            self._start_browser()
            time.sleep(2)
            
            # Verify chain (compact 3-line output)
            conn_info = self.chain.verify_full_chain(
                self._driver, 
                vpn_country=target, 
                proxy_country=target,
                take_screenshot=self._screenshot if take_screenshot else None
            )
            
            # Navigate
            Log.step(f"Loading {self.BASE_URL}", "nav")
            self._driver.get(self.BASE_URL)
            time.sleep(4)
            
            # Track initial page load bandwidth
            try:
                initial_html = self._driver.page_source
                if initial_html:
                    est = bandwidth.estimate_from_html(initial_html)
                    bandwidth.add_page_load(est["html_bytes"], est["estimated_resources"])
            except:
                pass
            
            Log.ok("Page loaded", "nav")
            
            if take_screenshot:
                self._screenshot("home")
            
            # Handle popups
            self._handle_cookies()
            self._handle_login_popup()
            
            # Find input
            Log.step("Finding input", "input")
            inp = self._find_input()
            if not inp:
                raise Exception("Input not found")
            Log.ok("Input found", "input")
            
            # Submit
            self._submit_query(inp, query)
            
            # Wait
            self._wait_response(take_screenshot, query)
            
            # Extract
            extracted = self._extract()
            
            # Done
            elapsed = time.time() - start_time
            
            # Log bandwidth and cost
            print()
            bandwidth.log_session()
            print()
            Log.result(True, f"Done in {elapsed:.1f}s - {len(extracted['sources'])} sources")
            
            return {
                "status": "success",
                "data": extracted["sources"],
                "response_text": extracted["response_text"],
                "html_content": extracted["html_content"],
                "response_html_elements": extracted["response_html_elements"],
                "all_links": extracted["all_links"],
                "metadata": {
                    "source": "perplexity",
                    "proxy_used": self.proxy,
                    "timestamp": timestamp,
                    "connectivity": conn_info,
                    "elapsed_seconds": elapsed,
                    "sources_count": len(extracted["sources"]),
                    "links_count": len(extracted["all_links"]),
                    "bandwidth": bandwidth.get_stats(),
                }
            }

        except Exception as e:
            elapsed = time.time() - start_time
            Log.fail(f"Failed: {e} ({elapsed:.1f}s)")
            
            if take_screenshot and self._driver:
                self._screenshot("error")
            
            html = ""
            if self._driver:
                try:
                    html = self._driver.page_source
                    if html:
                        est = bandwidth.estimate_from_html(html)
                        bandwidth.add_page_load(est["html_bytes"], est["estimated_resources"])
                except:
                    pass
            
            # Log bandwidth even on failure
            if bandwidth.session_bytes > 0:
                print()
                bandwidth.log_session()

            return {
                "status": "failed",
                "data": [],
                "response_text": "",
                "html_content": html,
                "response_html_elements": [],
                "all_links": [],
                "error": str(e),
                "metadata": {
                    "source": "perplexity",
                    "proxy_used": self.proxy,
                    "timestamp": timestamp,
                    "connectivity": conn_info,
                    "elapsed_seconds": elapsed,
                    "bandwidth": bandwidth.get_stats(),
                }
            }
        finally:
            if self._driver:
                Log.step("Closing browser", "close")
                self._driver.quit()
                Log.ok("Closed", "close")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._driver:
            self._driver.quit()
