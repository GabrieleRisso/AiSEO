# 📖 API Reference - Quick Lookup

**Simple reference for all API endpoints**

---

## 🔍 Scraper API (Port 5000)

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check service status |

### Configuration
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/config` | Get scraper configuration |

### Scraping
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/scrape` | Execute scraping job |

---

## 🔍 Backend API (Port 8000)

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Check service status |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/config` | Get system configuration |
| GET | `/api/vpn/servers` | Get VPN server list |

### Brands
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/brands` | List all brands |
| GET | `/api/brands/details` | Get detailed brand analytics |
| POST | `/api/brands` | Create new brand |
| DELETE | `/api/brands/{id}` | Delete brand |

### Prompts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/prompts` | List all prompts |
| GET | `/api/prompts/{query_id}` | Get prompt details |

### Sources
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sources` | List all sources |
| GET | `/api/sources/analytics` | Get source analytics |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/metrics` | Get dashboard metrics |
| GET | `/api/visibility` | Get visibility data |
| GET | `/api/suggestions` | Get SEO suggestions |

### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | List all jobs |
| POST | `/api/jobs/scrape` | Create scraping job |

---

## 📝 Request Examples

### Create Scraping Job
```json
POST /api/jobs/scrape
{
  "query": "best seo tools",
  "country": "us",
  "scraper_type": "google_ai",
  "num_results": 10
}
```

### Create Brand
```json
POST /api/brands
{
  "id": "my-brand",
  "name": "My Brand",
  "type": "competitor",
  "color": "#ff0000",
  "variations": ["My Brand", "MB"]
}
```

### Schedule Recurring Job
```json
POST /api/jobs/scrape
{
  "query": "daily tracking",
  "country": "it",
  "frequency": "daily",
  "start_date": "2026-02-01T09:00:00"
}
```

---

## 📤 Response Examples

### Health Check
```json
{
  "status": "ok"
}
```

### Config
```json
{
  "scrapers": ["google_ai", "perplexity", "brightdata", "chatgpt"],
  "proxies": ["ch", "de", "es", "fr", "it", "nl", "se", "uk"],
  "default_scraper": "google_ai"
}
```

### Brands List
```json
[
  {
    "id": "wix",
    "name": "Wix",
    "type": "primary",
    "color": "#06b6d4",
    "visibility": 45.5,
    "avgPosition": 2.3,
    "trend": "up",
    "sentiment": "positive"
  }
]
```

---

## 🏷️ Category Guide

| Category | Purpose | Endpoints |
|----------|---------|-----------|
| **Health** | Service status | 2 endpoints |
| **System** | Configuration | 3 endpoints |
| **Brands** | Brand management | 4 endpoints |
| **Prompts** | Query tracking | 2 endpoints |
| **Sources** | Citation tracking | 2 endpoints |
| **Analytics** | Metrics & insights | 3 endpoints |
| **Jobs** | Job management | 2 endpoints |
| **Scraping** | Execute scraping | 1 endpoint |

---

## 🔗 Quick Links

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Team Guide**: `TEAM_GUIDE.md`
- **Postman Collection**: `postman/AiSEO_API.postman_collection.json`

---

**Keep this handy for quick API lookups!**
