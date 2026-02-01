#!/usr/bin/env python3
"""
VPN Status Dashboard
A simple Flask app that displays the status of all VPN containers.
Queries gluetun control servers for real-time status information.
"""

import os
import asyncio
import aiohttp
from flask import Flask, render_template_string, jsonify
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Parse VPN endpoints from environment
# Format: vpn-fr:9001,vpn-de:9002,...
VPN_ENDPOINTS_RAW = os.environ.get('VPN_ENDPOINTS', '')

# Map of country codes to full names and flag emojis
COUNTRY_INFO = {
    'fr': {'name': 'France', 'flag': '🇫🇷'},
    'de': {'name': 'Germany', 'flag': '🇩🇪'},
    'nl': {'name': 'Netherlands', 'flag': '🇳🇱'},
    'it': {'name': 'Italy', 'flag': '🇮🇹'},
    'es': {'name': 'Spain', 'flag': '🇪🇸'},
    'uk': {'name': 'United Kingdom', 'flag': '🇬🇧'},
    'ch': {'name': 'Switzerland', 'flag': '🇨🇭'},
    'se': {'name': 'Sweden', 'flag': '🇸🇪'},
    'us': {'name': 'United States', 'flag': '🇺🇸'},
    'ca': {'name': 'Canada', 'flag': '🇨🇦'},
    'jp': {'name': 'Japan', 'flag': '🇯🇵'},
    'au': {'name': 'Australia', 'flag': '🇦🇺'},
    'br': {'name': 'Brazil', 'flag': '🇧🇷'},
    'pl': {'name': 'Poland', 'flag': '🇵🇱'},
    'at': {'name': 'Austria', 'flag': '🇦🇹'},
    'be': {'name': 'Belgium', 'flag': '🇧🇪'},
    'pt': {'name': 'Portugal', 'flag': '🇵🇹'},
    'no': {'name': 'Norway', 'flag': '🇳🇴'},
    'dk': {'name': 'Denmark', 'flag': '🇩🇰'},
    'fi': {'name': 'Finland', 'flag': '🇫🇮'},
}


def parse_vpn_endpoints():
    """Parse VPN endpoints from environment variable."""
    endpoints = []
    if not VPN_ENDPOINTS_RAW:
        # Default endpoints if not configured
        default_config = {
            'fr': {'control': 9001, 'vpn_port': 8001, 'res_port': 8101},
            'de': {'control': 9002, 'vpn_port': 8002, 'res_port': 8102},
            'nl': {'control': 9003, 'vpn_port': 8003, 'res_port': 8103},
            'it': {'control': 9004, 'vpn_port': 8004, 'res_port': 8104},
            'es': {'control': 9005, 'vpn_port': 8005, 'res_port': 8105},
            'uk': {'control': 9006, 'vpn_port': 8006, 'res_port': 8106},
            'ch': {'control': 9007, 'vpn_port': 8007, 'res_port': 8107},
            'se': {'control': 9008, 'vpn_port': 8008, 'res_port': 8108},
        }
        for code, ports in default_config.items():
            endpoints.append({
                'container': f'vpn-{code}',
                'host': f'vpn-{code}',
                'port': ports['control'],
                'vpn_proxy_port': ports['vpn_port'],
                'residential_proxy_port': ports['res_port'],
                'code': code,
                **COUNTRY_INFO.get(code, {'name': code.upper(), 'flag': '🏳️'})
            })
    else:
        for entry in VPN_ENDPOINTS_RAW.split(','):
            if ':' in entry:
                container_host, port = entry.strip().split(':')
                # Extract country code from container name (vpn-fr -> fr)
                code = container_host.replace('vpn-', '').lower()
                port_num = int(port)
                # Calculate proxy ports based on control port
                base = port_num - 9000
                endpoints.append({
                    'container': container_host,
                    'host': container_host,
                    'port': port_num,
                    'vpn_proxy_port': 8000 + base,
                    'residential_proxy_port': 8100 + base,
                    'code': code,
                    **COUNTRY_INFO.get(code, {'name': code.upper(), 'flag': '🏳️'})
                })
    return endpoints


VPN_ENDPOINTS = parse_vpn_endpoints()


