# GitHub Integration Guide

## 📦 What's Included

This Postman collection is ready for GitHub and includes:

- ✅ **AiSEO_API.postman_collection.json** - Complete API collection (22 endpoints)
- ✅ **Local.postman_environment.json** - Local development environment
- ✅ **README.md** - Full documentation
- ✅ **SETUP.md** - Detailed setup guide
- ✅ **QUICK_START.md** - Quick reference
- ✅ **validate.sh** - Validation script
- ✅ **.gitignore** - Excludes personal files
- ✅ **GitHub Actions** - Auto-validation on push

## 🚀 Getting Started

### For New Users

1. **Clone Repository**
   ```bash
   git clone <your-repo-url>
   cd aiseo/postman
   ```

2. **Import to Postman**
   - Open Postman
   - Import `AiSEO_API.postman_collection.json`
   - Import `Local.postman_environment.json`
   - Select **Local** environment

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Test**
   - `Scraper API` → `Health Check` → **Send**

### For Team Members

1. **Pull Latest**
   ```bash
   git pull
   ```

2. **Update Collection** (if changed)
   - Postman → **Import**
   - Select `AiSEO_API.postman_collection.json`
   - Choose **Replace** if updating existing

## 🔄 Syncing Changes

### Exporting from Postman

When you modify the collection in Postman:

1. **Export Collection**
   - Right-click collection → **Export**
   - Choose **Collection v2.1**
   - Save to `postman/AiSEO_API.postman_collection.json`
   - **Overwrite** existing file

2. **Export Environment** (if changed)
   - Right-click environment → **Export**
   - Save to `postman/Local.postman_environment.json`

3. **Validate**
   ```bash
   cd postman
   ./validate.sh
   ```

4. **Commit & Push**
   ```bash
   git add postman/
   git commit -m "Update Postman collection"
   git push
   ```

### Best Practices

- ✅ Always validate before committing
- ✅ Use descriptive commit messages
- ✅ Test endpoints after updating
- ✅ Update README if structure changes
- ❌ Never commit personal environments
- ❌ Never commit sensitive data

## 🤖 GitHub Actions

The repository includes automatic validation:

- **Triggers**: On push/PR to `postman/` directory
- **Validates**: JSON syntax, structure, endpoints
- **Status**: Check Actions tab in GitHub

### Manual Validation

```bash
cd postman
./validate.sh
```

## 📋 Collection Structure

```
AiSEO API Collection
├── Scraper API (4 endpoints)
│   ├── Health Check
│   ├── Get Config
│   ├── Scrape (One-time)
│   └── Scrape (With Anti-Detect)
│
└── Backend API (18 endpoints)
    ├── System (3)
    ├── Brands (4)
    ├── Prompts (2)
    ├── Sources (2)
    ├── Analytics (3)
    └── Jobs (4)
```

## 🔐 Security

### Environment Variables

- ✅ **Safe to Commit**: `Local.postman_environment.json` (no secrets)
- ❌ **Never Commit**: Personal environments with API keys
- ❌ **Never Commit**: Production credentials

### .gitignore

The `.gitignore` excludes:
- Personal environment files
- Local workspace files
- Sensitive configurations

## 📚 Documentation

- **Quick Start**: [QUICK_START.md](./QUICK_START.md)
- **Full Setup**: [SETUP.md](./SETUP.md)
- **Collection Docs**: [README.md](./README.md)
- **API Docs**: [../API_DOCS.md](../API_DOCS.md)

## 🆘 Troubleshooting

### Collection Won't Import

1. Validate JSON:
   ```bash
   python3 -m json.tool AiSEO_API.postman_collection.json
   ```

2. Check Postman version (needs v2.1 support)

3. Try importing via URL (if hosted)

### Tests Failing

1. Ensure services are running
2. Check environment variables
3. Verify endpoint URLs

### GitHub Actions Failing

1. Check Actions tab for error details
2. Run validation locally:
   ```bash
   cd postman && ./validate.sh
   ```
3. Verify JSON syntax

## 🎯 Next Steps

1. ✅ Import collection to Postman
2. ✅ Test endpoints
3. ✅ Customize for your needs
4. ✅ Share with team
5. ✅ Keep collection updated

## 📞 Support

- Check [SETUP.md](./SETUP.md) for detailed help
- Review [API_DOCS.md](../API_DOCS.md) for endpoint details
- Validate collection: `./validate.sh`

---

**Ready to test!** 🚀
