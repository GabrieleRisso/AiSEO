# Postman Collection Integration

The Postman collection and environment files are now integrated into the API Tester.

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

## Importing into Postman

1. Open Postman
2. Click **Import** button (top left)
3. Import the collection file: `AiSEO_API.postman_collection.json`
4. Import the environment file: `Local.postman_environment.json`
5. Select **Local** from the environment dropdown (top right)

## Collection Structure

### Scraper API (Port 5000)
- Health Check
- Get Config
- Scrape (One-time)
- Scrape (With Anti-Detect)

### Backend API (Port 8000)
- **System**: Health, Config, VPN Servers
- **Brands**: List, Details, Create, Delete
- **Prompts**: List, Details
- **Sources**: List, Analytics
- **Analytics**: Metrics, Visibility, Suggestions
- **Jobs**: List, Create (One-time), Create (Scheduled)

## Environment Variables

The `Local` environment includes:
- `backend_base_url`: http://localhost:8000
- `scraper_base_url`: http://localhost:5000

## Testing

1. Make sure services are running:
   ```bash
   docker-compose up -d scraper backend
   ```

2. Start with **Scraper API** → **Health Check**
3. Then try **Backend API** → **Health Check**

## Notes

- All requests include automated tests
- Environment variables are auto-saved from responses
- Collection is kept in sync with API changes
