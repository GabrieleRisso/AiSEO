# Quick Start - Postman Collection

## 🚀 3-Step Setup

### 1. Import Collection
- Postman → **Import** → Select `AiSEO_API.postman_collection.json`

### 2. Import Environment  
- Postman → **Environments** → **Import** → Select `Local.postman_environment.json`
- Select **Local** from dropdown (top right)

### 3. Test It!
- `Scraper API` → `Health Check` → **Send**
- Should see: `200 OK` with `{"status": "ok"}`

## ✅ Verify Services Running

```bash
docker-compose up -d scraper backend
```

## 📚 Full Documentation

- **Setup Guide**: [SETUP.md](./SETUP.md)
- **Collection Docs**: [README.md](./README.md)
- **API Docs**: [../API_DOCS.md](../API_DOCS.md)

## 🎯 Common Workflows

### Test Scraping
1. `Backend API` → `Jobs` → `Create Scrape Job (One-time)` → **Send**
2. `Backend API` → `Jobs` → `List Jobs` → **Send** (check status)
3. `Backend API` → `Prompts` → `List Prompts` → **Send** (see results)

### Test Brands
1. `Backend API` → `Brands` → `List Brands` → **Send**
2. `Backend API` → `Brands` → `Create Brand` → **Send**
3. `Backend API` → `Brands` → `List Brands` → **Send** (verify)

## 🔧 Troubleshooting

**Connection Refused?**
```bash
docker-compose ps  # Check services running
curl http://localhost:5000/health  # Test scraper
curl http://localhost:8000/api/health  # Test backend
```

**Variables Not Working?**
- Ensure **Local** environment is selected (top right)
- Check variable names match exactly

## 📦 What's Included

- ✅ 20+ API endpoints
- ✅ Automated tests
- ✅ Example requests
- ✅ Environment variables
- ✅ Documentation

Ready to test! 🎉
