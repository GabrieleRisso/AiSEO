# AiSEO Infrastructure - Deployment Summary

Hey! Here's a quick overview of our deployed infrastructure and all the API endpoints.

## 🌐 Live URLs

| Service | URL | What it does |
|---------|-----|--------------|
| **Frontend App** | https://app.tokenspender.com | React dashboard for brand visibility tracking |
| **Backend API** | https://api.tokenspender.com | FastAPI REST API for all data operations |
| **Admin Dashboard** | https://admin.tokenspender.com | System monitoring, VPN status, logs |
| **API Docs** | https://api.tokenspender.com/docs | Swagger/OpenAPI documentation |
| **SQLAdmin** | https://api.tokenspender.com/admin | Database management interface |
| **Scraper API** | http://scraper.tokenspender.com:5000 | Scraping engine with VPN/proxy access |
| **VPN Dashboard** | http://vpn.tokenspender.com:9090 | VPN container status |

---

## 🔌 API Endpoints

### Backend API (api.tokenspender.com)

**Jobs/Scraping:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/jobs` | GET | List all scraping jobs |
| `/api/jobs/scrape` | POST | Create new scrape job |
| `/api/jobs/{id}` | GET | Get job details with results |
| `/api/jobs/{id}/details` | GET | Full job details including screenshots |

**Brands:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/brands` | GET | List all tracked brands |
| `/api/brands` | POST | Add a new brand |
| `/api/brands/{id}` | GET/PUT/DELETE | Manage single brand |

**Statistics:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stats/database` | GET | Database statistics (counts, etc.) |
| `/api/stats/visibility` | GET | Brand visibility metrics |

**Templates & Scheduling:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/templates` | GET/POST | Prompt templates for batch jobs |
| `/api/scheduled-jobs` | GET/POST | Scheduled recurring scrapes |

---

### Scraper API (scraper.tokenspender.com:5000)

**Core:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/config` | GET | Available scrapers and countries |
| `/scrape` | POST | Execute a scrape job |

**Proxy Layers:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/proxies` | GET | All proxy configurations |
| `/profiles` | GET | Device viewport profiles |
| `/api-reference` | GET | Valid API call examples |

**Docker Management (for Admin Dashboard):**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/docker/containers` | GET | List all Docker containers |
| `/api/docker/logs/{name}` | GET | Get container logs |
| `/api/docker/restart/{name}` | POST | Restart a VPN container |

---

## 🔒 VPN Infrastructure

8 countries available for geo-targeted scraping:

| Country | Proxy Port | Control Port |
|---------|------------|--------------|
| 🇫🇷 France | 8001 | 9001 |
| 🇩🇪 Germany | 8002 | 9002 |
| 🇳🇱 Netherlands | 8003 | 9003 |
| 🇮🇹 Italy | 8004 | 9004 |
| 🇪🇸 Spain | 8005 | 9005 |
| 🇬🇧 UK | 8006 | 9006 |
| 🇨🇭 Switzerland | 8007 | 9007 |
| 🇸🇪 Sweden | 8008 | 9008 |

Each VPN has:
- Datacenter IP (free, via ProtonVPN)
- Residential proxy sidecar (Bright Data, ~$8/GB)

---

## 💰 Monthly Costs

| Service | Provider | Cost |
|---------|----------|------|
| Frontend, Backend, Dashboard | Railway | ~$5-15 |
| PostgreSQL Database | Railway | ~$0-5 |
| VPN/Scraper Server | Hetzner CX23 | €4.51 |
| **Total** | | **~$10-25/month** |

---

## 🚀 Quick Commands

**Test backend:**
```bash
curl https://api.tokenspender.com/api/jobs?limit=1
```

**Test scraper:**
```bash
curl http://scraper.tokenspender.com:5000/health
```

**Check VPN status (via admin):**
```bash
curl https://admin.tokenspender.com/proxy/scraper/api/docker/containers
```

**Create a scrape job:**
```bash
curl -X POST https://api.tokenspender.com/api/jobs/scrape \
  -H "Content-Type: application/json" \
  -d '{"query": "best ecommerce platform", "country": "uk", "scraper_type": "google_ai"}'
```

---

## 📊 Admin Dashboard Features

The admin dashboard at https://admin.tokenspender.com provides:

1. **Real-time VPN Status** - All 8 VPNs showing healthy/unhealthy
2. **Docker Logs** - Stream logs from any container
3. **Job Monitoring** - Track scraping jobs and costs
4. **Quick Scrape** - One-click scrape from any country
5. **API Health** - Monitor backend and scraper status

---

## 🔧 Local Development

To run locally:

```bash
# Backend
cd backend && uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Full stack with Docker
docker-compose up -d
```

Local URLs:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Scraper: http://localhost:5000

---

Let me know if you need any changes or have questions!
