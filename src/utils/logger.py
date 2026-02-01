"""Minimal colored logging with timing, chain verification, and bandwidth tracking."""

import logging
import sys
import time
import socket
import json
import urllib.request
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from contextlib import contextmanager


class C:
    """ANSI color codes."""
    RST = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"


# Backward compatible alias
Colors = C


class Log:
    """Minimal logger with colors, timing, and job ID tracking."""
    
    _start_times: Dict[str, float] = {}
    _job_id: Optional[int] = None
    
    @classmethod
    def set_job(cls, job_id: int):
        """Set current job ID for log correlation."""
        cls._job_id = job_id
    
    @classmethod
    def clear_job(cls):
        """Clear job ID."""
        cls._job_id = None
    
    @staticmethod
    def _ts() -> str:
        return f"{C.DIM}{datetime.now().strftime('%H:%M:%S')}{C.RST}"
    
    @classmethod
    def _jid(cls) -> str:
        if cls._job_id:
            return f"{C.CYAN}[job:{cls._job_id}]{C.RST} "
        return ""
    
    @classmethod
    def _fmt(cls, icon: str, color: str, msg: str, elapsed: float = None) -> str:
        time_str = f" {C.DIM}({elapsed:.1f}s){C.RST}" if elapsed else ""
        return f"{cls._ts()} {cls._jid()}{color}{icon}{C.RST} {msg}{time_str}"
    
    @classmethod
    def step(cls, msg: str, key: str = None):
        """Action step (→). Optionally start timer with key."""
        if key:
            cls._start_times[key] = time.time()
        print(cls._fmt("→", C.CYAN, msg))
    
    @classmethod
    def ok(cls, msg: str, key: str = None):
        """Success (✓). Optionally show elapsed time for key."""
        elapsed = None
        if key and key in cls._start_times:
            elapsed = time.time() - cls._start_times.pop(key)
        print(cls._fmt("✓", C.GREEN, msg, elapsed))
    
    @classmethod
    def fail(cls, msg: str, key: str = None):
        """Failure (✗)."""
        elapsed = None
        if key and key in cls._start_times:
            elapsed = time.time() - cls._start_times.pop(key)
        print(cls._fmt("✗", C.RED, msg, elapsed))
    
    @classmethod
    def warn(cls, msg: str, key: str = None):
        """Warning (⚠)."""
        elapsed = None
        if key and key in cls._start_times:
            elapsed = time.time() - cls._start_times.pop(key)
        print(cls._fmt("⚠", C.YELLOW, msg, elapsed))
    
    @classmethod
    def info(cls, msg: str):
        """Info (○)."""
        print(cls._fmt("○", C.DIM, msg))
    
    @classmethod
    def data(cls, label: str, value: Any):
        """Data point."""
        print(f"{Log._ts()}   {C.MAGENTA}{label}:{C.RST} {value}")
    
    @classmethod
    def hop(cls, num: int, name: str, ip: str, loc: str, isp: str, ok: bool, extra: str = ""):
        """Network hop - compact single line."""
        icon = f"{C.GREEN}●{C.RST}" if ok else f"{C.RED}○{C.RST}"
        extra_str = f" {extra}" if extra else ""
        print(f"{Log._ts()} {icon} {C.BOLD}{name}{C.RST}: {C.WHITE}{ip}{C.RST} {C.DIM}({loc}){C.RST} {C.MAGENTA}{isp}{C.RST}{extra_str}")
    
    @classmethod
    def result(cls, ok: bool, msg: str):
        """Final result badge."""
        badge = f"{C.BG_GREEN} OK {C.RST}" if ok else f"{C.BG_RED} FAIL {C.RST}"
        print(f"{Log._ts()} {badge} {msg}")
    
    @classmethod
    def cost(cls, label: str, bytes_val: int, cost_usd: float):
        """Cost/bandwidth display."""
        size_str = format_bytes(bytes_val)
        cost_str = f"${cost_usd:.4f}" if cost_usd < 0.01 else f"${cost_usd:.2f}"
        print(f"{Log._ts()}   {C.YELLOW}${C.RST} {label}: {C.WHITE}{size_str}{C.RST} = {C.GREEN}{cost_str}{C.RST}")
    
    @classmethod
    @contextmanager
    def timed(cls, msg: str):
        """Context manager for timed operations."""
        start = time.time()
        print(cls._fmt("→", C.CYAN, msg))
        try:
            yield
        finally:
            elapsed = time.time() - start
            print(cls._fmt("✓", C.GREEN, msg, elapsed))


