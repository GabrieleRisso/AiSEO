# 🚀 AiSEO API - Complete Guide

**Everything you need to know about the APIs**

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [API Overview](#api-overview)
3. [Categories](#categories)
4. [Endpoints](#endpoints)
5. [Examples](#examples)
6. [Team Guide](#team-guide)

---

## 🚀 Quick Start

### Start Services
```bash
docker-compose up -d scraper backend
```

### Access Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Scraper API**: http://localhost:5000/docs

### Test APIs
```bash
curl http://localhost:5000/health
curl http://localhost:8000/api/health
```

---

## 📊 API Overview

### Scraper API (Port 5000)
**Purpose**: Execute web scraping operations

**Categories:**
- 🏥 **Health** - Service status
- ⚙️ **Config** - System configuration  
- 🔧 **Scraping** - Execute scraping jobs

**Total Endpoints**: 3

### Backend API (Port 8000)
**Purpose**: Manage data, analytics, and jobs

**Categories:**
- 🏥 **Health** - Service status
- ⚙️ **System** - Configuration and VPN
- 🏷️ **Brands** - Brand management
- 💬 **Prompts** - Query tracking
- 📄 **Sources** - Citation tracking
- 📊 **Analytics** - Metrics and insights
- 🔧 **Jobs** - Job management

**Total Endpoints**: 16

---

## 🏷️ Categories Explained

### 🏥 Health
**Purpose**: Check if services are running

**Endpoints:**
- `GET /health` (Scraper)
- `GET /api/health` (Backend)

**When to use**: Monitoring, health checks, service discovery

---

### ⚙️ System
**Purpose**: Get system configuration

**Endpoints:**
- `GET /config` - Scraper config
- `GET /api/config` - Backend config
- `GET /api/vpn/servers` - VPN servers

**When to use**: Discover available options, check configuration

---

### 🏷️ Brands
**Purpose**: Track brand visibility

**Endpoints:**
- `GET /api/brands` - List brands
- `GET /api/brands/details` - Detailed analytics
- `POST /api/brands` - Create brand
- `DELETE /api/brands/{id}` - Delete brand

**When to use**: Monitor brand mentions, track competitors

---

### 💬 Prompts
**Purpose**: Track search queries

**Endpoints:**
- `GET /api/prompts` - List queries
- `GET /api/prompts/{id}` - Query details

**When to use**: Analyze query performance, track results

---

### 📄 Sources
**Purpose**: Track citation sources

**Endpoints:**
- `GET /api/sources` - List sources
- `GET /api/sources/analytics` - Source analytics

**When to use**: Analyze citations, track domains

---

### 📊 Analytics
**Purpose**: Get insights and metrics

**Endpoints:**
- `GET /api/metrics` - Dashboard KPIs
- `GET /api/visibility` - Visibility trends
- `GET /api/suggestions` - SEO suggestions

**When to use**: Build dashboards, get recommendations

---

### 🔧 Jobs
**Purpose**: Manage scraping jobs

**Endpoints:**
- `GET /api/jobs` - List jobs
- `POST /api/jobs/scrape` - Create job

**When to use**: Schedule scraping, monitor jobs

---

### 🔧 Scraping
**Purpose**: Execute scraping operations

**Endpoints:**
- `POST /scrape` - Run scraping job

**When to use**: Immediate scraping, testing

---

## 📖 Complete Endpoint List

### Scraper API

| Category | Method | Endpoint | Description |
|----------|--------|----------|-------------|
| Health | GET | `/health` | Check service status |
| Config | GET | `/config` | Get scraper configuration |
| Scraping | POST | `/scrape` | Execute scraping job |

### Backend API

| Category | Method | Endpoint | Description |
|----------|--------|----------|-------------|
| Health | GET | `/api/health` | Check service status |
| System | GET | `/api/config` | Get system configuration |
| System | GET | `/api/vpn/servers` | Get VPN server list |
| Brands | GET | `/api/brands` | List all brands |
| Brands | GET | `/api/brands/details` | Get detailed analytics |
| Brands | POST | `/api/brands` | Create new brand |
| Brands | DELETE | `/api/brands/{id}` | Delete brand |
| Prompts | GET | `/api/prompts` | List all prompts |
| Prompts | GET | `/api/prompts/{id}` | Get prompt details |
| Sources | GET | `/api/sources` | List all sources |
| Sources | GET | `/api/sources/analytics` | Get source analytics |
| Analytics | GET | `/api/metrics` | Get dashboard metrics |
| Analytics | GET | `/api/visibility` | Get visibility data |
| Analytics | GET | `/api/suggestions` | Get SEO suggestions |
| Jobs | GET | `/api/jobs` | List all jobs |
| Jobs | POST | `/api/jobs/scrape` | Create scraping job |

---

## 💡 Examples

### Example 1: Check Service Health
```bash
curl http://localhost:8000/api/health
```

### Example 2: Get Brand Visibility
```bash
curl http://localhost:8000/api/brands
```

### Example 3: Create Scraping Job
```bash
curl -X POST http://localhost:8000/api/jobs/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "query": "best seo tools",
    "country": "us",
    "scraper_type": "google_ai"
  }'
```

### Example 4: Get Dashboard Metrics
```bash
curl http://localhost:8000/api/metrics
```

---

## 👥 Team Resources

### Documentation Files
- **TEAM_GUIDE.md** - Complete team guide
- **API_REFERENCE.md** - Quick endpoint reference
- **API_DOCS.md** - Detailed documentation
- **QUICK_START_GUIDE.md** - Quick start instructions

### Testing Tools
- **Postman Collection**: `postman/AiSEO_API.postman_collection.json`
- **Environment**: `postman/Local.postman_environment.json`
- **Web Interface**: http://localhost:9000 (API Tester)

### Interactive Docs
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🎯 Common Workflows

### Workflow 1: Monitor Brand Visibility
1. `GET /api/brands` - See all brands
2. `GET /api/brands/details` - Get detailed analytics
3. `GET /api/metrics` - Check overall metrics

### Workflow 2: Create and Track Job
1. `POST /api/jobs/scrape` - Create job
2. `GET /api/jobs` - Check job status
3. `GET /api/prompts` - See results

### Workflow 3: Analyze Sources
1. `GET /api/sources` - List sources
2. `GET /api/sources/analytics` - Get analytics
3. `GET /api/suggestions` - Get recommendations

---

## ✅ Best Practices

1. **Always check health** before making requests
2. **Use appropriate categories** for organization
3. **Monitor job status** for long operations
4. **Use scheduled jobs** for recurring tasks
5. **Check documentation** for examples

---

## 📞 Getting Help

- **Swagger UI**: Interactive API explorer
- **Team Guide**: `TEAM_GUIDE.md`
- **API Reference**: `API_REFERENCE.md`
- **Postman**: Pre-configured collection

---

**Ready to use! Start with the Quick Start section above.** 🚀
