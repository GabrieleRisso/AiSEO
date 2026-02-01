# API Reference

Complete reference for all AiSEO API endpoints.

## Endpoints by Category

### Health
- `GET /api/health` - Health check

### System
- `GET /api/config` - System configuration
- `GET /api/vpn/servers` - VPN server list

### Brands
- `GET /api/brands` - List all brands with metrics
- `GET /api/brands/details` - Detailed brand analytics
- `POST /api/brands` - Create new brand
- `DELETE /api/brands/{brand_id}` - Delete brand

### Prompts
- `GET /api/prompts` - List all prompts
- `GET /api/prompts/{query_id}` - Get prompt details

### Sources
- `GET /api/sources` - List all sources
- `GET /api/sources/analytics` - Source analytics

### Analytics
- `GET /api/metrics` - Dashboard metrics
- `GET /api/visibility` - Visibility data
- `GET /api/suggestions` - SEO suggestions

### Jobs
- `GET /api/jobs` - List all jobs
- `POST /api/jobs/scrape` - Create scraping job

## Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

For detailed endpoint documentation with examples, see the interactive docs above.
