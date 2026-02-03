# AISEO Roadmap

## Live Platform

| Service | URL | Status |
|---------|-----|--------|
| Frontend | app.tokenspender.com | ✅ Live |
| Backend API | api.tokenspender.com | ✅ Live |
| Admin | admin.tokenspender.com | ✅ Live |
| Scraper | scraper.tokenspender.com:5000 | ✅ Hetzner |
| Docs | docs.tokenspender.com | ✅ Live |

## Current Focus (Feb 2026)

### ✅ Completed
- Multi-scraper: Google AI, ChatGPT, Perplexity
- 8 VPN countries: IT, UK, FR, DE, ES, NL, CH, SE
- 4 proxy layers: direct, residential, unlocker, browser
- Brand tracking: 17 brands monitored
- Mobile scraping: Pixel 7, iPhone profiles

### 🔄 Active
- Italy market daily scraping (browser + mobile)
- Automated commits via Cyberdeck/OpenClaw
- Job scheduler: daily runs at 3 AM CET

## Weekly Dev (Cyberdeck)

**Mon/Wed/Fri @ 20:00 CET** - Auto-commit cycle:
1. Pull latest from origin
2. Pick ONE task from backlog
3. Implement & test
4. Update CHANGELOG.md
5. Commit with `[auto]` tag
6. Push

### Backlog (Priority Order)
1. [ ] Brand visibility trends chart
2. [ ] Export to CSV
3. [ ] Email digest reports
4. [ ] Perplexity scraper improvements
5. [ ] Multi-country comparison view
6. [ ] API rate limiting
7. [ ] User authentication

## API Quick Reference

```bash
# Create scrape job
curl -X POST https://api.tokenspender.com/api/jobs/scrape \
  -H "Content-Type: application/json" \
  -d '{"query":"best ecommerce platform","country":"it","proxy_layer":"browser","profile":"pixel_7"}'

# Check stats
curl https://api.tokenspender.com/api/stats/database

# List jobs
curl https://api.tokenspender.com/api/jobs?limit=10
```

## Costs

| Service | Monthly |
|---------|---------|
| Railway | ~$5-15 |
| Hetzner VPS | €4.51 |
| Bright Data | ~$5-10 |
| **Total** | **~$15-30** |

---

*Automated by Cyberdeck (OpenClaw) | GabrieleRisso*
