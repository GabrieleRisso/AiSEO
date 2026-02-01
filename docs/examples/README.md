# API Examples

Request and response examples for all API endpoints.

## Quick Start

```bash
# Health check
curl http://localhost:8000/api/health

# List brands
curl http://localhost:8000/api/brands

# Create scraping job
curl -X POST http://localhost:8000/api/jobs/scrape \
  -H "Content-Type: application/json" \
  -d '{"query": "best seo tools", "country": "us", "scraper_type": "google_ai"}'
```

## Examples by Category

### Health

#### Health Check
```bash
GET /api/health
```

**Response:**
```json
{
  "status": "ok"
}
```

### Brands

#### List Brands
```bash
GET /api/brands
```

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

#### Create Brand
```bash
POST /api/brands
Content-Type: application/json

{
  "id": "magento",
  "name": "Magento",
  "type": "competitor",
  "color": "#f97316",
  "variations": ["Magento", "Adobe Commerce"]
}
```

**Response:**
```json
{
  "id": "magento",
  "name": "Magento",
  "type": "competitor",
  "color": "#f97316",
  "variations": ["Magento", "Adobe Commerce"],
  "visibility": 0.0,
  "avgPosition": 0.0,
  "trend": "stable",
  "sentiment": "neutral",
  "totalMentions": 0,
  "totalPrompts": 0,
  "topPrompts": [],
  "visibilityByMonth": []
}
```

### Jobs

#### Create Scraping Job (One-time)
```bash
POST /api/jobs/scrape
Content-Type: application/json

{
  "query": "best e-commerce platform",
  "country": "us",
  "scraper_type": "google_ai",
  "num_results": 10
}
```

**Response:**
```json
{
  "job_id": 123,
  "status": "pending",
  "query": "best e-commerce platform",
  "created_at": "2026-02-01T10:00:00Z"
}
```

#### Create Scheduled Job
```bash
POST /api/jobs/scrape
Content-Type: application/json

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
  "job_id": 124,
  "status": "scheduled",
  "next_run_at": "2026-02-01T09:00:00",
  "frequency": "daily"
}
```

### Prompts

#### List Prompts
```bash
GET /api/prompts
```

**Response:**
```json
[
  {
    "query": "best seo tools",
    "totalRuns": 5,
    "latestRun": {
      "id": 1,
      "runNumber": 5,
      "scrapedAt": "2026-01-31T10:00:00Z",
      "visibility": 80.0,
      "avgPosition": 1.5,
      "totalMentions": 3
    }
  }
]
```

### Analytics

#### Get Metrics
```bash
GET /api/metrics
```

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

## Python Examples

### Using requests

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Health check
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# List brands
response = requests.get(f"{BASE_URL}/brands")
brands = response.json()
print(brands)

# Create scraping job
job_data = {
    "query": "best seo tools",
    "country": "us",
    "scraper_type": "google_ai"
}
response = requests.post(f"{BASE_URL}/jobs/scrape", json=job_data)
job = response.json()
print(f"Job ID: {job['job_id']}")
```

## JavaScript Examples

### Using fetch

```javascript
const BASE_URL = 'http://localhost:8000/api';

// Health check
fetch(`${BASE_URL}/health`)
  .then(res => res.json())
  .then(data => console.log(data));

// List brands
fetch(`${BASE_URL}/brands`)
  .then(res => res.json())
  .then(brands => console.log(brands));

// Create scraping job
fetch(`${BASE_URL}/jobs/scrape`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'best seo tools',
    country: 'us',
    scraper_type: 'google_ai'
  })
})
  .then(res => res.json())
  .then(job => console.log(`Job ID: ${job.job_id}`));
```

## Postman Collection

For more examples and automated tests, import the Postman collection:
- Collection: `../postman/AiSEO_API.postman_collection.json`
- Environment: `../postman/Local.postman_environment.json`

See [Postman Guide](../postman/README.md) for setup instructions.
