# AiSEO API Documentation

Complete API reference for the AiSEO platform.

## Base URL

- **Local**: `http://localhost:8000/api`
- **Production**: `https://api.aiseo.example.com/api`

## Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Postman Collection**: See [Postman Guide](./postman/README.md)

## Endpoints

### Health

#### GET /api/health
Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

### System

#### GET /api/config
Get system configuration including available scrapers and proxies.

**Response:**
```json
{
  "scrapers": ["google_ai", "perplexity", "chatgpt"],
  "proxies": ["fr", "de", "nl", "it", "es", "uk", "ch", "se"],
  "default_scraper": "google_ai"
}
```

#### GET /api/vpn/servers
Get list of available VPN servers.

### Brands

#### GET /api/brands
List all brands with visibility metrics.

**Response:**
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

#### GET /api/brands/details
Get detailed brand analytics with monthly breakdown.

#### POST /api/brands
Create a new brand.

**Request:**
```json
{
  "id": "magento",
  "name": "Magento",
  "type": "competitor",
  "color": "#f97316",
  "variations": ["Magento", "Adobe Commerce"]
}
```

#### DELETE /api/brands/{brand_id}
Delete a brand and all its mentions.

### Prompts

#### GET /api/prompts
List all prompts with aggregated statistics.

#### GET /api/prompts/{query_id}
Get detailed prompt information with all runs.

### Sources

#### GET /api/sources
List all citation sources with usage metrics.

#### GET /api/sources/analytics
Get detailed source analytics including types and domains.

### Analytics

#### GET /api/metrics
Get dashboard KPIs including visibility, position, and counts.

**Response:**
```json
{
  "visibility": {
    "value": 45.5,
    "trend": "up",
    "change": 5.2
  },
  "avgPosition": {
    "value": 2.3,
    "trend": "down",
    "change": -0.5
  },
  "totalPrompts": 150,
  "totalMentions": 68
}
```

#### GET /api/visibility
Get monthly visibility data for charts.

#### GET /api/suggestions
Get AI-powered SEO improvement suggestions.

### Jobs

#### GET /api/jobs
List all scraping jobs. Supports `status` query parameter.

**Query Parameters:**
- `status` (optional): Filter by status (pending, running, completed, failed, scheduled)

#### POST /api/jobs/scrape
Create a new scraping job.

**Request (One-time):**
```json
{
  "query": "best seo tools",
  "country": "us",
  "num_results": 10,
  "scraper_type": "google_ai"
}
```

**Request (Scheduled):**
```json
{
  "query": "daily tracking",
  "country": "it",
  "frequency": "daily",
  "start_date": "2026-02-01T09:00:00"
}
```

**Response:**
```json
{
  "job_id": 123,
  "status": "scheduled",
  "next_run_at": "2026-02-01T09:00:00"
}
```

## Examples

See [Examples Documentation](./examples/README.md) for detailed request/response examples and code samples.

## Postman Collection

Import the Postman collection for easy testing:
- Collection: `postman/AiSEO_API.postman_collection.json`
- Environment: `postman/Local.postman_environment.json`

See [Postman Guide](./postman/README.md) for setup instructions.
