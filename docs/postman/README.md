# Postman Collection Guide

Complete guide for using the AiSEO API Postman collection.

## Quick Start

### Option 1: Download from API Tester (Recommended)

1. Start the API Tester:
   ```bash
   docker-compose up -d api-tester
   ```

2. Open http://localhost:9000

3. Click **"Download Postman Collection"** and **"Download Environment"** buttons in the sidebar

4. Import both files into Postman

### Option 2: Direct Download

- Collection: http://localhost:9000/postman/collection
- Environment: http://localhost:9000/postman/environment

### Option 3: Manual Import

1. **Import Collection**
   - Open Postman
   - Click **Import**
   - Select `api-tester/AiSEO_API.postman_collection.json`

2. **Import Environment**
   - Click **Environments** → **Import**
   - Select `api-tester/Local.postman_environment.json`
   - Select **Local** from environment dropdown

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Test API**
   - Navigate to **Backend API** → **Health Check**
   - Click **Send**

## Collection Structure

### Backend API

#### Health
- **Health Check** - Verify service is running

#### System
- **Get Config** - System configuration
- **Get VPN Servers** - Available VPN servers

#### Brands
- **List Brands** - Get all brands with metrics
- **Get Brand Details** - Detailed analytics
- **Create Brand** - Add new brand
- **Delete Brand** - Remove brand

#### Prompts
- **List Prompts** - Get all queries
- **Get Prompt Detail** - Detailed prompt info

#### Sources
- **List Sources** - Get all sources
- **Get Source Analytics** - Source metrics

#### Analytics
- **Get Metrics** - Dashboard KPIs
- **Get Visibility Data** - Monthly visibility
- **Get Suggestions** - SEO recommendations

#### Jobs
- **List Jobs** - All scraping jobs
- **Create Scrape Job (One-time)** - Immediate execution
- **Create Scrape Job (Scheduled)** - Recurring job

## Features

### Automated Tests

Each request includes tests that:
- Verify status codes
- Validate response structure
- Check required fields
- Save IDs for chained requests

### Environment Variables

- `backend_base_url` - Backend API URL (default: `http://localhost:8000`)
- `scraper_base_url` - Scraper API URL (default: `http://localhost:5000`)
- `last_job_id` - Auto-saved from job creation
- `last_brand_id` - Auto-saved from brand creation

## Usage Examples

### Complete Workflow

1. **Create Scraping Job**
   - Go to **Jobs** → **Create Scrape Job (One-time)**
   - Modify query if needed
   - Click **Send**
   - Note the `job_id` in response

2. **Check Job Status**
   - Go to **Jobs** → **List Jobs**
   - Add query param: `status=completed`
   - Click **Send**

3. **View Results**
   - Go to **Prompts** → **List Prompts**
   - Click **Send**
   - Find your query in results

4. **Check Brand Visibility**
   - Go to **Brands** → **List Brands**
   - Click **Send**
   - See visibility metrics

### Create and Test Brand

1. Go to **Brands** → **Create Brand**
2. Modify brand details
3. Click **Send**
4. Brand ID auto-saved to `{{last_brand_id}}`
5. Go to **Brands** → **List Brands**
6. Verify brand appears
7. Go to **Brands** → **Delete Brand**
8. Uses `{{last_brand_id}}` automatically

## Run in Postman Button

To add a "Run in Postman" button to your documentation:

1. Upload collection to Postman
2. Get collection URL from Postman
3. Add button link:
   ```markdown
   [![Run in Postman](https://run.pstmn.io/button.svg)](https://app.getpostman.com/run-collection/YOUR_COLLECTION_ID)
   ```

## Troubleshooting

### Connection Refused
- Ensure services running: `docker-compose ps`
- Check ports: `docker-compose port backend 8000`
- Verify environment variables

### Tests Failing
- Check response structure matches expectations
- Verify data exists in database
- Review test scripts for correct field names

### CORS Errors
- Ensure CORS enabled in backend
- Check `CORS_ORIGINS` environment variable

## Collection Files

- **Collection**: `../../postman/AiSEO_API.postman_collection.json`
- **Environment**: `../../postman/Local.postman_environment.json`
- **Documentation**: `../../postman/README.md`
