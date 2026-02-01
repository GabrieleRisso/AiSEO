# AiSEO VPN Infrastructure Deployment

Deploy the VPN/Scraper stack to Hetzner or Oracle Cloud.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Railway (Cloud)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Frontend   │  │  Backend    │  │  PostgreSQL         │  │
│  │  (React)    │  │  (FastAPI)  │  │  (Database)         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ API calls
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Hetzner / Oracle Cloud (VPS)                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              VPN Stack (8 countries)                │    │
│  │  vpn-fr, vpn-de, vpn-nl, vpn-it,                   │    │
│  │  vpn-es, vpn-uk, vpn-ch, vpn-se                    │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Scraper API (:5000)                    │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           VPN Dashboard (:9090)                     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Comparison

| Feature | Hetzner CX22 | Oracle Free Tier |
|---------|--------------|------------------|
| **Cost** | €3.79/month | **FREE** |
| **CPU** | 2 vCPU (x86) | 4 ARM cores |
| **RAM** | 4 GB | 24 GB |
| **Storage** | 40 GB SSD | 200 GB |
| **Architecture** | x86_64 | ARM64 |
| **Setup** | 5 min | 15 min |
| **Best For** | Production | Testing/Dev |

---

## Option 1: Hetzner Cloud (Recommended for Production)

### Step 1: Create Server

