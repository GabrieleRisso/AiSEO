# AiSEO API Documentation

## System Configuration

### GET /api/config
Returns available system configuration including supported scrapers and active proxies.

**Response:**
```json
{
  "scrapers": ["google_ai", "perplexity"],
  "proxies": ["fr", "de", "nl", "it", "es", "uk", "ch", "se"],
  "default_scraper": "google_ai"
}
```

### GET /api/vpn/servers
Returns the list of available ProtonVPN servers from the official Gluetun repository.

**Response:**
```json
{
  "provider": "protonvpn",
  "countries": ["Afghanistan", "Albania", ...],
  "total_servers": 1600,
  "active_proxies": ["fr", "de", "nl", "it", "es", "uk", "ch", "se"]
}
```

## Job Management

### POST /api/jobs/scrape
Triggers a new scraping job or schedules a recurring one.

**Request (One-time):**
```json
{
  "query": "best seo tools",
  "country": "us",
  "num_results": 10,
  "scraper_type": "google_ai", // or "perplexity"
  "device_type": "desktop", // desktop, mobile, tablet
  "os_type": "windows", // windows, mac, linux, android, ios
  "browser_type": "chrome",
  "human_behavior": true
}
```

**Request (Scheduled):**
```json
{
  "query": "daily tracking",
  "country": "it",
  "frequency": "daily", // daily, weekly, hourly
  "start_date": "2026-02-01T09:00:00" // Optional, defaults to now
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

### GET /api/jobs
List all jobs.

**Query Parameters:**
- `status`: Filter by status (pending, running, completed, failed, scheduled)

## Database Models

- **ScrapeJob**: Tracks the status, metadata, and errors of each scrape attempt.
  - `schedule_type`: "once" or "recurring"
  - `frequency`: Interval for recurring jobs
  - `next_run_at`: Timestamp for next execution
  - `parent_job_id`: ID of the original scheduled job (for recurring instances)
  - `config_snapshot`: JSON string of the request configuration.
  - `profile_data`: JSON string of the full anti-detect profile used.
  - `proxy_used`: The proxy URL used for the scrape.
  - `scraper_type`: The type of scraper used (e.g., "google_ai").

## Infrastructure

- **Database UI**: Access the SQLite database at `http://localhost:8080`.
- **VPNs**: Configured for FR, DE, NL, IT, ES, UK, CH, SE.
