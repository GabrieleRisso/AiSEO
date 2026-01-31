# 🚀 Quick Start Guide - See Your APIs in Action!

## ✅ Services Running

Both APIs are now running:
- **Scraper API**: http://localhost:5000 ✅
- **Backend API**: http://localhost:8000 ✅

## 📚 Step 1: View FastAPI Documentation

### Option A: Swagger UI (Interactive)
Open in your browser:
```
http://localhost:8000/docs
```

**What you'll see:**
- All 18 backend API endpoints
- Try it out functionality
- Request/response examples
- Full documentation

### Option B: ReDoc (Beautiful Docs)
Open in your browser:
```
http://localhost:8000/redoc
```

**What you'll see:**
- Clean, readable documentation
- Searchable
- Mobile-friendly

### Option C: Scraper API Docs
Open in your browser:
```
http://localhost:5000/docs
```

**What you'll see:**
- Scraper API endpoints
- Scraping configuration
- Anti-detection features

## 🧪 Step 2: Test with cURL

### Test Health Endpoints

```bash
# Scraper API Health
curl http://localhost:5000/health

# Backend API Health
curl http://localhost:8000/api/health
```

**Expected Response:**
```json
{"status":"ok"}
{"status":"healthy","timestamp":"2026-01-31T18:36:32.114478"}
```

### Test Config Endpoints

```bash
# Get Scraper Config
curl http://localhost:5000/config

# Get Backend Config
curl http://localhost:8000/api/config
```

**Expected Response:**
```json
{
  "scrapers": ["google_ai", "perplexity", "brightdata"],
  "proxies": ["de", "es", "fr", "it", "nl", "se", "uk"],
  "default_scraper": "google_ai"
}
```

### Test Brands Endpoint

```bash
# List All Brands
curl http://localhost:8000/api/brands
```

**Expected Response:**
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

## 📬 Step 3: Use Postman Collection

### Import Collection

1. **Open Postman**
2. **Click Import** (top left)
3. **Select File**: `postman/AiSEO_API.postman_collection.json`
4. **Click Import**

### Import Environment

1. **Click Environments** (left sidebar)
2. **Click Import**
3. **Select File**: `postman/Local.postman_environment.json`
4. **Select "Local"** from dropdown (top right)

### Run Tests

1. **Click on Collection**: "AiSEO API Collection"
2. **Click "Run"** button (top right)
3. **Click "Run AiSEO API Collection"**
4. **View Results**: See all 22 tests run automatically!

### Test Individual Endpoints

1. **Expand Collection** → **Scraper API** → **Health Check**
2. **Click Send**
3. **See Response**: Status 200 OK with `{"status":"ok"}`
4. **Check Tests Tab**: See automated test results

## 🎯 Step 4: Try Interactive Examples

### Example 1: Get Dashboard Metrics

**In Swagger UI (http://localhost:8000/docs):**
1. Find **GET /api/metrics**
2. Click **Try it out**
3. Click **Execute**
4. See response with visibility, prompts, sources, position

### Example 2: List Brands

**In Swagger UI:**
1. Find **GET /api/brands**
2. Click **Try it out**
3. Click **Execute**
4. See all brands with visibility metrics

### Example 3: Create a Scrape Job

**In Swagger UI:**
1. Find **POST /api/jobs/scrape**
2. Click **Try it out**
3. Modify the example JSON:
   ```json
   {
     "query": "best seo tools",
     "country": "us",
     "scraper_type": "google_ai"
   }
   ```
4. Click **Execute**
5. See job created with job_id

## 📊 Step 5: View Test Results

### In Postman

After running the collection:
- **Green checkmarks** = Tests passed ✅
- **Red X** = Tests failed ❌
- **Test Results** show:
  - Status code checks
  - Response time
  - Field validation
  - Type checks

### Expected Results

All 22 endpoints should show:
- ✅ Status code is 200
- ✅ Response time is less than 5000ms
- ✅ Response is JSON
- ✅ Field validations pass

## 🔍 Step 6: Explore Endpoints

### Scraper API Endpoints

1. **GET /health** - Check service status
2. **GET /config** - Get scraper configuration
3. **POST /scrape** - Execute scraping job

### Backend API Endpoints

**System:**
- GET /api/health
- GET /api/config
- GET /api/vpn/servers

**Brands:**
- GET /api/brands
- GET /api/brands/details
- POST /api/brands
- DELETE /api/brands/{id}

**Prompts:**
- GET /api/prompts
- GET /api/prompts/{query_id}

**Sources:**
- GET /api/sources
- GET /api/sources/analytics

**Analytics:**
- GET /api/metrics
- GET /api/visibility
- GET /api/suggestions

**Jobs:**
- GET /api/jobs
- POST /api/jobs/scrape

## 🎨 Step 7: See Documentation Features

### In Swagger UI

- **Tags**: Endpoints organized by category
- **Schemas**: See request/response models
- **Examples**: Pre-filled example requests
- **Try it out**: Execute requests directly
- **Responses**: See example responses

### In Postman

- **Tests**: Automated validation
- **Pre-request Scripts**: Setup before requests
- **Variables**: Environment variables
- **Collections**: Organized folders
- **Documentation**: Built-in docs

## 🐛 Troubleshooting

### Services Not Responding?

```bash
# Check services
docker-compose ps

# View logs
docker-compose logs scraper
docker-compose logs backend

# Restart services
docker-compose restart scraper backend
```

### Ports Already in Use?

```bash
# Check what's using ports
lsof -i :5000
lsof -i :8000

# Stop conflicting services
docker-compose down
```

### Postman Tests Failing?

1. **Check Environment**: Ensure "Local" is selected
2. **Check URLs**: Verify `scraper_base_url` and `backend_base_url`
3. **Check Services**: Ensure APIs are running
4. **View Console**: Check Postman console for errors

## 📝 Next Steps

1. ✅ **View Docs**: Open http://localhost:8000/docs
2. ✅ **Import Postman**: Import collection and environment
3. ✅ **Run Tests**: Execute collection tests
4. ✅ **Try Endpoints**: Use Swagger UI to test
5. ✅ **Explore**: Check out different endpoints

## 🎉 You're Ready!

Everything is set up and running. Start exploring your APIs!

**Quick Links:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Scraper Docs: http://localhost:5000/docs
- Postman Collection: `postman/AiSEO_API.postman_collection.json`

Happy testing! 🚀
