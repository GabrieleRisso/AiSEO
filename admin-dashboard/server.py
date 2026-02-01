"""
Admin Dashboard Server with configurable API endpoints.
Serves static files, config endpoint, and proxies requests to scraper API.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import json
import urllib.request
import urllib.error

PORT = int(os.getenv('PORT', 9091))
API_BASE = os.getenv('API_BASE_URL', 'http://localhost:8000')
SCRAPER_API = os.getenv('SCRAPER_API_URL', 'http://localhost:5000')
VPN_DASHBOARD = os.getenv('VPN_DASHBOARD_URL', 'http://localhost:9090')

class ConfigHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def proxy_to_scraper(self, path):
        """Proxy request to scraper API"""
        try:
            url = f"{SCRAPER_API}{path}"
            req = urllib.request.Request(url, headers={'User-Agent': 'AdminDashboard/1.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e), 'code': e.code}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_GET(self):
        # Serve config endpoint
        if self.path == '/config.json':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            config = {
                'API_BASE': API_BASE,
                'SCRAPER_API': '/proxy/scraper',  # Use local proxy instead of direct (avoids mixed content)
                'SCRAPER_API_DISPLAY': SCRAPER_API,  # Actual URL for display purposes
                'VPN_DASHBOARD': VPN_DASHBOARD
            }
            self.wfile.write(json.dumps(config).encode())
            return
        
        # Serve health endpoint
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
        
        # Proxy requests to scraper API (avoids HTTPS mixed content issues)
        if self.path.startswith('/proxy/scraper'):
            scraper_path = self.path.replace('/proxy/scraper', '')
            if not scraper_path:
                scraper_path = '/'
            self.proxy_to_scraper(scraper_path)
            return
        
        # Serve static files
        return super().do_GET()
    
    def do_POST(self):
        # Proxy POST requests to scraper API
        if self.path.startswith('/proxy/scraper'):
            scraper_path = self.path.replace('/proxy/scraper', '')
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length else None
            try:
                url = f"{SCRAPER_API}{scraper_path}"
                req = urllib.request.Request(url, data=post_data, headers={
                    'User-Agent': 'AdminDashboard/1.0',
                    'Content-Type': self.headers.get('Content-Type', 'application/json')
                })
                with urllib.request.urlopen(req, timeout=30) as response:
                    data = response.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(data)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f'Admin Dashboard starting on http://0.0.0.0:{PORT}')
    print(f'  API_BASE: {API_BASE}')
    print(f'  SCRAPER_API: {SCRAPER_API}')
    print(f'  VPN_DASHBOARD: {VPN_DASHBOARD}')
    server = HTTPServer(('0.0.0.0', PORT), ConfigHandler)
    server.serve_forever()
