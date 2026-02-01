# AiSEO - AI Search Engine Optimization Dashboard

Track your brand's visibility in AI-generated search results. AiSEO scrapes Google AI Mode responses, analyzes brand mentions and citation patterns, and provides actionable SEO insights through an interactive dashboard.

## Overview

AiSEO is a full-stack application that:

1. **Scrapes** Google AI Mode responses for e-commerce queries
2. **Analyzes** which brands are mentioned and their positions
3. **Tracks** citation sources used by AI systems
4. **Visualizes** visibility trends over time in a dashboard
5. **Suggests** SEO improvements based on data patterns

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│     Frontend     │     │     Backend      │     │     Scraper      │
│  React + Vite    │◄───►│  FastAPI + SQLite│◄───►│  undetected-     │
│  TailwindCSS     │     │  SQLModel ORM    │     │  chromedriver    │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
   Dashboard UI            REST API (12          Google AI Mode
   localhost:5173          endpoints)            (udm=50 param)
                           localhost:8000
```

**Data Flow:**
```
Google AI Mode → Scraper → JSON files → Backend imports → SQLite DB → API → Dashboard
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Chrome browser

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Start the server
uvicorn main:app --reload --port 8000
```

API available at: http://localhost:8000
API docs at: http://localhost:8000/docs

## 📚 API Documentation

Complete API documentation is available in the `docs/` folder:

- **[API Reference](docs/api/README.md)** - Complete endpoint documentation
- **[Examples](docs/examples/README.md)** - Request/response examples and code samples
- **[Postman Collection](docs/postman/README.md)** - Postman setup and usage guide

**Interactive Documentation:**
- **Backend Swagger UI**: http://localhost:8000/docs
- **Backend ReDoc**: http://localhost:8000/redoc
- **Scraper API Docs**: http://localhost:5000/docs
- **Postman**: http://localhost:8000/docs/postman

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start development server
npm run dev
```

Dashboard available at: http://localhost:5173

### 3. Running the Scraper

```bash
# From project root (with venv activated)

# Basic scrape
python scripts/scrape_google_ai.py "best ecommerce platform"

# Headless mode (no browser window)
python scripts/scrape_google_ai.py "best ecommerce platform" --headless

# With debug screenshots
python scripts/scrape_google_ai.py "best ecommerce platform" --screenshot
```

Results saved to: `data/results/google/{query}.json`

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────────────┐       ┌─────────────┐
│   Brand     │       │ PromptBrandMention  │       │   Prompt    │
├─────────────┤       ├─────────────────────┤       ├─────────────┤
│ id (PK)     │◄──────│ brand_id (FK)       │       │ id (PK)     │
│ name        │       │ prompt_id (FK)      │──────►│ query       │
│ type        │       │ mentioned           │       │ run_number  │
│ color       │       │ position            │       │ response_txt│
│ variations  │       │ sentiment           │       │ scraped_at  │
└─────────────┘       │ context             │       └─────────────┘
                      └─────────────────────┘              │
                                                           │
