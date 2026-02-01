# 👥 AiSEO API - Team Guide

**Simple, organized guide for the entire team**

## 🚀 Quick Start

### 1. Start Services
```bash
docker-compose up -d scraper backend
```

### 2. Access Documentation
- **Backend Swagger UI**: http://localhost:8000/docs
- **Backend ReDoc**: http://localhost:8000/redoc
- **Scraper API Docs**: http://localhost:5000/docs

### 3. Test APIs
```bash
# Health checks
curl http://localhost:5000/health
curl http://localhost:8000/api/health

# Get configuration
curl http://localhost:8000/api/config
```

---

## 📚 API Overview

### Scraper API (Port 5000)
**Purpose**: Execute web scraping jobs

**Categories:**
- **Health** - Service status checks
- **Config** - System configuration
- **Scraping** - Execute scraping operations

**Endpoints:**
- `GET /health` - Check if service is running
- `GET /config` - Get available scrapers and proxies
- `POST /scrape` - Run a scraping job

### Backend API (Port 8000)
**Purpose**: Manage brands, analytics, and jobs

**Categories:**
- **Health** - Service status
- **System** - Configuration and VPN info
- **Brands** - Brand management and analytics
- **Prompts** - Query and prompt tracking
- **Sources** - Citation source management
- **Analytics** - Metrics and reporting
- **Jobs** - Scraping job management

---

## 📋 API Categories Explained

### 🏥 Health
**Purpose**: Check if services are running

**Endpoints:**
- `GET /health` (Scraper API)
- `GET /api/health` (Backend API)

**Use Case**: Monitoring, health checks, service discovery

---

### ⚙️ System
**Purpose**: Get system configuration and infrastructure info

**Endpoints:**
- `GET /config` - Scraper configuration
- `GET /api/config` - Backend configuration
- `GET /api/vpn/servers` - Available VPN servers

**Use Case**: Discover available scrapers, proxies, VPN locations

---

### 🏷️ Brands
**Purpose**: Track brand visibility and mentions in AI responses

**Endpoints:**
- `GET /api/brands` - List all brands with metrics
- `GET /api/brands/details` - Detailed brand analytics
- `POST /api/brands` - Create new brand
- `DELETE /api/brands/{id}` - Delete brand

**Use Case**: 
- Monitor brand visibility across queries
- Track competitor mentions
- Analyze brand positioning trends

**Key Metrics:**
- Visibility (% of queries mentioning brand)
- Average position when mentioned
- Trend (up/down/stable)
- Sentiment analysis

---

### 💬 Prompts
**Purpose**: Track search queries and their results

**Endpoints:**
- `GET /api/prompts` - List all queries with stats
- `GET /api/prompts/{query_id}` - Get detailed query info

**Use Case**:
- Track which queries mention your brand
- Analyze query performance over time
- See all runs/scrapes for a query

**Key Metrics:**
- Visibility across runs
- Average position
- Total mentions
- Number of runs

---

### 📄 Sources
**Purpose**: Track citation sources and domains

**Endpoints:**
- `GET /api/sources` - List all sources with usage
- `GET /api/sources/analytics` - Detailed source analytics

**Use Case**:
- See which domains cite your brand
- Analyze source types (blog, news, community)
- Track citation patterns

**Key Metrics:**
- Usage (% of queries citing source)
- Average citation position
- Source type breakdown
- Top domains

---

### 📊 Analytics
**Purpose**: Get insights and metrics for dashboards

**Endpoints:**
- `GET /api/metrics` - Dashboard KPIs
- `GET /api/visibility` - Monthly visibility trends
- `GET /api/suggestions` - SEO improvement suggestions

**Use Case**:
- Build dashboards
- Track trends over time
- Get actionable SEO recommendations

**Key Metrics:**
- Overall visibility score
- Total prompts tracked
- Total sources cited
- Average position
- Month-over-month changes

---

### 🔧 Jobs
**Purpose**: Create and manage scraping jobs

**Endpoints:**
- `GET /api/jobs` - List all jobs
- `POST /api/jobs/scrape` - Create new scraping job

**Use Case**:
- Schedule recurring scraping jobs
- Monitor job status
- Track scraping history

**Job Types:**
- **One-time**: Execute immediately
- **Scheduled**: Recurring (daily, weekly, hourly)

---

## 🎯 Common Use Cases

### Use Case 1: Check Brand Visibility
```bash
# Get all brands with visibility metrics
curl http://localhost:8000/api/brands

# Get detailed analytics for a brand
curl http://localhost:8000/api/brands/details
```

### Use Case 2: Create a Scraping Job
```bash
curl -X POST http://localhost:8000/api/jobs/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "query": "best seo tools",
    "country": "us",
    "scraper_type": "google_ai"
  }'
```

### Use Case 3: Get Dashboard Metrics
```bash
# Get all KPIs
curl http://localhost:8000/api/metrics

# Get visibility trends
curl http://localhost:8000/api/visibility

# Get SEO suggestions
curl http://localhost:8000/api/suggestions
```

### Use Case 4: Track a Query
```bash
# List all queries
curl http://localhost:8000/api/prompts

# Get details for a specific query
curl http://localhost:8000/api/prompts/query-1
```

---

## 📖 Code Organization

