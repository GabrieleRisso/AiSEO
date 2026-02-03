# Changelog

All notable changes to AISEO are documented here.

## [Unreleased]

### Added
- Italy market scraper with browser mode
- Italian localized queries (20 queries)
- Multi-language query support
- Development roadmap (ROADMAP.md)
- Automated commits via Cyberdeck/OpenClaw

### Changed
- Scraper defaults to browser mode (higher success rate)
- Job scheduler improvements

---

## [0.3.0] - 2026-02-03

### Added
- 🇮🇹 **Italy Market Launch**
  - `setup_italy_jobs.py` - Italy-specific scraper
  - 20 Italian ecommerce queries
  - 5 English comparison queries
  - Browser mode for reliability

- 📊 **Development Infrastructure**
  - `ROADMAP.md` - Weekly development timeline
  - `CHANGELOG.md` - Version tracking
  - Automated commit workflow (Cyberdeck)

### Technical
- Proxy layer: `browser` (full automation)
- Country code: `it`
- Frequency: daily at 3 AM CET

---

## [0.2.0] - 2026-02-01

### Added
- UK market scraping (40 daily jobs)
- Google AI scraper
- ChatGPT scraper
- VPN integration (ProtonVPN)
- Brand mention tracking
- Basic React dashboard

---

## [0.1.0] - 2026-01-28

### Added
- Initial project setup
- FastAPI backend
- SQLite database
- Basic scraper framework
- Railway deployment config

---

## Commit Convention

Commits follow semantic format:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation
- `chore:` Maintenance
- `refactor:` Code improvements

Automated commits by Cyberdeck include `[auto]` tag.

---

*Maintained by Cyberdeck (OpenClaw) and GabrieleRisso*
