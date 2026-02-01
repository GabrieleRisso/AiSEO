# AiSEO Deployment Guide

Complete guide for deploying AiSEO in production and running locally.

## 🌐 Production URLs

| Service | URL | Provider |
|---------|-----|----------|
| **Frontend** | https://app.tokenspender.com | Railway |
| **Backend API** | https://api.tokenspender.com | Railway |
| **Admin Dashboard** | https://admin.tokenspender.com | Railway |
| **Scraper API** | http://scraper.tokenspender.com:5000 | Hetzner |
| **VPN Dashboard** | http://vpn.tokenspender.com:9090 | Hetzner |
| **API Docs** | https://api.tokenspender.com/docs | Railway |
| **SQLAdmin** | https://api.tokenspender.com/admin | Railway |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAILWAY (Cloud PaaS)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Frontend    │  │  Backend API │  │  Admin Dashboard     │   │
│  │  (React)     │  │  (FastAPI)   │  │  (Python + HTML)     │   │
│  │  :3000       │  │  :8000       │  │  :9091               │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                           │                    │                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    PostgreSQL                            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ API calls (proxied)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                 HETZNER (VPS - 65.108.158.17)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Scraper API (:5000)                         │   │
│  │   - Google AI scraping                                   │   │
│  │   - Docker management endpoints                          │   │
│  │   - Proxy layer selection                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              VPN Stack (8 countries)                     │   │
│  │   vpn-fr, vpn-de, vpn-nl, vpn-it                        │   │
│  │   vpn-es, vpn-uk, vpn-ch, vpn-se                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Residential Proxies (8 sidecars)               │   │
│  │   Bright Data integration via GOST                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💻 Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Google Chrome (for scraper)

### 1. Backend (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start server
uvicorn main:app --reload --port 8000
```

**Local URLs:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Admin: http://localhost:8000/admin

### 2. Frontend (React)

```bash
cd frontend

# Install dependencies
npm install

# Create local env file
echo "VITE_API_BASE_URL=http://localhost:8000/api" > .env

# Start dev server
npm run dev
```

**Local URL:** http://localhost:5173

### 3. Full Stack with Docker

```bash
# From project root
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

This starts:
- Backend API on :8000
- Frontend on :5173
- Scraper API on :5000
- VPN containers (if configured)

### 4. Admin Dashboard (Local)

```bash
cd admin-dashboard

# Start simple server
python server.py
```

**Local URL:** http://localhost:9091

---

## 🚀 Deploying to Production

### Railway Services

All Railway services are configured with `railway.json` files and deploy automatically from the main branch.

**Manual redeploy:**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy a service
cd aiseo
railway service link aiseo-api
railway up --detach

# Or deploy frontend
railway service link aiseo-frontend
railway up --path-as-root --detach ./frontend
```

### Hetzner VPN Stack

```bash
# SSH to server
ssh -i ~/.ssh/hetzner root@65.108.158.17

# View services
cd /opt/aiseo
docker-compose ps

# Restart services
docker-compose restart

# View logs
docker-compose logs -f scraper
docker-compose logs -f vpn-fr

# Update and redeploy
# (from local machine)
scp -i ~/.ssh/hetzner ./src/scraper_api.py root@65.108.158.17:/opt/aiseo/src/
ssh -i ~/.ssh/hetzner root@65.108.158.17 "cd /opt/aiseo && docker-compose restart scraper"
```

---

## 🔧 Environment Variables

### Backend (Railway)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | Auto-set by Railway |
| `CORS_ORIGINS` | Allowed origins | `https://app.tokenspender.com` |
| `SECRET_KEY` | Session secret | Random 32-char string |
| `LOG_LEVEL` | Logging level | `INFO` |

### Frontend (Railway)

| Variable | Description | Value |
|----------|-------------|-------|
| `VITE_API_BASE_URL` | Backend API | `https://api.tokenspender.com/api` |

### Admin Dashboard (Railway)

| Variable | Description | Value |
|----------|-------------|-------|
| `API_BASE_URL` | Backend API | `https://api.tokenspender.com` |
| `SCRAPER_API_URL` | Scraper API | `http://scraper.tokenspender.com:5000` |
| `VPN_DASHBOARD_URL` | VPN Dashboard | `http://vpn.tokenspender.com:9090` |

### Scraper / VPN (Hetzner)

See `deploy/README.md` for full environment variable reference including:
- ProtonVPN WireGuard keys
- Bright Data credentials
- Proxy configuration

---

## 📡 API Endpoints Summary

### Backend API (api.tokenspender.com)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/jobs` | GET | List scraping jobs |
| `/api/jobs/scrape` | POST | Create new scrape job |
| `/api/jobs/{id}` | GET | Get job details |
| `/api/brands` | GET/POST | Manage brands |
| `/api/stats/database` | GET | Database statistics |
| `/admin` | GET | SQLAdmin panel |
| `/docs` | GET | Swagger documentation |

### Scraper API (scraper.tokenspender.com:5000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/config` | GET | Scraper configuration |
| `/scrape` | POST | Execute scrape job |
| `/profiles` | GET | Device viewport profiles |
| `/proxies` | GET | Available proxies |
| `/api/docker/containers` | GET | List Docker containers |
| `/api/docker/logs/{name}` | GET | Get container logs |

---

## 🔒 Security

### Firewall (Hetzner - UFW)

```
22/tcp     - SSH
5000/tcp   - Scraper API
9090/tcp   - VPN Dashboard
8001-8008  - VPN Proxies (datacenter)
8101-8108  - VPN Proxies (residential)
9001-9008  - VPN Control ports
```

### Cloudflare DNS

All domains use Cloudflare with:
- HTTPS (Full strict mode for Railway)
- Proxied for Railway services
- DNS-only for Hetzner (port requirements)

---

## 📊 Monitoring

### Admin Dashboard Features

- Real-time VPN status (8/8 healthy)
- Docker container management
- Live log streaming
- Job monitoring
- API health checks

### Useful Commands

```bash
# Check all VPN IPs
for port in 8001 8002 8003 8004 8005 8006 8007 8008; do
  curl -s --proxy http://65.108.158.17:$port ifconfig.me
done

# Test scraper API
curl http://scraper.tokenspender.com:5000/health

# Test backend API
curl https://api.tokenspender.com/api/jobs?limit=1
```

---

## 💰 Cost Summary

| Service | Provider | Monthly Cost |
|---------|----------|--------------|
| Frontend | Railway | ~$0-5 |
| Backend API | Railway | ~$0-5 |
| Admin Dashboard | Railway | ~$0-2 |
| PostgreSQL | Railway | ~$0-5 |
| **VPN Stack** | **Hetzner CX23** | **€4.51** |
| **Total** | | **~$10-20/month** |

---

## 🔄 Deployment Checklist

- [ ] Backend API responding at api.tokenspender.com
- [ ] Frontend loading at app.tokenspender.com
- [ ] Admin dashboard at admin.tokenspender.com
- [ ] Scraper API at scraper.tokenspender.com:5000
- [ ] All 8 VPNs showing healthy
- [ ] Docker logs accessible via admin dashboard
- [ ] Database connected (check /admin)