1. Go to [Hetzner Cloud Console](https://console.hetzner.cloud/)
2. Create new project (if needed)
3. Add Server:
   - **Location**: Falkenstein or Helsinki (EU)
   - **Image**: Ubuntu 24.04
   - **Type**: CX22 (€3.79/month)
   - **SSH Key**: Add your public key
   - **Cloud config**: Paste contents of `hetzner/cloud-init.yaml`
4. Create server and note the IP

### Step 2: Deploy

```bash
# Make script executable
chmod +x hetzner/deploy.sh

# Deploy (replace with your server IP)
./hetzner/deploy.sh YOUR_SERVER_IP ~/.ssh/id_rsa
```

### Step 3: Configure & Start

```bash
# SSH to server
ssh root@YOUR_SERVER_IP

# Edit environment variables
nano /opt/aiseo/.env
# Add your ProtonVPN WireGuard keys!

# Start services
cd /opt/aiseo
docker-compose up -d

# Check status
docker-compose ps
```

---

## Option 2: Oracle Cloud Free Tier (FREE!)

### Step 1: Create Free Account

1. Go to [Oracle Cloud](https://www.oracle.com/cloud/free/)
2. Sign up for Always Free tier
3. Wait for account activation (can take 24h)

### Step 2: Create Instance

1. Go to Compute > Instances > Create Instance
2. Configure:
   - **Name**: aiseo-vpn
   - **Image**: Ubuntu 22.04 (or 24.04)
   - **Shape**: VM.Standard.A1.Flex (ARM)
     - **OCPUs**: 4 (max free)
     - **Memory**: 24 GB (max free)
   - **Networking**: Create new VCN or use existing
   - **SSH Key**: Upload your public key
   - **Cloud-init**: Paste contents of `oracle/cloud-init.yaml`
3. Create and note the public IP

### Step 3: Configure Security List (IMPORTANT!)

Oracle Cloud blocks all ports by default. You must open them:

1. Go to **Networking > Virtual Cloud Networks**
2. Click your VCN > **Security Lists** > **Default Security List**
3. Add **Ingress Rules**:

| Source CIDR | Protocol | Port Range | Description |
|-------------|----------|------------|-------------|
| 0.0.0.0/0 | TCP | 22 | SSH |
| 0.0.0.0/0 | TCP | 5000 | Scraper API |
| 0.0.0.0/0 | TCP | 9090 | VPN Dashboard |
| 0.0.0.0/0 | TCP | 8001-8008 | VPN Proxies |
| 0.0.0.0/0 | TCP | 9001-9008 | VPN Control |

### Step 4: Deploy

```bash
chmod +x oracle/deploy.sh
./oracle/deploy.sh YOUR_SERVER_IP ~/.ssh/id_rsa ubuntu
```

### Step 5: Configure & Start

```bash
ssh -i ~/.ssh/id_rsa ubuntu@YOUR_SERVER_IP

nano /opt/aiseo/.env
# Add ProtonVPN keys

cd /opt/aiseo
sudo docker-compose up -d
sudo docker-compose ps
```

---

## Environment Variables

Create `.env` file with your credentials:

```bash
# ProtonVPN WireGuard Keys (REQUIRED)
# Generate from: https://account.protonvpn.com/downloads#wireguard-configuration
# Select WireGuard > Create Certificate for each country

PROTONVPN_KEY_FR=your_france_private_key
PROTONVPN_KEY_DE=your_germany_private_key
PROTONVPN_KEY_NL=your_netherlands_private_key
PROTONVPN_KEY_IT=your_italy_private_key
PROTONVPN_KEY_ES=your_spain_private_key
PROTONVPN_KEY_UK=your_uk_private_key
PROTONVPN_KEY_CH=your_switzerland_private_key
PROTONVPN_KEY_SE=your_sweden_private_key

# Bright Data Residential Proxy (OPTIONAL)
BRIGHT_DATA_USER=
BRIGHT_DATA_PASSWORD=
BRIGHT_DATA_HOST=brd.superproxy.io
BRIGHT_DATA_PORT=22225

# Bright Data Scraping Browser (OPTIONAL)
BRIGHTDATA_API_TOKEN=
BRIGHTDATA_CUSTOMER_ID=
BRIGHTDATA_BROWSER_ZONE=scraping_browser1
BRIGHTDATA_BROWSER_PASSWORD=
```

---

## Endpoints

After deployment, these endpoints are available:

| Service | Port | URL |
|---------|------|-----|
| Scraper API | 5000 | http://YOUR_IP:5000 |
| VPN Dashboard | 9090 | http://YOUR_IP:9090 |
| VPN France Proxy | 8001 | http://YOUR_IP:8001 |
| VPN Germany Proxy | 8002 | http://YOUR_IP:8002 |
| VPN Netherlands Proxy | 8003 | http://YOUR_IP:8003 |
| VPN Italy Proxy | 8004 | http://YOUR_IP:8004 |
| VPN Spain Proxy | 8005 | http://YOUR_IP:8005 |
| VPN UK Proxy | 8006 | http://YOUR_IP:8006 |
| VPN Switzerland Proxy | 8007 | http://YOUR_IP:8007 |
| VPN Sweden Proxy | 8008 | http://YOUR_IP:8008 |

---

## Management Commands

```bash
# View all containers
docker-compose ps

# View logs
docker-compose logs -f vpn-fr
docker-compose logs -f scraper

# Restart a VPN
docker-compose restart vpn-fr

# Restart all
docker-compose restart

# Stop all
docker-compose down

# Update and restart
docker-compose pull
docker-compose up -d
```

---

## Troubleshooting

### VPN not connecting
```bash
# Check VPN logs
docker logs vpn-fr

# Common issues:
# - Invalid WireGuard key
# - ProtonVPN server maintenance
# - Firewall blocking
```

### Oracle Cloud ports not accessible
1. Check Security List has ingress rules
2. Check instance iptables: `sudo iptables -L -n`
3. Ensure cloud-init completed: `cat /var/log/cloud-init-output.log`

### ARM compatibility (Oracle)
All images used are multi-arch and support ARM64:
- `qmcgaw/gluetun` ✅
- `ginuerzh/gost` ✅
- Python images ✅

---

## Cost Summary

| Component | Provider | Monthly Cost |
|-----------|----------|--------------|
| Frontend | Railway | $0-2 |
| Backend API | Railway | $0-5 |
| PostgreSQL | Railway | $0-5 |
| **VPN Stack** | **Hetzner** | **€3.79** |
| **VPN Stack** | **Oracle** | **FREE** |
| **TOTAL** | | **$5-15** or **$0-12** |