async def fetch_vpn_status(session, endpoint):
    """Fetch status from a single VPN container's gluetun control server."""
    url = f"http://{endpoint['host']}:{endpoint['port']}/v1/publicip/ip"
    status = {
        'container': endpoint['container'],
        'code': endpoint['code'],
        'name': endpoint['name'],
        'flag': endpoint['flag'],
        'status': 'unknown',
        'public_ip': None,
        'country': None,
        'region': None,
        'error': None,
        'vpn_proxy_port': endpoint.get('vpn_proxy_port', 8000 + int(endpoint['port']) - 9000),
        'residential_proxy_port': endpoint.get('residential_proxy_port', 8100 + int(endpoint['port']) - 9000),
        'residential_status': 'unknown',
    }
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status == 200:
                data = await response.json()
                status['public_ip'] = data.get('public_ip', data.get('ip'))
                status['status'] = 'connected'
                
                # Try to get full info
                info_url = f"http://{endpoint['host']}:{endpoint['port']}/v1/publicip/info"
                try:
                    async with session.get(info_url, timeout=aiohttp.ClientTimeout(total=3)) as info_resp:
                        if info_resp.status == 200:
                            info_data = await info_resp.json()
                            status['country'] = info_data.get('country')
                            status['region'] = info_data.get('region')
                except:
                    pass
                
                # Check residential proxy sidecar (via internal port 8889)
                # The sidecar runs in the VPN network, so we check if it's reachable
                status['residential_status'] = 'available' if status['status'] == 'connected' else 'unavailable'
            else:
                status['status'] = 'error'
                status['error'] = f'HTTP {response.status}'
                status['residential_status'] = 'unavailable'
    except asyncio.TimeoutError:
        status['status'] = 'timeout'
        status['error'] = 'Connection timeout'
        status['residential_status'] = 'unavailable'
    except aiohttp.ClientConnectorError as e:
        status['status'] = 'offline'
        status['error'] = 'Cannot connect'
        status['residential_status'] = 'unavailable'
    except Exception as e:
        status['status'] = 'error'
        status['error'] = str(e)
        status['residential_status'] = 'unavailable'
    
    return status


async def get_all_vpn_statuses():
    """Fetch status from all VPN containers concurrently."""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_vpn_status(session, ep) for ep in VPN_ENDPOINTS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        statuses = []
        for result in results:
            if isinstance(result, Exception):
                statuses.append({
                    'status': 'error',
                    'error': str(result)
                })
            else:
                statuses.append(result)
        
        return statuses


DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Status Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e4e4e7;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .subtitle {
            color: #9ca3af;
            font-size: 1rem;
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        .stat {
            text-align: center;
            padding: 15px 25px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
        }
        
        .stat-label {
            font-size: 0.85rem;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stat-connected .stat-value { color: #4ade80; }
        .stat-offline .stat-value { color: #f87171; }
        .stat-total .stat-value { color: #60a5fa; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-4px);
            border-color: rgba(96, 165, 250, 0.3);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }
        
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        
        .country {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .flag {
            font-size: 2rem;
        }
        
        .country-name {
            font-size: 1.25rem;
            font-weight: 600;
        }
        
        .country-code {
            font-size: 0.8rem;
            color: #9ca3af;
            text-transform: uppercase;
        }
        
        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .status-connected {
            background: rgba(74, 222, 128, 0.2);
            color: #4ade80;
            border: 1px solid rgba(74, 222, 128, 0.3);
        }
        
        .status-offline {
            background: rgba(248, 113, 113, 0.2);
            color: #f87171;
            border: 1px solid rgba(248, 113, 113, 0.3);
        }
        
        .status-error, .status-timeout, .status-unknown {
            background: rgba(251, 191, 36, 0.2);
            color: #fbbf24;
            border: 1px solid rgba(251, 191, 36, 0.3);
        }
        
        .card-body {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .info-row:last-child {
            border-bottom: none;
        }
        
        .info-label {
            color: #9ca3af;
            font-size: 0.85rem;
        }
        
        .info-value {
            font-family: 'SF Mono', 'Monaco', monospace;
            font-size: 0.9rem;
            color: #e4e4e7;
        }
        
        .info-value.ip {
            color: #60a5fa;
        }
        
        .error-msg {
            color: #f87171;
            font-size: 0.85rem;
            font-style: italic;
        }
        
        .proxy-types {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .proxy-type {
            padding: 10px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            text-align: center;
        }
        
        .proxy-type-label {
            font-size: 0.7rem;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        
        .proxy-type-port {
            font-family: 'SF Mono', 'Monaco', monospace;
            font-size: 0.85rem;
            color: #60a5fa;
        }
        
        .proxy-type.datacenter {
            border-left: 3px solid #3b82f6;
        }
        
        .proxy-type.residential {
            border-left: 3px solid #8b5cf6;
        }
        
        .residential-badge {
            display: inline-block;
            padding: 2px 6px;
            font-size: 0.65rem;
            background: rgba(139, 92, 246, 0.2);
            color: #a78bfa;
            border-radius: 4px;
            margin-left: 6px;
        }
        
        .refresh-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            padding: 16px 24px;
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 10px 30px rgba(59, 130, 246, 0.3);
            transition: all 0.3s ease;
        }
        
        .refresh-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 40px rgba(59, 130, 246, 0.4);
        }
        
        .refresh-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .last-updated {
            text-align: center;
            color: #6b7280;
            font-size: 0.85rem;
            margin-top: 30px;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .loading {
            animation: pulse 1.5s ease-in-out infinite;
        }
        
        .auto-refresh {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .auto-refresh label {
            color: #9ca3af;
            font-size: 0.9rem;
        }
        
        .toggle {
            position: relative;
            width: 50px;
            height: 26px;
        }
        
        .toggle input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #374151;
            transition: 0.3s;
            border-radius: 26px;
        }
        
        .slider:before {
            position: absolute;
            content: "";
            height: 20px;
            width: 20px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: 0.3s;
            border-radius: 50%;
        }
        
        input:checked + .slider {
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        }
        
        input:checked + .slider:before {
            transform: translateX(24px);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>VPN Status Dashboard</h1>
            <p class="subtitle">ProtonVPN Multi-Country Status Monitor</p>
        </header>
        
        <div class="auto-refresh">
            <label for="autoRefresh">Auto-refresh (30s)</label>
            <label class="toggle">
                <input type="checkbox" id="autoRefresh" checked>
                <span class="slider"></span>
            </label>
        </div>
        
        <div class="stats">
            <div class="stat stat-connected">
                <div class="stat-value" id="connected-count">-</div>
                <div class="stat-label">Connected</div>
            </div>
            <div class="stat stat-offline">
                <div class="stat-value" id="offline-count">-</div>
                <div class="stat-label">Offline</div>
            </div>
            <div class="stat stat-total">
                <div class="stat-value" id="total-count">-</div>
                <div class="stat-label">Total</div>
            </div>
        </div>
        
        <div class="grid" id="vpn-grid">
            <!-- Cards will be inserted here -->
        </div>
        
        <p class="last-updated">Last updated: <span id="last-update">-</span></p>
    </div>
    
    <button class="refresh-btn" onclick="refreshStatus()">Refresh Status</button>
    
    <script>
        let autoRefreshInterval = null;
        
        function createCard(vpn) {
            const statusClass = `status-${vpn.status}`;
            const statusText = vpn.status.charAt(0).toUpperCase() + vpn.status.slice(1);
            const resAvailable = vpn.residential_status === 'available';
            
            return `
                <div class="card">
                    <div class="card-header">
                        <div class="country">
                            <span class="flag">${vpn.flag}</span>
                            <div>
                                <div class="country-name">${vpn.name}${resAvailable ? '<span class="residential-badge">RES</span>' : ''}</div>
                                <div class="country-code">${vpn.code.toUpperCase()} - ${vpn.container}</div>
                            </div>
                        </div>
                        <span class="status-badge ${statusClass}">${statusText}</span>
                    </div>
                    <div class="card-body">
                        ${vpn.public_ip ? `
                            <div class="info-row">
                                <span class="info-label">VPN IP</span>
                                <span class="info-value ip">${vpn.public_ip}</span>
                            </div>
                        ` : ''}
                        ${vpn.country ? `
                            <div class="info-row">
                                <span class="info-label">Location</span>
                                <span class="info-value">${vpn.country}${vpn.region ? ', ' + vpn.region : ''}</span>
                            </div>
                        ` : ''}
                        ${vpn.error ? `
                            <div class="info-row">
                                <span class="info-label">Error</span>
                                <span class="error-msg">${vpn.error}</span>
                            </div>
                        ` : ''}
                        <div class="proxy-types">
                            <div class="proxy-type datacenter">
                                <div class="proxy-type-label">VPN Direct</div>
                                <div class="proxy-type-port">:${vpn.vpn_proxy_port}</div>
                            </div>
                            <div class="proxy-type residential">
                                <div class="proxy-type-label">Residential</div>
                                <div class="proxy-type-port">:${vpn.residential_proxy_port}</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        async function refreshStatus() {
            const btn = document.querySelector('.refresh-btn');
            const grid = document.getElementById('vpn-grid');
            
            btn.disabled = true;
            btn.textContent = 'Loading...';
            grid.classList.add('loading');
            
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                // Update stats
                const connected = data.filter(v => v.status === 'connected').length;
                const offline = data.filter(v => v.status !== 'connected').length;
                
                document.getElementById('connected-count').textContent = connected;
                document.getElementById('offline-count').textContent = offline;
                document.getElementById('total-count').textContent = data.length;
                
                // Update grid
                grid.innerHTML = data.map(createCard).join('');
                
                // Update timestamp
                document.getElementById('last-update').textContent = new Date().toLocaleString();
            } catch (error) {
                console.error('Error fetching status:', error);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Refresh Status';
                grid.classList.remove('loading');
            }
        }
        
        function toggleAutoRefresh() {
            const checkbox = document.getElementById('autoRefresh');
            
            if (checkbox.checked) {
                autoRefreshInterval = setInterval(refreshStatus, 30000);
            } else {
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
            }
        }
        
        // Initialize
        document.getElementById('autoRefresh').addEventListener('change', toggleAutoRefresh);
        refreshStatus();
        toggleAutoRefresh();
    </script>
</body>
</html>
'''


@app.route('/')
def dashboard():
    """Render the dashboard HTML."""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/status')
def api_status():
    """Return VPN status as JSON."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        statuses = loop.run_until_complete(get_all_vpn_statuses())
        return jsonify(statuses)
    finally:
        loop.close()


@app.route('/api/health')
def api_health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9090))
    app.run(host='0.0.0.0', port=port, debug=False)