┌─────────────┐       ┌─────────────────────┐              │
│   Source    │       │    PromptSource     │              │
├─────────────┤       ├─────────────────────┤              │
│ id (PK)     │◄──────│ source_id (FK)      │              │
│ domain      │       │ prompt_id (FK)      │──────────────┘
│ url (unique)│       │ citation_order      │
│ title       │       └─────────────────────┘
│ description │
│ published_dt│
└─────────────┘
```

### Tables

| Table | Description | Key Fields |
|-------|-------------|------------|
| **Brand** | Tracked brands (1 primary + competitors) | `id`, `name`, `type` (primary/competitor), `color`, `variations` |
| **Prompt** | Scraped query results | `query`, `run_number`, `response_text`, `scraped_at` |
| **PromptBrandMention** | Brand mentions per prompt | `position` (1=first), `sentiment`, `mentioned` (bool), `context` |
| **Source** | Cited websites | `domain`, `url` (unique), `title`, `description`, `published_date` |
| **PromptSource** | Links prompts to sources | `citation_order` |

### Tracked Brands (Default)

| Brand | Type | Color | Purpose |
|-------|------|-------|---------|
| Wix | primary | Cyan | Your brand (visibility focus) |
| Shopify | competitor | Amber | Main competitor |
| WooCommerce | competitor | Purple | Open-source competitor |
| BigCommerce | competitor | Pink | Enterprise competitor |
| Squarespace | competitor | Emerald | Design-focused competitor |

## API Endpoints

See [API Documentation](docs/API.md) for complete endpoint reference.

**Quick Links:**
- [API Reference](docs/api/README.md) - All endpoints
- [Examples](docs/examples/README.md) - Code samples
- [Postman Collection](docs/postman/README.md) - Testing guide

## 📁 Project Structure

```
AiSEO/
├── docs/                         # 📚 All API documentation
│   ├── api/                      # API endpoint reference
│   ├── examples/                 # Code examples
│   └── postman/                  # Postman collection
├── backend/                      # FastAPI backend
│   ├── main.py                   # API endpoints (1200+ lines)
│   ├── models.py                 # SQLModel ORM models
│   ├── schemas.py                # Pydantic response schemas
│   ├── database.py               # DB connection and init
│   ├── requirements.txt          # Python dependencies
│   ├── .env.example              # Environment template
│   ├── aiseo.db                  # SQLite database
│   ├── scripts/                  # Utility scripts (see scripts/README.md)
│   │   ├── seed_data.py          # Initial data seeding
│   │   ├── sync_brand_mentions.py # Re-sync brand detection
│   │   └── ...                   # Historical data scripts
│   └── backups/                  # Database exports
│       ├── database_export.json
│       └── aiseo.db.backup
│
├── frontend/                     # React dashboard
│   ├── src/
│   │   ├── App.tsx               # Main app component
│   │   ├── config.ts             # API configuration
│   │   ├── api/client.ts         # API client
│   │   ├── types/index.ts        # TypeScript interfaces
│   │   ├── pages/                # Route pages (6)
│   │   │   ├── Dashboard.tsx     # Main metrics dashboard
│   │   │   ├── Brands.tsx        # Brand management
│   │   │   ├── Prompts.tsx       # Query library
│   │   │   ├── Sources.tsx       # Citation analysis
│   │   │   ├── Suggestions.tsx   # SEO recommendations
│   │   │   └── Settings.tsx      # App settings
│   │   ├── components/           # Reusable components
│   │   │   ├── layout/           # Header, Sidebar, MobileNav
│   │   │   ├── ui/               # MetricCard, DataTable, Modal, Toast
│   │   │   ├── charts/           # VisibilityChart, BrandComparison
│   │   │   └── search/           # GlobalSearch, SearchResults
│   │   └── hooks/                # Custom React hooks (7)
│   ├── package.json
│   └── vite.config.ts
│
├── src/                          # Scraper library
│   ├── scrapers/
│   │   └── google_ai_scraper.py  # Main Google AI scraper
│   ├── config/settings.py        # Pydantic settings
│   └── utils/                    # Logger, exceptions
│
├── scripts/
│   └── scrape_google_ai.py       # CLI entry point
│
├── data/                         # Runtime data
│   ├── results/google/           # Scrape results (JSON)
│   └── screenshots/              # Debug screenshots
│
├── tests/                        # Test suites (empty)
├── pyproject.toml                # Python project config
└── .env.example                  # Root environment template
```

## Environment Variables

### Root `.env` (Scraper)

```bash
BROWSER_HEADLESS=false           # Show browser window during scrape
BROWSER_TIMEOUT_SECONDS=60       # Page load timeout
SCRAPER_TAKE_SCREENSHOTS=false   # Capture debug screenshots
LOG_LEVEL=INFO
```

### Backend `backend/.env`

```bash
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173  # Allowed origins
DATABASE_URL=                    # Optional: PostgreSQL connection string
LOG_LEVEL=INFO
DEBUG=false
```

### Frontend `frontend/.env`

```bash
VITE_API_BASE_URL=http://localhost:8000/api  # Backend API URL
```

## Key Concepts

### Visibility Score

Percentage of tracked queries where your brand is mentioned in the AI response.

```
Visibility = (queries_with_mention / total_queries) × 100
```

Position affects the visibility contribution:
- Position 1 (first mentioned) = 100%
- Position 2 = 80%
- Position 3 = 60%
- And so on...

### Sentiment Analysis

Brand mentions are classified as:
- **Positive**: Contains words like "excellent", "powerful", "recommended", "best"
- **Negative**: Contains words like "limited", "expensive", "complicated", "lacks"
- **Neutral**: Default when no sentiment keywords detected

### Source Classification

Cited sources are automatically categorized:
- **Brand**: Official brand sites (shopify.com, wix.com)
- **Blog**: Contains `/blog/` in URL, Medium, Dev.to
- **Community**: Reddit, Quora, Stack Exchange
- **News**: Forbes, TechCrunch, BusinessInsider
- **Review**: G2, Capterra, Trustpilot
- **Other**: Uncategorized

### Run (Multiple Scrapes)

The same query can be scraped multiple times to track changes:
- `run_number`: 1, 2, 3, etc.
- Allows trend analysis over time
- Dashboard aggregates across runs

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 19, TypeScript, Vite, TailwindCSS 4, Recharts, React Router 7 |
| **Backend** | FastAPI, SQLModel (Pydantic + SQLAlchemy), SQLite, Uvicorn |
| **Scraper** | undetected-chromedriver, Selenium, BeautifulSoup |
| **Styling** | Dark "Data Observatory" theme, CSS variables, Glassmorphism |

## Development

### Adding a New Brand

1. POST to `/api/brands`:
```json
{
  "id": "magento",
  "name": "Magento",
  "type": "competitor",
  "color": "#f97316",
  "variations": ["Magento", "Adobe Commerce", "magento.com"]
}
```

2. System automatically scans all existing prompts for mentions

### Running Utility Scripts

See `backend/scripts/README.md` for data management scripts.

### Building for Production

```bash
# Frontend build
cd frontend
npm run build
# Output: frontend/dist/

# Backend
# Use gunicorn or similar for production
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Scraper Details

The Google AI Mode scraper (`src/scrapers/google_ai_scraper.py`):

1. Uses `undetected-chromedriver` to avoid bot detection
2. Navigates to `google.com/search?udm=50&q={query}` (AI Mode)
3. Handles cookie consent dialogs automatically
4. Waits for AI response to generate (up to 60s)
5. Extracts response text (headings, lists, tables)
6. Extracts all source citations with metadata
7. Saves structured JSON to `data/results/google/`

## License

MIT