def format_bytes(b: int) -> str:
    """Format bytes to human readable."""
    if b < 1024:
        return f"{b} B"
    elif b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    elif b < 1024 * 1024 * 1024:
        return f"{b / (1024 * 1024):.2f} MB"
    else:
        return f"{b / (1024 * 1024 * 1024):.2f} GB"


@dataclass
class BandwidthTracker:
    """Track bandwidth usage and calculate BrightData costs.
    
    BrightData Residential Proxy Pricing (as of 2024):
    - Pay-as-you-go: ~$8.4/GB for residential
    - With commitment plans can be lower (~$5.04/GB)
    
    We use $8.4/GB as default (conservative estimate).
    """
    
    # Pricing per GB in USD (residential proxy)
    PRICE_PER_GB: float = 8.4
    
    # Running totals
    bytes_sent: int = 0
    bytes_received: int = 0
    requests_count: int = 0
    
    # Per-session tracking
    session_bytes_sent: int = 0
    session_bytes_received: int = 0
    session_requests: int = 0
    session_start: float = field(default_factory=time.time)
    
    def reset_session(self):
        """Reset session counters."""
        self.session_bytes_sent = 0
        self.session_bytes_received = 0
        self.session_requests = 0
        self.session_start = time.time()
    
    def add_request(self, sent: int = 0, received: int = 0):
        """Add a request's bandwidth."""
        self.bytes_sent += sent
        self.bytes_received += received
        self.requests_count += 1
        
        self.session_bytes_sent += sent
        self.session_bytes_received += received
        self.session_requests += 1
    
    def add_page_load(self, html_size: int, estimated_resources: int = 0):
        """Add bandwidth for a page load.
        
        Args:
            html_size: Size of HTML content
            estimated_resources: Estimated size of additional resources (JS, CSS, images)
        """
        # Request overhead (headers, etc) ~500 bytes sent per request
        sent = 500
        received = html_size + estimated_resources
        self.add_request(sent, received)
    
    @property
    def total_bytes(self) -> int:
        return self.bytes_sent + self.bytes_received
    
    @property
    def session_bytes(self) -> int:
        return self.session_bytes_sent + self.session_bytes_received
    
    @property
    def total_cost(self) -> float:
        """Total cost in USD."""
        gb = self.total_bytes / (1024 * 1024 * 1024)
        return gb * self.PRICE_PER_GB
    
    @property
    def session_cost(self) -> float:
        """Session cost in USD."""
        gb = self.session_bytes / (1024 * 1024 * 1024)
        return gb * self.PRICE_PER_GB
    
    def estimate_from_html(self, html: str) -> Dict[str, Any]:
        """Estimate bandwidth from HTML content.
        
        Estimates total page weight based on HTML size.
        Typical ratios: HTML is ~10-15% of total page weight.
        """
        html_bytes = len(html.encode('utf-8')) if html else 0
        
        # Estimate total resources (conservative: HTML is ~20% of total)
        # This accounts for JS, CSS, fonts, images loaded
        estimated_total = html_bytes * 5  # 5x multiplier
        
        return {
            "html_bytes": html_bytes,
            "estimated_total": estimated_total,
            "estimated_resources": estimated_total - html_bytes,
        }
    
    def log_session(self):
        """Log session bandwidth and cost."""
        if self.session_bytes == 0:
            return
        
        Log.data("Requests", self.session_requests)
        Log.cost("Bandwidth", self.session_bytes, self.session_cost)
    
    def log_total(self):
        """Log total bandwidth and cost."""
        if self.total_bytes == 0:
            return
        
        print(f"\n{C.YELLOW}{C.BOLD}Bandwidth Summary{C.RST}")
        Log.data("Total requests", self.requests_count)
        Log.cost("Total bandwidth", self.total_bytes, self.total_cost)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get stats dict for metadata."""
        return {
            "session_bytes_sent": self.session_bytes_sent,
            "session_bytes_received": self.session_bytes_received,
            "session_total_bytes": self.session_bytes,
            "session_requests": self.session_requests,
            "session_cost_usd": round(self.session_cost, 6),
            "total_bytes": self.total_bytes,
            "total_requests": self.requests_count,
            "total_cost_usd": round(self.total_cost, 6),
            "price_per_gb_usd": self.PRICE_PER_GB,
        }


# Global bandwidth tracker instance
bandwidth = BandwidthTracker()


class ScraperLogger:
    """Wrapper for backward compatibility."""
    
    def __init__(self, name: str = "scraper"):
        self.name = name
    
    def step(self, msg: str): Log.step(msg)
    def ok(self, msg: str): Log.ok(msg)
    def fail(self, msg: str): Log.fail(msg)
    def warn(self, msg: str): Log.warn(msg)
    def info(self, msg: str): Log.info(msg)
    def debug(self, msg: str): Log.info(msg)
    def data(self, label: str, value: Any): Log.data(label, value)
    def section(self, title: str): print(f"\n{C.CYAN}{C.BOLD}{title}{C.RST}")
    def result(self, ok: bool, msg: str): Log.result(ok, msg)
    def chain_hop(self, num: int, name: str, ip: str, loc: str, ok: bool): Log.hop(num, name, ip, loc, ok)


@dataclass
class IPInfo:
    """IP geolocation data."""
    ip: str = ""
    country: str = ""
    country_code: str = ""
    city: str = ""
    isp: str = ""
    is_residential: bool = True
    error: Optional[str] = None


class ChainConnectivityChecker:
    """Verify network chain: VPN → Proxy → Target."""
    
    IP_API = "http://ip-api.com/json/?fields=status,query,country,countryCode,city,isp,proxy,hosting"
    
    def __init__(self, logger: Optional[ScraperLogger] = None):
        pass
    
    def _get_ip_direct(self, timeout: float = 5.0, proxy: str = None) -> IPInfo:
        """Get IP via direct request. Can optionally use a proxy."""
        import os
        try:
            # Try multiple IP services
            services = [
                ("https://ipinfo.io/json", lambda d: (d.get("ip"), d.get("country"), d.get("city"), d.get("org"))),
                ("https://api.ipify.org?format=json", lambda d: (d.get("ip"), "", "", "")),
                (self.IP_API, lambda d: (d.get("query"), d.get("countryCode"), d.get("city"), d.get("isp")) if d.get("status") == "success" else None),
            ]
            
            # Use proxy from environment or parameter
            proxy_url = proxy or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
            
            for url, parser in services:
                try:
                    if proxy_url:
                        # Use requests library with proxy
                        import requests
                        resp = requests.get(url, proxies={"http": proxy_url, "https": proxy_url}, timeout=timeout)
                        d = resp.json()
                    else:
                        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
                        with urllib.request.urlopen(req, timeout=timeout) as resp:
                            d = json.loads(resp.read().decode())
                    
                    result = parser(d)
                    if result and result[0]:
                        ip, country, city, isp = result
                        return IPInfo(
                            ip=ip,
                            country_code=country,
                            city=city,
                            isp=isp,
                            is_residential=True,
                        )
                except:
                    continue
                    
        except Exception as e:
            return IPInfo(error=str(e))
        return IPInfo(error="lookup failed")
    
    def _get_ip_browser(self, driver) -> IPInfo:
        """Get IP via browser (through proxy). Try multiple services."""
        # List of IP lookup services to try
        services = [
            ("https://ipinfo.io/json", lambda d: IPInfo(
                ip=d.get("ip", ""),
                country=d.get("country", ""),
                country_code=d.get("country", ""),
                city=d.get("city", ""),
                isp=d.get("org", ""),
                is_residential=True,  # ipinfo doesn't provide this
            )),
            ("https://api.ipify.org?format=json", lambda d: IPInfo(
                ip=d.get("ip", ""),
                country_code="",
                city="",
                isp="",
                is_residential=True,
            )),
            (self.IP_API, lambda d: IPInfo(
                ip=d.get("query", ""),
                country=d.get("country", ""),
                country_code=d.get("countryCode", ""),
                city=d.get("city", ""),
                isp=d.get("isp", ""),
                is_residential=not (d.get("proxy") or d.get("hosting")),
            ) if d.get("status") == "success" else None),
        ]
        
        for url, parser in services:
            try:
                driver.get(url)
                time.sleep(2)
                body = driver.find_element("tag name", "body").text
                
                # Track bandwidth
                bandwidth.add_request(sent=500, received=len(body.encode('utf-8')))
                
                # Try to parse JSON
                d = json.loads(body)
                result = parser(d)
                if result and result.ip:
                    return result
            except Exception:
                continue
        
        return IPInfo(error="all IP lookups failed")
    
    def _check_vpn(self, expected_country: Optional[str] = None, vpn_proxy: str = None) -> Dict[str, Any]:
        """Check VPN exit IP."""
        start = time.time()
        if not vpn_proxy and expected_country:
            vpn_proxy = f"http://vpn-{expected_country.lower()}:8888"
        
        info = self._get_ip_direct(proxy=vpn_proxy)
        elapsed = time.time() - start
        
        result = {"success": bool(info.ip), "ip": info.ip, "country_code": info.country_code,
                  "city": info.city, "isp": info.isp, "country_match": None, "elapsed": elapsed}
        
        if expected_country and info.country_code:
            result["country_match"] = info.country_code.upper() == expected_country.upper()
        
        return result
    
    def _check_proxy(self, driver, expected_country: Optional[str] = None) -> Dict[str, Any]:
        """Check proxy exit IP via browser."""
        start = time.time()
        info = self._get_ip_browser(driver)
        elapsed = time.time() - start
        
        result = {"success": bool(info.ip), "ip": info.ip, "country_code": info.country_code,
                  "city": info.city, "isp": info.isp, "is_residential": info.is_residential,
                  "country_match": None, "elapsed": elapsed}
        
        if expected_country and info.country_code:
            result["country_match"] = info.country_code.upper() == expected_country.upper()
        
        return result
    
    def verify_full_chain(
        self,
        driver,
        vpn_country: Optional[str] = None,
        proxy_country: Optional[str] = None,
        take_screenshot=None,
        vpn_proxy: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify chain: VPN → Proxy. Compact 3-line output."""
        country = vpn_country or proxy_country
        
        # Check both layers
        vpn = self._check_vpn(country, vpn_proxy)
        proxy = self._check_proxy(driver, country)
        
        # Determine chain validity
        chain_valid = proxy["success"]
        ips_differ = vpn["success"] and proxy["success"] and vpn.get("ip") != proxy.get("ip")
        
        # Line 1: VPN
        vpn_loc = f"{vpn.get('city', '')}, {vpn.get('country_code', '?')}" if vpn.get('city') else vpn.get('country_code', '?')
        vpn_check = f"{C.GREEN}✓{C.RST}" if vpn.get("country_match", True) else f"{C.RED}✗{C.RST}"
        if vpn["success"]:
            print(f"{Log._ts()} {C.GREEN}●{C.RST} VPN:   {C.WHITE}{vpn['ip']}{C.RST} {C.DIM}{vpn_loc}{C.RST} {vpn_check} {C.DIM}({vpn['elapsed']:.1f}s){C.RST}")
        else:
            print(f"{Log._ts()} {C.RED}○{C.RST} VPN:   {C.RED}failed{C.RST}")
        
        # Line 2: Proxy
        proxy_loc = f"{proxy.get('city', '')}, {proxy.get('country_code', '?')}" if proxy.get('city') else proxy.get('country_code', '?')
        proxy_check = f"{C.GREEN}✓{C.RST}" if proxy.get("country_match", True) else f"{C.RED}✗{C.RST}"
        res_tag = "" if proxy.get("is_residential", True) else f" {C.YELLOW}[DC]{C.RST}"
        if proxy["success"]:
            print(f"{Log._ts()} {C.GREEN}●{C.RST} Proxy: {C.WHITE}{proxy['ip']}{C.RST} {C.DIM}{proxy_loc}{C.RST}{res_tag} {proxy_check} {C.DIM}({proxy['elapsed']:.1f}s){C.RST}")
        else:
            print(f"{Log._ts()} {C.RED}○{C.RST} Proxy: {C.RED}failed{C.RST}")
        
        # Line 3: Chain status
        if ips_differ:
            print(f"{Log._ts()} {C.GREEN}✓{C.RST} Chain: {C.GREEN}VPN → Proxy (IPs differ){C.RST}")
        elif vpn["success"] and proxy["success"]:
            print(f"{Log._ts()} {C.YELLOW}○{C.RST} Chain: {C.YELLOW}same IP (no residential proxy?){C.RST}")
        elif proxy["success"]:
            print(f"{Log._ts()} {C.GREEN}✓{C.RST} Chain: {C.GREEN}Proxy ok{C.RST}")
        else:
            print(f"{Log._ts()} {C.RED}✗{C.RST} Chain: {C.RED}failed{C.RST}")
        
        if take_screenshot:
            take_screenshot("chain")
        
        return {"chain_valid": chain_valid, "vpn": vpn, "proxy": proxy}
    
    # Backward compat aliases
    def verify_vpn_layer(self, expected_country=None, vpn_proxy=None):
        return self._check_vpn(expected_country, vpn_proxy)
    
    def verify_proxy_layer(self, driver, expected_country=None):
        return self._check_proxy(driver, expected_country)


# Backward compatible alias
FastConnectivityChecker = ChainConnectivityChecker


def setup_logging(level: str = "INFO") -> None:
    """Configure logging."""
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        level=getattr(logging, level.upper()),
    )


def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)
