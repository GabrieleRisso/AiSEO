# Multi-Country VPN Scraper System

This system runs 5 simultaneous VPN tunnels (France, Germany, Netherlands, Italy, Spain) and rotates their IP addresses every 10 minutes.

## Architecture

- **VPN Services**: 5 Gluetun containers (`vpn-fr`, `vpn-de`, `vpn-nl`, `vpn-it`, `vpn-es`) connected to ProtonVPN.
- **VPN Manager**: A service that periodically restarts the VPN connections to rotate IPs.
- **Scraper Service**: A Python container that can route traffic through any of the 5 VPNs.

## Setup

1. **Configure Credentials**:
   Edit `.env` or set `WIREGUARD_PRIVATE_KEY`.

2. **Start the System**:
   ```bash
   docker-compose up -d
   ```
   This starts all VPNs, the Manager, and the Scraper.

## Usage

### Run Scraper

You can run the scraper from the `scraper` container.

**Pick a random country:**
```bash
docker-compose exec scraper python scripts/scrape_with_vpn.py "best crm" --random
```

**Pick a specific country:**
```bash
docker-compose exec scraper python scripts/scrape_with_vpn.py "best crm" --country fr
```

**Check Available Proxies:**
Inside the container, proxies are available as env vars: `PROXY_FR`, `PROXY_DE`, etc.

### Check Rotation Status

View logs of the manager:
```bash
docker-compose logs -f vpn-manager
```

## Customization

- **Change Countries**: Edit `docker-compose.yml` services `vpn-XX` and change `SERVER_COUNTRIES`.
- **Change Interval**: Edit `vpn-manager` environment variable `ROTATION_INTERVAL` (seconds).
- **Add More Tunnels**: Duplicate a VPN service block and add it to `VPN_CONTAINERS` list in `vpn-manager`.

## Deployment on Railway

1. **Deploy VPNs**: Create 5 services using `qmcgaw/gluetun`. Set `SERVER_COUNTRIES` differently for each.
2. **Deploy Manager**: Deploy this repo, set `command` to `python scripts/vpn_manager.py`. set `VPN_CONTAINERS` to the internal hostnames of your VPN services (e.g. `vpn-fr.railway.internal`).
3. **Deploy Scraper**: Deploy this repo, set env vars `PROXY_FR`, etc. to the internal hostnames.