### Scraper API (`src/scraper_api.py`)
```
├── Health Endpoints
│   └── GET /health
├── Config Endpoints
│   └── GET /config
└── Scraping Endpoints
    └── POST /scrape
```

### Backend API (`backend/main.py`)
```
├── Health
│   └── GET /api/health
├── System
│   ├── GET /api/config
│   └── GET /api/vpn/servers
├── Brands
│   ├── GET /api/brands
│   ├── GET /api/brands/details
│   ├── POST /api/brands
│   └── DELETE /api/brands/{id}
├── Prompts
│   ├── GET /api/prompts
│   └── GET /api/prompts/{id}
├── Sources
│   ├── GET /api/sources
│   └── GET /api/sources/analytics
├── Analytics
│   ├── GET /api/metrics
│   ├── GET /api/visibility
│   └── GET /api/suggestions
└── Jobs
    ├── GET /api/jobs
    └── POST /api/jobs/scrape
```

---

## 🔑 Key Concepts

### Scraper Types
- **google_ai**: Google AI Overview (default)
- **perplexity**: Perplexity AI
- **brightdata**: BrightData residential proxy
- **chatgpt**: ChatGPT

### Proxy Types
- **Datacenter VPN**: Standard VPN proxy (port 8888)
- **Residential Proxy**: Residential IP proxy (port 8889, requires sidecar)

### Job Statuses
- **pending**: Queued but not started
- **running**: Currently executing
- **completed**: Finished successfully
- **failed**: Encountered an error
- **scheduled**: Recurring job waiting for next run

### Brand Types
- **primary**: Your main brand (only one allowed)
- **competitor**: Competitor brands

---

## 🛠️ Development Workflow

### 1. Making Changes
1. Edit endpoint in `src/scraper_api.py` or `backend/main.py`
2. Add/update documentation (tags, description, examples)
3. Test locally: `curl http://localhost:8000/api/health`
4. Update Postman collection if needed
5. Commit changes

### 2. Adding New Endpoints
1. Add endpoint with proper decorator
2. Add tag (use existing categories)
3. Add summary and description
4. Add response model
5. Add examples
6. Update Postman collection
7. Update this guide

### 3. Testing
```bash
# Test health
curl http://localhost:5000/health
curl http://localhost:8000/api/health

# Test with Postman
# Import collection and run tests
```

---

## 📦 Files to Share

### For Developers
- `TEAM_GUIDE.md` - This file
- `API_DOCS.md` - Detailed API documentation
- `QUICK_START_GUIDE.md` - Quick start instructions

### For API Users
- `postman/AiSEO_API.postman_collection.json` - Postman collection
- `postman/Local.postman_environment.json` - Environment config
- `postman/README.md` - Postman setup guide

### For Documentation
- Backend Swagger UI: http://localhost:8000/docs
- Backend ReDoc: http://localhost:8000/redoc
- Scraper API Docs: http://localhost:5000/docs

---

## 🎓 Learning Path

### Beginner
1. Read this guide
2. Open Backend Swagger UI: http://localhost:8000/docs
3. Open Scraper API Docs: http://localhost:5000/docs
4. Try health endpoints
5. Try config endpoints

### Intermediate
1. Use Postman collection
2. Create a scraping job
3. Check brand visibility
4. View analytics

### Advanced
1. Schedule recurring jobs
2. Analyze source patterns
3. Use anti-detection features
4. Integrate with your application

---

## 📞 Getting Help

### Documentation
- **Backend Swagger UI**: http://localhost:8000/docs - Interactive API explorer
- **Backend ReDoc**: http://localhost:8000/redoc - Beautiful documentation view
- **Scraper API Docs**: http://localhost:5000/docs - Scraper API documentation
- **API_DOCS.md**: Detailed endpoint docs
- **Postman Collection**: Pre-configured requests

### Testing
- **Swagger UI**: Try endpoints directly (Backend: http://localhost:8000/docs, Scraper: http://localhost:5000/docs)
- **Postman**: Run automated tests
- **cURL**: Command-line testing

### Troubleshooting
1. Check services: `docker-compose ps`
2. Check logs: `docker-compose logs scraper backend`
3. Test health: `curl http://localhost:8000/api/health`
4. Review documentation

---

## ✅ Best Practices

### API Usage
- ✅ Always check health before making requests
- ✅ Use appropriate scraper type for your needs
- ✅ Monitor job status for long-running operations
- ✅ Use scheduled jobs for recurring tasks

### Development
- ✅ Follow existing naming conventions
- ✅ Use appropriate tags/categories
- ✅ Add clear descriptions
- ✅ Include examples
- ✅ Update Postman collection

### Documentation
- ✅ Keep descriptions simple and clear
- ✅ Use consistent naming
- ✅ Provide examples
- ✅ Document all parameters
- ✅ Update team guide when adding features

---

## 🎯 Quick Reference

### Most Used Endpoints
1. `GET /api/health` - Check service status
2. `GET /api/brands` - List brands
3. `GET /api/metrics` - Dashboard metrics
4. `POST /api/jobs/scrape` - Create job
5. `GET /api/jobs` - List jobs

### Most Used Categories
1. **Analytics** - Get insights and metrics
2. **Brands** - Track brand visibility
3. **Jobs** - Manage scraping jobs
4. **System** - Get configuration

---

**Last Updated**: 2026-01-31
**Version**: 1.0.0
**Status**: ✅ Ready for Team Use
