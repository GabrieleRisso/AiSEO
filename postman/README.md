# Postman Collection for AiSEO API

This directory contains Postman collections and environments for testing the AiSEO API services.

## Files

- **`AiSEO_API.postman_collection.json`** - Complete API collection with all endpoints, tests, and examples
- **`Local.postman_environment.json`** - Local development environment configuration

## Quick Start

### 1. Import Collection

1. Open Postman
2. Click **Import** button (top left)
3. Select **`AiSEO_API.postman_collection.json`**
4. Click **Import**

### 2. Import Environment

1. Click the **Environments** icon in the left sidebar
2. Click **Import**
3. Select **`Local.postman_environment.json`**
4. Click **Import**
5. Select **Local** from the environment dropdown (top right)

### 3. Start Services

Make sure your services are running:

```bash
docker-compose up -d
```

Or start specific services:

```bash
docker-compose up -d scraper backend
```

### 4. Test APIs

1. Navigate to **Scraper API** → **Health Check**
2. Click **Send**
3. You should see a 200 response with `{"status": "ok"}`

## Collection Structure

### Scraper API
- **Health Check** - Verify scraper service is running
- **Get Config** - Get available scrapers and proxies
- **Scrape (One-time)** - Execute immediate scraping job
- **Scrape (With Anti-Detect)** - Scrape with anti-detection features

### Backend API

#### System
- **Health Check** - Verify backend service is running
- **Get Config** - Get system configuration
- **Get VPN Servers** - List available VPN servers

#### Brands
- **List Brands** - Get all brands with metrics
- **Get Brand Details** - Detailed brand analytics
- **Create Brand** - Create new brand (auto-syncs mentions)
- **Delete Brand** - Delete brand and mentions

#### Prompts
- **List Prompts** - Get all queries with stats
- **Get Prompt Detail** - Detailed prompt with all runs

#### Sources
- **List Sources** - Get all sources with usage metrics
- **Get Source Analytics** - Detailed source analytics

#### Analytics
- **Get Metrics** - Dashboard KPIs
- **Get Visibility Data** - Monthly visibility charts
- **Get Suggestions** - AI SEO improvement suggestions

#### Jobs
- **List Jobs** - List all scraping jobs (with status filter)
- **Create Scrape Job (One-time)** - Immediate execution
- **Create Scrape Job (Scheduled Daily)** - Recurring job
- **Create Scrape Job (With Screenshot)** - With screenshot enabled

## Features

### Automated Tests

Most requests include automated tests that:
- Verify status codes
- Validate response structure
- Check required fields
- Save IDs for chained requests

### Environment Variables

The collection uses environment variables:
- `scraper_base_url` - Scraper API base URL (default: `http://localhost:5000`)
- `backend_base_url` - Backend API base URL (default: `http://localhost:8000`)
- `last_job_id` - Automatically saved from job creation
- `last_brand_id` - Automatically saved from brand creation

### Example Requests

Each endpoint includes:
- Pre-filled example requests
- Documentation
- Test scripts
- Variable usage

## Usage Examples

### Test Complete Workflow

1. **Create a Scrape Job**
   - Go to **Backend API** → **Jobs** → **Create Scrape Job (One-time)**
   - Modify the query if needed
   - Click **Send**
   - Note the `job_id` in the response

2. **Check Job Status**
   - Go to **Backend API** → **Jobs** → **List Jobs**
   - Add query parameter: `status=completed`
   - Click **Send**
   - Find your job in the list

3. **View Results**
   - Go to **Backend API** → **Prompts** → **List Prompts**
   - Click **Send**
   - Find your query in the results

4. **Check Brand Visibility**
   - Go to **Backend API** → **Brands** → **List Brands**
   - Click **Send**
   - See visibility metrics for all brands

### Test Anti-Detection Features

1. Go to **Scraper API** → **Scrape (With Anti-Detect)**
2. Modify the query and country
3. Set `use_residential_proxy: true` for residential proxy
4. Set `take_screenshot: true` to capture screenshots
5. Click **Send**
6. Check the response metadata for profile information

### Create and Test Brand

1. Go to **Backend API** → **Brands** → **Create Brand**
2. Modify the brand details
3. Click **Send**
4. The brand ID is automatically saved to `last_brand_id`
5. Go to **Backend API** → **Brands** → **List Brands**
6. Verify your brand appears
7. Go to **Backend API** → **Brands** → **Delete Brand**
8. The request uses `{{last_brand_id}}` automatically

## Customization

### Add New Environment

Create a new environment file (e.g., `Production.postman_environment.json`):

```json
{
	"name": "Production",
	"values": [
		{
			"key": "scraper_base_url",
			"value": "https://api.yourdomain.com:5000",
			"type": "default"
		},
		{
			"key": "backend_base_url",
			"value": "https://api.yourdomain.com:8000",
			"type": "default"
		}
	]
}
```

### Add Custom Tests

Edit any request and add tests in the **Tests** tab:

```javascript
pm.test("Custom test", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.customField).to.equal("expectedValue");
});
```

### Add Pre-request Scripts

Add scripts in the **Pre-request Script** tab:

```javascript
// Set dynamic timestamp
pm.environment.set("timestamp", new Date().toISOString());
```

## Troubleshooting

### Connection Refused

- Ensure services are running: `docker-compose ps`
- Check ports are exposed: `docker-compose port scraper 5000`
- Verify environment variables are set correctly

### Tests Failing

- Check response structure matches expectations
- Verify data exists in database
- Review test scripts for correct field names

### CORS Errors

- Ensure CORS is enabled in backend
- Check `CORS_ORIGINS` environment variable includes your origin

## Contributing

When adding new endpoints:

1. Add to appropriate folder in collection
2. Include example request body
3. Add automated tests
4. Update this README
5. Use environment variables for URLs

## Resources

- [Postman Documentation](https://learning.postman.com/docs/)
- [API Documentation](../API_DOCS.md)
- [Project README](../README.md)
