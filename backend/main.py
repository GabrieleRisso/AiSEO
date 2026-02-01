import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from sqlmodel import Session, select, func
from datetime import datetime, timedelta
from collections import Counter
from itertools import groupby
import requests
import json
from pydantic import BaseModel, Field

from database import create_db_and_tables, get_session, engine

# Scraper API URL - configurable for production vs local
SCRAPER_API_URL = os.getenv("SCRAPER_API_URL", "http://aiseo-scraper:5000")
from models import Brand, Prompt, PromptBrandMention, Source, PromptSource, ScrapeJob, DailyStats, PromptTemplate
from admin import setup_admin
from schemas import (
    BrandResponse,
    PromptResponse,
    PromptDetailResponse,
    PromptBrandMentionResponse,
    SourceResponse,
    SourceInPromptResponse,
    RunResponse,
    DashboardMetricsResponse,
    MetricResponse,
    DailyVisibilityResponse,
    SourcesAnalyticsResponse,
    SourcesSummary,
    DomainBreakdown,
    SourceType,
    TopSource,
    SuggestionsResponse,
    Suggestion,
    SuggestionExample,
    BrandCreate,
    BrandDetailResponse,
    BrandListResponse,
    BrandPromptDetail,
    BrandMonthlyVisibility,
)

app = FastAPI(
    title="AiSEO API",
    description="""
    # AiSEO API Documentation
    
    Backend API for AiSEO platform - Track brand visibility in AI-generated search results.
    
    ## Quick Start
    
    - **Interactive Docs**: [Swagger UI](/docs) | [ReDoc](/redoc)
    - **Postman Collection**: [Run in Postman](https://www.postman.com/collections/aiseo-api)
    - **Base URL**: `http://localhost:8000/api`
    
    ## Features
    
    - **Brand Management**: Track brand visibility and mentions across AI responses
    - **Prompt Analytics**: Analyze query performance and brand positioning  
    - **Source Analytics**: Track citation sources and domains
    - **Job Management**: Create and monitor scraping jobs
    - **Dashboard Metrics**: Get KPIs and visibility trends
    
    ## Authentication
    
    Currently no authentication required. All endpoints are publicly accessible.
    
    ## Rate Limiting
    
    No rate limiting currently implemented. Use responsibly.
    
    ## Examples
    
    See [Examples Documentation](/docs/examples) for request/response examples.
    """,
    version="1.0.0",
    contact={
        "name": "AiSEO API Support",
        "url": "https://github.com/yourorg/aiseo",
    },
    license_info={
        "name": "MIT",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Local development server",
        },
        {
            "url": "https://api.aiseo.example.com",
            "description": "Production server",
        },
    ],
    tags_metadata=[
        {
            "name": "health",
            "description": "Health check endpoints for service monitoring",
        },
        {
            "name": "system",
            "description": "System configuration and VPN server information",
        },
        {
            "name": "brands",
            "description": "Brand management and analytics endpoints. Track brand visibility, mentions, and sentiment across AI responses.",
        },
        {
            "name": "prompts",
            "description": "Prompt and query management endpoints. View scraped queries and their results.",
        },
        {
            "name": "sources",
            "description": "Source and citation management endpoints. Track which websites are cited by AI systems.",
        },
        {
            "name": "analytics",
            "description": "Analytics, metrics, and reporting endpoints. Get KPIs, visibility trends, and SEO suggestions.",
        },
        {
            "name": "jobs",
            "description": "Scraping job management endpoints. Create and monitor scraping jobs for tracking brand visibility.",
        },
    ],
)

# CORS for frontend and admin dashboard - read from environment variable
cors_origins = os.getenv(
    "CORS_ORIGINS", 
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:9091,http://127.0.0.1:9091,http://localhost:8000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware required for SQLAdmin authentication
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "change-me-in-production-secret-key")
)

# Setup SQLAdmin database viewer at /admin
# Access the UI at http://localhost:8000/admin
setup_admin(app, engine)

# Custom ReDoc with Postman button
@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """Custom ReDoc page with Postman integration."""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>AiSEO API Documentation - ReDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {
            margin: 0;
            padding: 0;
        }
        .postman-button {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            background: #FF6C37;
            color: white;
            padding: 12px 24px;
            border-radius: 4px;
            text-decoration: none;
            font-family: 'Roboto', sans-serif;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            transition: background 0.3s;
        }
        .postman-button:hover {
            background: #E55A2B;
        }
        .docs-links {
            position: fixed;
            top: 70px;
            right: 20px;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .docs-link {
            background: #4A90E2;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            text-decoration: none;
            font-family: 'Roboto', sans-serif;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            transition: background 0.3s;
        }
        .docs-link:hover {
            background: #357ABD;
        }
    </style>
</head>
<body>
    <a href="/docs/postman" target="_blank" class="postman-button">
        🚀 Run in Postman
    </a>
    <div class="docs-links">
        <a href="/docs" class="docs-link">Swagger UI</a>
        <a href="/docs/examples" class="docs-link">Examples</a>
    </div>
    <redoc spec-url='/openapi.json'></redoc>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

# Serve static docs if directory exists (relative to project root)
docs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
if os.path.exists(docs_path):
    app.mount("/docs", StaticFiles(directory=docs_path, html=True), name="docs")

# Postman collection endpoint (redirects to api-tester)
@app.get("/docs/postman", include_in_schema=False)
async def postman_collection():
    """Postman collection download page - redirects to api-tester."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="http://localhost:9000/postman/collection")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    seed_brands()


def seed_brands():
    """
    Seed initial brand data if database is empty.
    
    Creates default brands for tracking:
    - Primary brand: TokenSpender
    - Competitors: GEO/AI SEO industry competitors
    
    Handles race conditions when multiple workers start simultaneously.
    Uses merge() to safely insert/update brands.
    """
    from sqlmodel import Session
    from database import engine

    brands_data = [
        {"id": "tokenspender", "name": "TokenSpender", "type": "primary", "color": "#06b6d4"},
        {"id": "profound", "name": "Profound", "type": "competitor", "color": "#f59e0b"},
        {"id": "airops", "name": "AirOps", "type": "competitor", "color": "#8b5cf6"},
        {"id": "ahrefs", "name": "Ahrefs", "type": "competitor", "color": "#ec4899"},
        {"id": "otterly-ai", "name": "Otterly.AI", "type": "competitor", "color": "#10b981"},
    ]

    with Session(engine) as session:
        # Only seed if no brands exist
        existing_brands = session.exec(select(Brand)).first()
        if existing_brands:
            return  # Don't overwrite existing brands
            
        for brand_data in brands_data:
            brand = Brand(**brand_data)
            session.merge(brand)
        try:
            session.commit()
        except Exception:
            # Ignore errors from concurrent seeding (race condition)
            session.rollback()


def get_run_data(session: Session, prompt: Prompt, brands: list[Brand]) -> RunResponse:
    """
    Build run response data for a single prompt/scrape run.
    
    Aggregates data from:
    - Brand mentions (position, sentiment, mentioned status)
    - Sources (citations with order)
    - Visibility calculation (based on primary brand position)
    
    Args:
        session: Database session
        prompt: Prompt/run to process
        brands: List of all brands to check for mentions
    
    Returns:
        RunResponse: Complete run data with brands, sources, and metrics
    """
    mentions = session.exec(
        select(PromptBrandMention).where(PromptBrandMention.prompt_id == prompt.id)
    ).all()

    brand_responses = []
    for brand in brands:
        mention = next((m for m in mentions if m.brand_id == brand.id), None)
        brand_responses.append(
            PromptBrandMentionResponse(
                brandId=brand.id,
                brandName=brand.name,
                position=mention.position if mention and mention.mentioned else 0,
                mentioned=mention.mentioned if mention else False,
                sentiment=mention.sentiment if mention and mention.sentiment else "neutral",
            )
        )

    # Get sources
    prompt_sources = session.exec(
        select(PromptSource).where(PromptSource.prompt_id == prompt.id)
    ).all()
    source_responses = []
    for ps in prompt_sources:
        source = session.get(Source, ps.source_id)
        if source:
            source_responses.append(
                SourceInPromptResponse(
                    domain=source.domain,
                    url=source.url,
                    title=source.title,
                    description=source.description,
                    publishedDate=source.published_date,
                    citationOrder=ps.citation_order,
                )
            )
    source_responses.sort(key=lambda x: x.citationOrder)

    mentioned_brands = [b for b in brand_responses if b.mentioned]

    # Calculate visibility based on primary brand (if exists) or Wix as fallback
    primary_brand = next((b for b in brands if b.type == "primary"), None)
    primary_brand_id = primary_brand.id if primary_brand else "wix"
    
    primary_mention = next((b for b in brand_responses if b.brandId == primary_brand_id), None)
    if primary_mention and primary_mention.mentioned and primary_mention.position > 0:
        # Position 1 = 100%, Position 2 = 80%, Position 3 = 60%, etc.
        visibility = max(0, 100 - (primary_mention.position - 1) * 20)
    else:
        visibility = 0  # Not mentioned

    # Use primary position
    avg_position = primary_mention.position if primary_mention and primary_mention.mentioned else 0

    return RunResponse(
        id=prompt.id,
        runNumber=prompt.run_number if hasattr(prompt, 'run_number') else 1,
        scrapedAt=prompt.scraped_at.isoformat() if prompt.scraped_at else "",
        visibility=visibility,
        avgPosition=round(avg_position, 1),
        totalMentions=len(mentioned_brands),
        brands=brand_responses,
        responseText=prompt.response_text,
        sources=source_responses,
    )


@app.get(
    "/api/brands",
    tags=["brands"],
    summary="List all brands",
    description="""
    Get all brands with computed visibility metrics for January 2026.
    
    Metrics include:
    - **Visibility**: Percentage of prompts mentioning the brand
    - **Average Position**: Average position when mentioned
    - **Trend**: Month-over-month trend (up/down/stable)
    - **Sentiment**: Most common sentiment
    
    Brands are sorted with primary brand first, then by visibility descending.
    """,
    response_model=list[BrandResponse],
    responses={
        200: {
            "description": "List of brands with metrics",
            "content": {
                "application/json": {
                    "example": [
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
                }
            }
        }
    }
)
def get_brands(session: Session = Depends(get_session)):
    """
    Get all brands with computed metrics.
    
    Calculates visibility based on January 2026 prompts only.
    Trend is calculated by comparing January vs December 2025 visibility.
    """
    brands = session.exec(select(Brand)).all()

    # Get prompts by month
    all_prompts = session.exec(select(Prompt)).all()
    jan_prompts = [p for p in all_prompts if p.scraped_at and p.scraped_at.strftime("%Y-%m") == "2026-01"]
    dec_prompts = [p for p in all_prompts if p.scraped_at and p.scraped_at.strftime("%Y-%m") == "2025-12"]

    jan_queries = set(p.query for p in jan_prompts)
    dec_queries = set(p.query for p in dec_prompts)
    total_jan_queries = len(jan_queries)
    total_dec_queries = len(dec_queries)

    result = []
    for brand in brands:
        # Get January mentions
        jan_mentioned_queries = set()
        jan_positions = []
        jan_sentiments = []

        for prompt in jan_prompts:
            mention = session.exec(
                select(PromptBrandMention).where(
                    PromptBrandMention.prompt_id == prompt.id,
                    PromptBrandMention.brand_id == brand.id,
                    PromptBrandMention.mentioned == True,
                )
            ).first()
            if mention:
                jan_mentioned_queries.add(prompt.query)
                if mention.position:
                    jan_positions.append(mention.position)
                if mention.sentiment:
                    jan_sentiments.append(mention.sentiment)

        jan_visibility = (len(jan_mentioned_queries) / total_jan_queries * 100) if total_jan_queries > 0 else 0
        avg_position = sum(jan_positions) / len(jan_positions) if jan_positions else 0
        most_common_sentiment = (
            Counter(jan_sentiments).most_common(1)[0][0] if jan_sentiments else "neutral"
        )

        # Get December mentions for trend calculation
        dec_mentioned_queries = set()
        for prompt in dec_prompts:
            mention = session.exec(
                select(PromptBrandMention).where(
                    PromptBrandMention.prompt_id == prompt.id,
                    PromptBrandMention.brand_id == brand.id,
                    PromptBrandMention.mentioned == True,
                )
            ).first()
            if mention:
                dec_mentioned_queries.add(prompt.query)

        dec_visibility = (len(dec_mentioned_queries) / total_dec_queries * 100) if total_dec_queries > 0 else 0

        # Determine trend by comparing Jan vs Dec visibility
        trend = "stable"
        if jan_visibility > dec_visibility + 2:  # +2% threshold to avoid noise
            trend = "up"
        elif jan_visibility < dec_visibility - 2:
            trend = "down"

        result.append(
            BrandResponse(
                id=brand.id,
                name=brand.name,
                type=brand.type,
                color=brand.color,
                visibility=round(jan_visibility, 1),
                avgPosition=round(avg_position, 1),
                trend=trend,
                sentiment=most_common_sentiment,
            )
        )

    # Sort: primary brand first, then by visibility descending
    result.sort(key=lambda x: (x.type != "primary", -x.visibility))
    return result


@app.get(
    "/api/brands/details",
    tags=["brands"],
    summary="Get detailed brand analytics",
    description="""
    Get comprehensive brand analytics with monthly breakdown.
    
    Includes:
    - Current month metrics (January 2026)
    - Monthly visibility trends (Sep 2025 - Jan 2026)
    - Top prompts where brand is mentioned
    - Total mentions across all time
    - Brand variations and search terms
    """,
    response_model=BrandListResponse,
    responses={
        200: {
            "description": "Detailed brand analytics",
        }
    }
)
def get_brands_details(session: Session = Depends(get_session)):
    """
    Get detailed brand analytics for brand management page.
    
    Provides comprehensive analytics including monthly trends,
    top prompts, and total mention counts.
    """
    brands = session.exec(select(Brand)).all()
    all_prompts = session.exec(select(Prompt)).all()

    # Group prompts by month
    months_order = ["Sep 2025", "Oct 2025", "Nov 2025", "Dec 2025", "Jan 2026"]
    month_map = {
        "2025-09": "Sep 2025",
        "2025-10": "Oct 2025",
        "2025-11": "Nov 2025",
        "2025-12": "Dec 2025",
        "2026-01": "Jan 2026",
    }

    prompts_by_month = {m: [] for m in months_order}
    for prompt in all_prompts:
        if prompt.scraped_at:
            month_key = prompt.scraped_at.strftime("%Y-%m")
            if month_key in month_map:
                prompts_by_month[month_map[month_key]].append(prompt)

    # January prompts for current stats
    jan_prompts = prompts_by_month.get("Jan 2026", [])
    dec_prompts = prompts_by_month.get("Dec 2025", [])
    jan_queries = set(p.query for p in jan_prompts)
    dec_queries = set(p.query for p in dec_prompts)

    result = []
    for brand in brands:
        # Parse variations
        variations = brand.variations.split(",") if brand.variations else [brand.name]
        variations = [v.strip() for v in variations if v.strip()]

        # Get January mentions for current stats
        jan_mentioned_queries = set()
        jan_positions = []
        jan_sentiments = []
        top_prompts = []

        for prompt in jan_prompts:
            mention = session.exec(
                select(PromptBrandMention).where(
                    PromptBrandMention.prompt_id == prompt.id,
                    PromptBrandMention.brand_id == brand.id,
                    PromptBrandMention.mentioned == True,
                )
            ).first()
            if mention:
                jan_mentioned_queries.add(prompt.query)
                if mention.position:
                    jan_positions.append(mention.position)
                if mention.sentiment:
                    jan_sentiments.append(mention.sentiment)
                top_prompts.append(BrandPromptDetail(
                    query=prompt.query,
                    position=mention.position,
                    sentiment=mention.sentiment,
                    scrapedAt=prompt.scraped_at.isoformat() if prompt.scraped_at else ""
                ))

        # Deduplicate top_prompts by query, keep best position
        unique_prompts = {}
        for tp in top_prompts:
            if tp.query not in unique_prompts or (tp.position and (not unique_prompts[tp.query].position or tp.position < unique_prompts[tp.query].position)):
                unique_prompts[tp.query] = tp
        top_prompts = sorted(unique_prompts.values(), key=lambda x: x.position if x.position else 999)[:10]

        jan_visibility = (len(jan_mentioned_queries) / len(jan_queries) * 100) if jan_queries else 0
        avg_position = sum(jan_positions) / len(jan_positions) if jan_positions else 0
        most_common_sentiment = Counter(jan_sentiments).most_common(1)[0][0] if jan_sentiments else "neutral"

        # Calculate December visibility for trend
        dec_mentioned_queries = set()
        for prompt in dec_prompts:
            mention = session.exec(
                select(PromptBrandMention).where(
                    PromptBrandMention.prompt_id == prompt.id,
                    PromptBrandMention.brand_id == brand.id,
                    PromptBrandMention.mentioned == True,
                )
            ).first()
            if mention:
                dec_mentioned_queries.add(prompt.query)

        dec_visibility = (len(dec_mentioned_queries) / len(dec_queries) * 100) if dec_queries else 0

        trend = "stable"
        if jan_visibility > dec_visibility + 2:
            trend = "up"
        elif jan_visibility < dec_visibility - 2:
            trend = "down"

        # Calculate visibility by month
        visibility_by_month = []
        for month_name in months_order:
            month_prompts = prompts_by_month.get(month_name, [])
            month_queries = set(p.query for p in month_prompts)

            mentioned_queries = set()
            for prompt in month_prompts:
                mention = session.exec(
                    select(PromptBrandMention).where(
                        PromptBrandMention.prompt_id == prompt.id,
                        PromptBrandMention.brand_id == brand.id,
                        PromptBrandMention.mentioned == True,
                    )
                ).first()
                if mention:
                    mentioned_queries.add(prompt.query)

            month_visibility = (len(mentioned_queries) / len(month_queries) * 100) if month_queries else 0
            visibility_by_month.append(BrandMonthlyVisibility(
                month=month_name,
                visibility=round(month_visibility, 1)
            ))

        # Count total mentions across all time
        total_mentions = session.exec(
            select(func.count(PromptBrandMention.id)).where(
                PromptBrandMention.brand_id == brand.id,
                PromptBrandMention.mentioned == True,
            )
        ).one()

        result.append(BrandDetailResponse(
            id=brand.id,
            name=brand.name,
            type=brand.type,
            color=brand.color,
            variations=variations,
            visibility=round(jan_visibility, 1),
            avgPosition=round(avg_position, 1),
            trend=trend,
            sentiment=most_common_sentiment,
            totalMentions=total_mentions,
            totalPrompts=len(jan_mentioned_queries),
            topPrompts=top_prompts,
            visibilityByMonth=visibility_by_month
        ))

    # Sort: primary brand first, then by visibility descending
    result.sort(key=lambda x: (x.type != "primary", -x.visibility))
    return BrandListResponse(brands=result)


@app.post(
    "/api/brands",
    tags=["brands"],
    summary="Create a new brand",
    description="""
    Create a new brand and automatically sync mentions from all existing prompts.
    
    The system will:
    1. Create the brand record
    2. Scan all existing prompts for brand mentions
    3. Create mention records with position and sentiment
    4. Return the created brand with analytics
    
    **Brand ID Format:**
    - Lowercase, no spaces
    - Use hyphens for multi-word names
    - Example: "adobe-commerce", "shopify-plus"
    
    **Brand Types:**
    - `primary`: Your main brand (only one allowed)
    - `competitor`: Competitor brands
    """,
    response_model=BrandDetailResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Brand created successfully",
        },
        400: {
            "description": "Brand ID already exists",
            "content": {
                "application/json": {
                    "example": {"detail": "Brand with ID 'wix' already exists"}
                }
            }
        }
    }
)
def create_brand(brand_data: BrandCreate, session: Session = Depends(get_session)):
    """
    Create a new brand and sync mentions from existing prompts.
    
    Automatically detects brand mentions in all existing prompt responses
    and creates mention records with position and sentiment analysis.
    """
    import re

    # Check if brand already exists
    existing = session.get(Brand, brand_data.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Brand with ID '{brand_data.id}' already exists")

    # Create the brand
    variations_str = ",".join(brand_data.variations) if brand_data.variations else brand_data.name
    new_brand = Brand(
        id=brand_data.id,
        name=brand_data.name,
        type=brand_data.type,
        color=brand_data.color,
        variations=variations_str
    )
    session.add(new_brand)
    session.commit()
    session.refresh(new_brand)

    # Sync mentions for all existing prompts
    all_prompts = session.exec(select(Prompt)).all()
    search_terms = brand_data.variations if brand_data.variations else [brand_data.name]

    for prompt in all_prompts:
        if not prompt.response_text:
            continue

        response_lower = prompt.response_text.lower()

        # Check if any variation is mentioned
        mentioned = False
        position = None
        context = None

        for term in search_terms:
            if term.lower() in response_lower:
                mentioned = True
                # Find position (simple: count newlines before first mention)
                idx = response_lower.find(term.lower())
                # Estimate position by checking for numbered lists or paragraph position
                before_text = response_lower[:idx]
                # Count how many other brands appear before
                brands = session.exec(select(Brand)).all()
                other_brands_before = 0
                for b in brands:
                    b_variations = b.variations.split(",") if b.variations else [b.name]
                    for bv in b_variations:
                        bv_idx = response_lower.find(bv.lower())
                        if 0 <= bv_idx < idx:
                            other_brands_before += 1
                            break
                position = other_brands_before + 1

                # Extract context (50 chars before and after)
                start = max(0, idx - 50)
                end = min(len(prompt.response_text), idx + len(term) + 50)
                context = prompt.response_text[start:end]
                break

        # Create mention record
        mention = PromptBrandMention(
            prompt_id=prompt.id,
            brand_id=new_brand.id,
            mentioned=mentioned,
            position=position if mentioned else None,
            sentiment="neutral",  # Default sentiment
            context=context
        )
        session.add(mention)

    session.commit()

    # Return the brand details
    return get_brand_detail(new_brand.id, session)


def get_brand_detail(brand_id: str, session: Session) -> BrandDetailResponse:
    """Helper to get brand detail response"""
    brand = session.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    all_prompts = session.exec(select(Prompt)).all()

    # January prompts
    jan_prompts = [p for p in all_prompts if p.scraped_at and p.scraped_at.strftime("%Y-%m") == "2026-01"]
    dec_prompts = [p for p in all_prompts if p.scraped_at and p.scraped_at.strftime("%Y-%m") == "2025-12"]
    jan_queries = set(p.query for p in jan_prompts)
    dec_queries = set(p.query for p in dec_prompts)

    variations = brand.variations.split(",") if brand.variations else [brand.name]
    variations = [v.strip() for v in variations if v.strip()]

    # Get January mentions
    jan_mentioned_queries = set()
    jan_positions = []
    jan_sentiments = []
    top_prompts = []

    for prompt in jan_prompts:
        mention = session.exec(
            select(PromptBrandMention).where(
                PromptBrandMention.prompt_id == prompt.id,
                PromptBrandMention.brand_id == brand.id,
                PromptBrandMention.mentioned == True,
            )
        ).first()
        if mention:
            jan_mentioned_queries.add(prompt.query)
            if mention.position:
                jan_positions.append(mention.position)
            if mention.sentiment:
                jan_sentiments.append(mention.sentiment)
            top_prompts.append(BrandPromptDetail(
                query=prompt.query,
                position=mention.position,
                sentiment=mention.sentiment,
                scrapedAt=prompt.scraped_at.isoformat() if prompt.scraped_at else ""
            ))

    unique_prompts = {}
    for tp in top_prompts:
        if tp.query not in unique_prompts or (tp.position and (not unique_prompts[tp.query].position or tp.position < unique_prompts[tp.query].position)):
            unique_prompts[tp.query] = tp
    top_prompts = sorted(unique_prompts.values(), key=lambda x: x.position if x.position else 999)[:10]

    jan_visibility = (len(jan_mentioned_queries) / len(jan_queries) * 100) if jan_queries else 0
    avg_position = sum(jan_positions) / len(jan_positions) if jan_positions else 0
    most_common_sentiment = Counter(jan_sentiments).most_common(1)[0][0] if jan_sentiments else "neutral"

    dec_mentioned_queries = set()
    for prompt in dec_prompts:
        mention = session.exec(
            select(PromptBrandMention).where(
                PromptBrandMention.prompt_id == prompt.id,
                PromptBrandMention.brand_id == brand.id,
                PromptBrandMention.mentioned == True,
            )
        ).first()
        if mention:
            dec_mentioned_queries.add(prompt.query)

    dec_visibility = (len(dec_mentioned_queries) / len(dec_queries) * 100) if dec_queries else 0

    trend = "stable"
    if jan_visibility > dec_visibility + 2:
        trend = "up"
    elif jan_visibility < dec_visibility - 2:
        trend = "down"

    # Visibility by month
    months_order = ["Sep 2025", "Oct 2025", "Nov 2025", "Dec 2025", "Jan 2026"]
    month_map = {
        "2025-09": "Sep 2025",
        "2025-10": "Oct 2025",
        "2025-11": "Nov 2025",
        "2025-12": "Dec 2025",
        "2026-01": "Jan 2026",
    }

    prompts_by_month = {m: [] for m in months_order}
    for prompt in all_prompts:
        if prompt.scraped_at:
            month_key = prompt.scraped_at.strftime("%Y-%m")
            if month_key in month_map:
                prompts_by_month[month_map[month_key]].append(prompt)

    visibility_by_month = []
    for month_name in months_order:
        month_prompts = prompts_by_month.get(month_name, [])
        month_queries = set(p.query for p in month_prompts)

        mentioned_queries = set()
        for prompt in month_prompts:
            mention = session.exec(
                select(PromptBrandMention).where(
                    PromptBrandMention.prompt_id == prompt.id,
                    PromptBrandMention.brand_id == brand.id,
                    PromptBrandMention.mentioned == True,
                )
            ).first()
            if mention:
                mentioned_queries.add(prompt.query)

        month_visibility = (len(mentioned_queries) / len(month_queries) * 100) if month_queries else 0
        visibility_by_month.append(BrandMonthlyVisibility(
            month=month_name,
            visibility=round(month_visibility, 1)
        ))

    total_mentions = session.exec(
        select(func.count(PromptBrandMention.id)).where(
            PromptBrandMention.brand_id == brand.id,
            PromptBrandMention.mentioned == True,
        )
    ).one()

    return BrandDetailResponse(
        id=brand.id,
        name=brand.name,
        type=brand.type,
        color=brand.color,
        variations=variations,
        visibility=round(jan_visibility, 1),
        avgPosition=round(avg_position, 1),
        trend=trend,
        sentiment=most_common_sentiment,
        totalMentions=total_mentions,
        totalPrompts=len(jan_mentioned_queries),
        topPrompts=top_prompts,
        visibilityByMonth=visibility_by_month
    )


@app.delete(
    "/api/brands/{brand_id}",
    tags=["brands"],
    summary="Delete a brand",
    description="""
    Delete a brand and all its mention records.
    
    **Warning:** This operation cannot be undone.
    
    **Restrictions:**
    - Cannot delete primary brand (type='primary')
    - All mention records will be permanently deleted
    """,
    responses={
        200: {
            "description": "Brand deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Brand 'test-brand' deleted successfully"
                    }
                }
            }
        },
        400: {
            "description": "Cannot delete primary brand",
            "content": {
                "application/json": {
                    "example": {"detail": "Cannot delete primary brand"}
                }
            }
        },
        404: {
            "description": "Brand not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Brand not found"}
                }
            }
        }
    }
)
def delete_brand(brand_id: str, session: Session = Depends(get_session)):
    """
    Delete a brand and all its mentions.
    
    Permanently removes the brand and all associated mention records.
    Primary brands cannot be deleted.
    """
    brand = session.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Prevent deleting primary brand
    if brand.type == "primary":
        raise HTTPException(status_code=400, detail="Cannot delete primary brand")

    # Delete all mentions for this brand
    mentions = session.exec(
        select(PromptBrandMention).where(PromptBrandMention.brand_id == brand_id)
    ).all()
    for mention in mentions:
        session.delete(mention)

    # Delete the brand
    session.delete(brand)
    session.commit()

    return {"success": True, "message": f"Brand '{brand_id}' deleted successfully"}


@app.put(
    "/api/brands/{brand_id}/set-primary",
    tags=["brands"],
    summary="Set a brand as primary",
    description="Sets the specified brand as the primary brand. Only one brand can be primary at a time.",
)
def set_brand_primary(brand_id: str, session: Session = Depends(get_session)):
    """Set a brand as the primary brand, demoting the current primary to competitor."""
    brand = session.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Demote current primary brand(s) to competitor
    current_primaries = session.exec(select(Brand).where(Brand.type == "primary")).all()
    for primary in current_primaries:
        primary.type = "competitor"
        session.add(primary)
    
    # Set new primary
    brand.type = "primary"
    session.add(brand)
    session.commit()
    
    return {"success": True, "message": f"Brand '{brand.name}' is now the primary brand"}


@app.get(
    "/api/prompts",
    tags=["prompts"],
    summary="List all prompts",
    description="""
    Get all unique queries with aggregated statistics across all runs.
    
    For each query, returns:
    - Average visibility across all runs
    - Average position across all runs
    - Total number of runs
    - Aggregated brand mentions (mentioned if mentioned in ANY run)
    
    Results are grouped by query, with metrics averaged across all runs.
    """,
    response_model=list[PromptResponse],
    responses={
        200: {
            "description": "List of prompts with aggregated stats",
        }
    }
)
def get_prompts(session: Session = Depends(get_session)):
    """
    Get all unique queries with aggregated stats across runs.
    
    Groups prompts by query and calculates average metrics
    across all runs for each query.
    """
    all_prompts = session.exec(select(Prompt).order_by(Prompt.query, Prompt.run_number)).all()
    brands = session.exec(select(Brand)).all()

    # Group prompts by query
    grouped = {}
    for prompt in all_prompts:
        if prompt.query not in grouped:
            grouped[prompt.query] = []
        grouped[prompt.query].append(prompt)

    result = []
    for idx, (query, prompts_list) in enumerate(grouped.items(), 1):
        # Use the latest run for brand data display
        latest_prompt = max(prompts_list, key=lambda p: p.run_number if hasattr(p, 'run_number') else 1)

        # Calculate aggregated stats across all runs
        all_visibilities = []
        all_positions = []
        all_mentions_count = []

        for prompt in prompts_list:
            mentions = session.exec(
                select(PromptBrandMention).where(PromptBrandMention.prompt_id == prompt.id)
            ).all()

            brand_responses = []
            for brand in brands:
                mention = next((m for m in mentions if m.brand_id == brand.id), None)
                brand_responses.append(
                    PromptBrandMentionResponse(
                        brandId=brand.id,
                        brandName=brand.name,
                        position=mention.position if mention and mention.mentioned else 0,
                        mentioned=mention.mentioned if mention else False,
                        sentiment=mention.sentiment if mention and mention.sentiment else "neutral",
                    )
                )

            mentioned_brands = [b for b in brand_responses if b.mentioned]

            # Calculate visibility based on Wix's position (primary brand)
            wix_mention = next((b for b in brand_responses if b.brandId == "wix"), None)
            if wix_mention and wix_mention.mentioned and wix_mention.position > 0:
                visibility = max(0, 100 - (wix_mention.position - 1) * 20)
            else:
                visibility = 0

            # Use Wix's position (primary brand), not average of all brands
            wix_position = wix_mention.position if wix_mention and wix_mention.mentioned else 0

            all_visibilities.append(visibility)
            if wix_position > 0:
                all_positions.append(wix_position)
            all_mentions_count.append(len(mentioned_brands))

        # Aggregate mentioned brands across ALL runs (not just latest)
        all_mentioned_brand_ids = set()
        for prompt in prompts_list:
            mentions = session.exec(
                select(PromptBrandMention).where(
                    PromptBrandMention.prompt_id == prompt.id,
                    PromptBrandMention.mentioned == True
                )
            ).all()
            for m in mentions:
                all_mentioned_brand_ids.add(m.brand_id)

        # Build aggregated brand responses (brand is "mentioned" if mentioned in ANY run)
        aggregated_brand_responses = []
        for brand in brands:
            aggregated_brand_responses.append(
                PromptBrandMentionResponse(
                    brandId=brand.id,
                    brandName=brand.name,
                    position=0,  # Position varies by run, use 0 for aggregated view
                    mentioned=brand.id in all_mentioned_brand_ids,
                    sentiment="neutral",  # Aggregated sentiment
                )
            )

        # Calculate averages
        avg_visibility = sum(all_visibilities) / len(all_visibilities) if all_visibilities else 0
        avg_pos = sum(all_positions) / len(all_positions) if all_positions else 0
        avg_mentions = sum(all_mentions_count) / len(all_mentions_count) if all_mentions_count else 0

        result.append(
            PromptResponse(
                id=f"query-{idx}",
                query=query,
                visibility=round(avg_visibility, 1),
                avgPosition=round(avg_pos, 1),
                totalMentions=round(avg_mentions),
                totalRuns=len(prompts_list),
                brands=aggregated_brand_responses,
            )
        )

    return result


@app.get(
    "/api/prompts/{query_id}",
    tags=["prompts"],
    summary="Get prompt details",
    description="""
    Get detailed information for a specific prompt query with all runs.
    
    **Query ID Format:**
    - Use format: `query-1`, `query-2`, etc.
    - Number corresponds to order from list prompts endpoint
    - Example: First query = `query-1`, second = `query-2`
    
    Returns:
    - Query text
    - Aggregated metrics across all runs
    - Individual run details with sources and brand mentions
    - Full response text for each run
    """,
    response_model=PromptDetailResponse,
    responses={
        200: {
            "description": "Prompt details with all runs",
        },
        400: {
            "description": "Invalid query ID format",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid query ID format"}
                }
            }
        },
        404: {
            "description": "Query not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Query not found"}
                }
            }
        }
    }
)
def get_prompt_detail(query_id: str, session: Session = Depends(get_session)):
    """
    Get detailed prompt info with all runs.
    
    Extracts query index from query_id (e.g., "query-1" -> 1)
    and returns all runs for that query with full details.
    """
    # Extract index from query_id (e.g., "query-1" -> 1)
    try:
        idx = int(query_id.replace("query-", "").replace("prompt-", ""))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid query ID format")

    all_prompts = session.exec(select(Prompt).order_by(Prompt.query, Prompt.run_number)).all()
    brands = session.exec(select(Brand)).all()

    # Group prompts by query
    grouped = {}
    for prompt in all_prompts:
        if prompt.query not in grouped:
            grouped[prompt.query] = []
        grouped[prompt.query].append(prompt)

    # Get the query by index
    queries = list(grouped.keys())
    if idx < 1 or idx > len(queries):
        raise HTTPException(status_code=404, detail="Query not found")

    query = queries[idx - 1]
    prompts_list = grouped[query]

    # Build runs
    runs = []
    for prompt in sorted(prompts_list, key=lambda p: p.run_number if hasattr(p, 'run_number') else 1):
        runs.append(get_run_data(session, prompt, brands))

    # Use latest run for aggregate display
    latest_run = runs[-1] if runs else None

    # Calculate averages across all runs
    avg_visibility = sum(r.visibility for r in runs) / len(runs) if runs else 0
    avg_position = sum(r.avgPosition for r in runs if r.avgPosition > 0) / len([r for r in runs if r.avgPosition > 0]) if any(r.avgPosition > 0 for r in runs) else 0
    avg_mentions = sum(r.totalMentions for r in runs) / len(runs) if runs else 0

    return PromptDetailResponse(
        id=query_id,
        query=query,
        visibility=round(avg_visibility, 1),
        avgPosition=round(avg_position, 1),
        totalMentions=round(avg_mentions),
        totalRuns=len(runs),
        brands=latest_run.brands if latest_run else [],
        runs=runs,
    )


@app.get(
    "/api/sources",
    tags=["sources"],
    summary="List all sources",
    description="""
    Get all citation sources with usage metrics.
    
    Metrics include:
    - **Usage**: Percentage of unique queries citing this source
    - **Average Citations**: Average citation position across all prompts
    
    Results are sorted by usage percentage descending.
    """,
    response_model=list[SourceResponse],
    responses={
        200: {
            "description": "List of sources with usage metrics",
        }
    }
)
def get_sources(session: Session = Depends(get_session)):
    """
    Get all sources with usage metrics.
    
    Calculates usage based on unique queries (not individual runs)
    citing each source.
    """
    # Count unique queries (not runs)
    all_prompts = session.exec(select(Prompt)).all()
    unique_queries = set(p.query for p in all_prompts)
    total_queries = len(unique_queries)

    sources = session.exec(select(Source)).all()

    result = []
    for source in sources:
        prompt_links = session.exec(
            select(PromptSource).where(PromptSource.source_id == source.id)
        ).all()

        # Count unique queries citing this source
        citing_queries = set()
        for pl in prompt_links:
            prompt = session.get(Prompt, pl.prompt_id)
            if prompt:
                citing_queries.add(prompt.query)

        usage = (len(citing_queries) / total_queries * 100) if total_queries > 0 else 0
        avg_citations = (
            sum(pl.citation_order for pl in prompt_links) / len(prompt_links)
            if prompt_links
            else 0
        )

        result.append(
            SourceResponse(
                domain=source.domain,
                usage=round(usage, 1),
                avgCitations=round(avg_citations, 1),
            )
        )

    # Sort by usage descending
    result.sort(key=lambda x: x.usage, reverse=True)
    return result


@app.get(
    "/api/metrics",
    tags=["analytics"],
    summary="Get dashboard metrics",
    description="""
    Get dashboard KPIs with month-over-month changes.
    
    Metrics include:
    - **Visibility**: Primary brand visibility percentage (Jan 2026)
    - **Total Prompts**: Total unique queries tracked
    - **Total Sources**: Total source citations (Jan 2026)
    - **Average Position**: Average position when mentioned (Jan 2026)
    
    All metrics include change values comparing January vs December 2025.
    """,
    response_model=DashboardMetricsResponse,
    responses={
        200: {
            "description": "Dashboard metrics with changes",
        }
    }
)
def get_metrics(session: Session = Depends(get_session)):
    """
    Get dashboard KPIs with month-over-month changes.
    
    Calculates metrics for January 2026 and compares with December 2025
    to show trends and changes.
    """
    all_prompts = session.exec(select(Prompt)).all()
    unique_queries = set(p.query for p in all_prompts)
    total_queries = len(unique_queries)

    # Separate January and December prompts
    jan_prompts = [p for p in all_prompts if p.scraped_at and p.scraped_at.strftime("%Y-%m") == "2026-01"]
    dec_prompts = [p for p in all_prompts if p.scraped_at and p.scraped_at.strftime("%Y-%m") == "2025-12"]

    jan_queries = set(p.query for p in jan_prompts)
    dec_queries = set(p.query for p in dec_prompts)

    # Calculate sources: count total source citations across all runs
    # Sources this month (January 2026)
    jan_source_count = 0
    for prompt in jan_prompts:
        prompt_sources = session.exec(
            select(PromptSource).where(PromptSource.prompt_id == prompt.id)
        ).all()
        jan_source_count += len(prompt_sources)

    # Sources last month (December 2025) for change calculation
    dec_source_count = 0
    for prompt in dec_prompts:
        prompt_sources = session.exec(
            select(PromptSource).where(PromptSource.prompt_id == prompt.id)
        ).all()
        dec_source_count += len(prompt_sources)

    # Total sources across all months
    total_source_count = 0
    for prompt in all_prompts:
        prompt_sources = session.exec(
            select(PromptSource).where(PromptSource.prompt_id == prompt.id)
        ).all()
        total_source_count += len(prompt_sources)

    sources_change = jan_source_count - dec_source_count

    # Calculate Wix visibility for January
    jan_wix_queries = set()
    jan_wix_positions = []
    for prompt in jan_prompts:
        mention = session.exec(
            select(PromptBrandMention).where(
                PromptBrandMention.prompt_id == prompt.id,
                PromptBrandMention.brand_id == "wix",
                PromptBrandMention.mentioned == True,
            )
        ).first()
        if mention:
            jan_wix_queries.add(prompt.query)
            if mention.position:
                jan_wix_positions.append(mention.position)

    jan_visibility = (len(jan_wix_queries) / len(jan_queries) * 100) if jan_queries else 0
    jan_avg_position = sum(jan_wix_positions) / len(jan_wix_positions) if jan_wix_positions else 0

    # Calculate Wix visibility for December
    dec_wix_queries = set()
    dec_wix_positions = []
    for prompt in dec_prompts:
        mention = session.exec(
            select(PromptBrandMention).where(
                PromptBrandMention.prompt_id == prompt.id,
                PromptBrandMention.brand_id == "wix",
                PromptBrandMention.mentioned == True,
            )
        ).first()
        if mention:
            dec_wix_queries.add(prompt.query)
            if mention.position:
                dec_wix_positions.append(mention.position)

    dec_visibility = (len(dec_wix_queries) / len(dec_queries) * 100) if dec_queries else 0
    dec_avg_position = sum(dec_wix_positions) / len(dec_wix_positions) if dec_wix_positions else 0

    # Calculate changes (Jan vs Dec)
    visibility_change = jan_visibility - dec_visibility
    # Position: lower is better, so flip sign (Dec - Jan = positive when improved)
    position_change = dec_avg_position - jan_avg_position  # Positive means improvement

    return DashboardMetricsResponse(
        visibility=MetricResponse(value=round(jan_visibility, 1), change=round(visibility_change, 1)),
        totalPrompts=MetricResponse(value=total_queries, change=0),
        totalSources=MetricResponse(value=jan_source_count, change=sources_change, total=total_source_count),
        avgPosition=MetricResponse(value=round(jan_avg_position, 1), change=round(position_change, 2)),
    )


@app.get(
    "/api/visibility",
    tags=["analytics"],
    summary="Get visibility data",
    description="""
    Get monthly visibility data for charts.
    
    Returns visibility percentages for each brand by month:
    - September 2025
    - October 2025
    - November 2025
    - December 2025
    - January 2026
    
    Visibility is calculated as percentage of unique queries mentioning each brand.
    """,
    response_model=list[DailyVisibilityResponse],
    responses={
        200: {
            "description": "Monthly visibility data",
        }
    }
)
def get_visibility_data(session: Session = Depends(get_session)):
    """
    Get monthly visibility data for charts.
    
    Calculates brand visibility percentages for each month
    from September 2025 to January 2026.
    """
    brands = session.exec(select(Brand)).all()
    all_prompts = session.exec(select(Prompt)).all()

    # Group prompts by month
    months = {
        "Sep 2025": [],
        "Oct 2025": [],
        "Nov 2025": [],
        "Dec 2025": [],
        "Jan 2026": [],
    }

    for prompt in all_prompts:
        if prompt.scraped_at:
            month_str = prompt.scraped_at.strftime("%Y-%m")
            if month_str == "2025-09":
                months["Sep 2025"].append(prompt)
            elif month_str == "2025-10":
                months["Oct 2025"].append(prompt)
            elif month_str == "2025-11":
                months["Nov 2025"].append(prompt)
            elif month_str == "2025-12":
                months["Dec 2025"].append(prompt)
            elif month_str == "2026-01":
                months["Jan 2026"].append(prompt)

    result = []
    for month_name in ["Sep 2025", "Oct 2025", "Nov 2025", "Dec 2025", "Jan 2026"]:
        month_prompts = months[month_name]
        unique_queries = set(p.query for p in month_prompts)
        total_queries = len(unique_queries)

        brand_visibility = {}
        for brand in brands:
            # Get mentions for prompts in this month
            mentioned_queries = set()
            for prompt in month_prompts:
                mention = session.exec(
                    select(PromptBrandMention).where(
                        PromptBrandMention.prompt_id == prompt.id,
                        PromptBrandMention.brand_id == brand.id,
                        PromptBrandMention.mentioned == True,
                    )
                ).first()
                if mention:
                    mentioned_queries.add(prompt.query)

            brand_visibility[brand.id] = (
                (len(mentioned_queries) / total_queries * 100) if total_queries > 0 else 0
            )

        result.append(DailyVisibilityResponse(
            date=month_name,
            shopify=round(brand_visibility.get("shopify", 0), 1),
            woocommerce=round(brand_visibility.get("woocommerce", 0), 1),
            bigcommerce=round(brand_visibility.get("bigcommerce", 0), 1),
            wix=round(brand_visibility.get("wix", 0), 1),
            squarespace=round(brand_visibility.get("squarespace", 0), 1),
        ))

    return result


@app.get(
    "/api/sources/analytics",
    tags=["sources"],
    summary="Get source analytics",
    description="""
    Get comprehensive analytics for citation sources.
    
    Includes:
    - **Summary**: Total sources, domains, citations, averages
    - **Domain Breakdown**: Top 20 domains by citation count
    - **Source Types**: Breakdown by type (blog, news, community, review, brand, other)
    - **Top Sources**: Top 50 sources by citation count with example prompts
    
    Source types are automatically classified based on domain patterns.
    """,
    response_model=SourcesAnalyticsResponse,
    responses={
        200: {
            "description": "Detailed source analytics",
        }
    }
)
def get_sources_analytics(session: Session = Depends(get_session)):
    """
    Get detailed analytics for citation sources.
    
    Provides comprehensive breakdown including domain analysis,
    source type classification, and top sources.
    """
    sources = session.exec(select(Source)).all()
    all_prompts = session.exec(select(Prompt)).all()

    # Classify domains by type
    def classify_domain(domain: str) -> str:
        domain_lower = domain.lower()
        # Brand/official sites
        if any(brand in domain_lower for brand in ['shopify', 'wix', 'woocommerce', 'bigcommerce', 'squarespace', 'wordpress']):
            return 'brand'
        # Community/forums
        if any(community in domain_lower for community in ['reddit', 'quora', 'stackexchange', 'stackoverflow', 'discourse']):
            return 'community'
        # News/media
        if any(news in domain_lower for news in ['forbes', 'techcrunch', 'entrepreneur', 'inc.com', 'businessinsider', 'cnet', 'zdnet', 'pcmag', 'theverge']):
            return 'news'
        # Blogs (common blog patterns)
        if any(blog in domain_lower for blog in ['blog', 'medium.com', 'dev.to', 'hashnode', 'substack']):
            return 'blog'
        # Review sites
        if any(review in domain_lower for review in ['g2.com', 'capterra', 'trustpilot', 'trustradius', 'getapp']):
            return 'review'
        # Default: check for common blog patterns in URL structure
        return 'other'

    # Build domain citation counts
    domain_citations = Counter()
    source_citations = {}  # source_id -> list of prompt queries

    for source in sources:
        prompt_links = session.exec(
            select(PromptSource).where(PromptSource.source_id == source.id)
        ).all()

        # Count total citations (across all runs)
        domain_citations[source.domain] += len(prompt_links)

        # Get unique prompts citing this source
        prompt_queries = []
        for pl in prompt_links:
            prompt = session.get(Prompt, pl.prompt_id)
            if prompt and prompt.query not in prompt_queries:
                prompt_queries.append(prompt.query)
        source_citations[source.id] = prompt_queries

    total_citations = sum(domain_citations.values())
    total_sources = len(sources)
    total_domains = len(set(s.domain for s in sources))

    # Build domain breakdown (top 20)
    domain_breakdown = []
    for domain, citations in domain_citations.most_common(20):
        domain_breakdown.append(DomainBreakdown(
            domain=domain,
            citations=citations,
            percentage=round(citations / total_citations * 100, 1) if total_citations > 0 else 0,
            type=classify_domain(domain)
        ))

    # Build source types breakdown
    type_counts = Counter()
    for source in sources:
        source_type = classify_domain(source.domain)
        # Refine classification: if URL contains /blog/ it's likely a blog post
        if source.url and '/blog/' in source.url.lower():
            source_type = 'blog'
        type_counts[source_type] += 1

    source_types = []
    for stype, count in type_counts.most_common():
        source_types.append(SourceType(
            type=stype,
            count=count,
            percentage=round(count / total_sources * 100, 1) if total_sources > 0 else 0
        ))

    # Build top sources list (top 50 by citation count)
    sources_with_citations = []
    for source in sources:
        prompt_links = session.exec(
            select(PromptSource).where(PromptSource.source_id == source.id)
        ).all()
        sources_with_citations.append((source, len(prompt_links)))

    sources_with_citations.sort(key=lambda x: x[1], reverse=True)

    top_sources = []
    for source, citation_count in sources_with_citations[:50]:
        top_sources.append(TopSource(
            id=source.id,
            domain=source.domain,
            url=source.url,
            title=source.title,
            citations=citation_count,
            prompts=source_citations.get(source.id, [])[:5]  # Limit to 5 prompts
        ))

    return SourcesAnalyticsResponse(
        summary=SourcesSummary(
            totalSources=total_sources,
            totalDomains=total_domains,
            totalCitations=total_citations,
            avgCitationsPerSource=round(total_citations / total_sources, 1) if total_sources > 0 else 0
        ),
        domainBreakdown=domain_breakdown,
        sourceTypes=source_types,
        topSources=top_sources
    )


@app.get(
    "/api/suggestions",
    tags=["analytics"],
    summary="Get SEO suggestions",
    description="""
    Get AI-powered SEO improvement suggestions based on source data analysis.
    
    Analyzes citation sources to provide actionable recommendations:
    - Content strategy (blog posts, guides)
    - Community engagement (Reddit, forums)
    - PR and authority building (news sites)
    - Technical optimization (comparison pages)
    - Review collection (G2, Capterra)
    
    Includes overall AI SEO score and prioritized suggestions with examples.
    """,
    response_model=SuggestionsResponse,
    responses={
        200: {
            "description": "SEO improvement suggestions",
        }
    }
)
def get_suggestions(session: Session = Depends(get_session)):
    """
    Get AI SEO improvement suggestions based on source data analysis.
    
    Analyzes source types and citation patterns to generate
    actionable SEO recommendations with examples.
    """
    sources = session.exec(select(Source)).all()
    all_prompts = session.exec(select(Prompt)).all()

    # Calculate source type percentages
    total_sources = len(sources)

    def classify_domain(domain: str, url: str = "") -> str:
        domain_lower = domain.lower()
        url_lower = url.lower() if url else ""

        if '/blog/' in url_lower:
            return 'blog'
        if any(brand in domain_lower for brand in ['shopify', 'wix', 'woocommerce', 'bigcommerce', 'squarespace']):
            return 'brand'
        if any(community in domain_lower for community in ['reddit', 'quora']):
            return 'community'
        if any(news in domain_lower for news in ['forbes', 'techcrunch', 'entrepreneur', 'inc.com', 'businessinsider']):
            return 'news'
        if any(review in domain_lower for review in ['g2.com', 'capterra', 'trustpilot']):
            return 'review'
        return 'other'

    type_counts = Counter()
    for source in sources:
        type_counts[classify_domain(source.domain, source.url)] += 1

    blog_pct = round(type_counts.get('blog', 0) / total_sources * 100) if total_sources > 0 else 0
    community_pct = round(type_counts.get('community', 0) / total_sources * 100) if total_sources > 0 else 0
    news_pct = round(type_counts.get('news', 0) / total_sources * 100) if total_sources > 0 else 0
    review_pct = round(type_counts.get('review', 0) / total_sources * 100) if total_sources > 0 else 0

    # Get sample sources for examples
    blog_sources = [s for s in sources if classify_domain(s.domain, s.url) == 'blog'][:3]
    community_sources = [s for s in sources if classify_domain(s.domain, s.url) == 'community'][:3]
    news_sources = [s for s in sources if classify_domain(s.domain, s.url) == 'news'][:3]

    # Get comparison prompts
    comparison_prompts = [p.query for p in all_prompts if any(word in p.query.lower() for word in ['vs', 'versus', 'compare', 'best', 'top'])]
    unique_comparison = list(set(comparison_prompts))[:5]
    comparison_pct = round(len(set(comparison_prompts)) / len(set(p.query for p in all_prompts)) * 100) if all_prompts else 0

    # Calculate Wix visibility score for overall AI SEO score
    jan_prompts = [p for p in all_prompts if p.scraped_at and p.scraped_at.strftime("%Y-%m") == "2026-01"]
    jan_queries = set(p.query for p in jan_prompts)

    wix_mentioned = 0
    for query in jan_queries:
        query_prompts = [p for p in jan_prompts if p.query == query]
        for prompt in query_prompts:
            mention = session.exec(
                select(PromptBrandMention).where(
                    PromptBrandMention.prompt_id == prompt.id,
                    PromptBrandMention.brand_id == "wix",
                    PromptBrandMention.mentioned == True,
                )
            ).first()
            if mention:
                wix_mentioned += 1
                break

    visibility_score = round(wix_mentioned / len(jan_queries) * 100) if jan_queries else 0

    # Overall AI SEO score (weighted average)
    ai_seo_score = min(100, round(visibility_score * 0.9 + 10))  # Base 10 + visibility contribution

    suggestions = [
        Suggestion(
            id=1,
            priority="high",
            category="content",
            title="Create More Blog Content",
            description=f"{blog_pct}% of AI citation sources are blog posts. Publishing regular, in-depth blog content about ecommerce topics significantly increases your chances of being cited by AI systems. Focus on comprehensive guides and tutorials.",
            stat=f"{blog_pct}%",
            statLabel="of sources are blogs",
            action="Start a blog with ecommerce guides, tutorials, and industry insights",
            examples=[
                SuggestionExample(type="source", domain=s.domain, title=s.title) for s in blog_sources
            ] + [
                SuggestionExample(type="prompt", query=q) for q in unique_comparison[:2]
            ]
        ),
        Suggestion(
            id=2,
            priority="medium",
            category="community",
            title="Engage on Reddit & Forums",
            description=f"{community_pct}% of AI citations come from community discussions on Reddit and forums. Participating authentically in relevant subreddits like r/ecommerce, r/shopify, and r/smallbusiness can boost your visibility.",
            stat=f"{community_pct}%",
            statLabel="of sources are community sites",
            action="Join r/ecommerce, r/entrepreneur, and relevant subreddit communities",
            examples=[
                SuggestionExample(type="source", domain=s.domain, title=s.title) for s in community_sources
            ]
        ),
        Suggestion(
            id=3,
            priority="high",
            category="authority",
            title="Get Featured in Industry Publications",
            description=f"News and industry publications account for {news_pct}% of AI citations. PR efforts, guest posts, and getting featured on authority sites like Forbes, TechCrunch, and Entrepreneur improve AI visibility significantly.",
            stat=f"{news_pct}%",
            statLabel="are news/industry sites",
            action="Pitch stories to ecommerce and tech publications, pursue guest posting opportunities",
            examples=[
                SuggestionExample(type="source", domain=s.domain, title=s.title) for s in news_sources
            ]
        ),
        Suggestion(
            id=4,
            priority="medium",
            category="technical",
            title="Optimize for Comparison Queries",
            description=f"{comparison_pct}% of tracked prompts are comparison queries (e.g., 'best platform', 'X vs Y'). Creating dedicated comparison pages and landing pages optimized for these queries can improve visibility.",
            stat=f"{comparison_pct}%",
            statLabel="of queries compare platforms",
            action="Build comparison landing pages and feature comparison content",
            examples=[
                SuggestionExample(type="prompt", query=q) for q in unique_comparison[:3]
            ]
        ),
        Suggestion(
            id=5,
            priority="low",
            category="content",
            title="Collect Reviews on G2 & Capterra",
            description=f"Review platforms account for {review_pct}% of sources. Having strong presence on review sites like G2, Capterra, and Trustpilot provides social proof that AI systems reference.",
            stat=f"{review_pct}%",
            statLabel="are review platforms",
            action="Encourage customers to leave reviews on G2, Capterra, and Trustpilot",
            examples=[]
        ),
    ]

    return SuggestionsResponse(
        score=ai_seo_score,
        suggestions=suggestions
    )


@app.get(
    "/api/health",
    tags=["health"],
    summary="Health check",
    description="Check if the backend API service is running and healthy.",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2026-01-31T18:00:00.000000"
                    }
                }
            }
        }
    }
)
def health_check():
    """
    Health check endpoint.
    
    Returns the current health status and timestamp.
    Use this to verify the API is running before making requests.
    """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Background Scheduler
import asyncio
from typing import List

async def scheduler_loop():
    """Background loop to process scheduled jobs."""
    while True:
        try:
            with Session(engine) as session:
                # Find pending scheduled jobs that are due
                now = datetime.utcnow()
                # 1. Recur: Jobs that are periodic and due for next run
                # (For simplicity, we query jobs with frequency set and next_run_at <= now)
                due_jobs = session.exec(
                    select(ScrapeJob).where(
                        ScrapeJob.is_active == True,
                        ScrapeJob.frequency != None,
                        ScrapeJob.next_run_at <= now
                    )
                ).all()
                
                for job in due_jobs:
                    # Create a new run instance for this job
                    await trigger_scheduled_job(job, session)
                    
                    # Update next run time
                    update_next_run(job)
                    session.add(job)
                    session.commit()
                    
        except Exception as e:
            print(f"Scheduler error: {e}")
            
        await asyncio.sleep(60) # Check every minute

def update_next_run(job: ScrapeJob):
    """
    Calculate next run time based on frequency.
    
    Supported frequencies:
    - hourly: Every hour
    - 2_per_day: Every 12 hours
    - 1_per_day / daily: Every 24 hours
    - 2_per_week: Every 3.5 days
    - weekly: Every 7 days
    - monthly: Every 30 days
    """
    if not job.next_run_at:
        job.next_run_at = datetime.utcnow()
    
    freq = job.frequency.lower() if job.frequency else "daily"
    
    # Map frequency to timedelta
    frequency_map = {
        "hourly": timedelta(hours=1),
        "2_per_day": timedelta(hours=12),
        "1_per_day": timedelta(days=1),
        "daily": timedelta(days=1),
        "2_per_week": timedelta(days=3, hours=12),  # ~3.5 days
        "1_per_week": timedelta(weeks=1),
        "weekly": timedelta(weeks=1),
        "monthly": timedelta(days=30),
    }
    
    delta = frequency_map.get(freq, timedelta(days=1))
    job.next_run_at += delta
    
    print(f"[Scheduler] Job {job.id} next run: {job.next_run_at} (frequency: {freq})")

async def trigger_scheduled_job(parent_job: ScrapeJob, session: Session):
    """Create and trigger a new job instance from a parent scheduled job."""
    print(f"Triggering scheduled job: {parent_job.id} - {parent_job.query}")
    
    # Clone config
    config = json.loads(parent_job.config_snapshot) if parent_job.config_snapshot else {}
    
    # Create new instance
    new_job = ScrapeJob(
        query=parent_job.query,
        country=parent_job.country,
        scraper_type=parent_job.scraper_type,
        status="running",
        config_snapshot=parent_job.config_snapshot,
        parent_job_id=parent_job.id,
        schedule_type="recurring_instance"
    )
    session.add(new_job)
    session.commit()
    session.refresh(new_job)
    
    # Execute (Reuse existing logic or call internal function)
    # We'll use a background task to avoid blocking the scheduler loop
    # Ideally, we should refactor create_scrape_job logic to be reusable
    asyncio.create_task(run_scrape_logic(new_job.id, config))

def analyze_brand_mentions(session: Session, prompt: Prompt):
    """Analyze response text for brand mentions and create PromptBrandMention records."""
    text = (prompt.response_text or "").lower()
    brands = session.exec(select(Brand)).all()
    
    for brand in brands:
        is_mentioned = False
        
        # Check name
        if brand.name.lower() in text:
            is_mentioned = True
            
        # Check variations
        if not is_mentioned and brand.variations:
            # Handle variations if it's a comma-separated string or list (schema vs model diff)
            # Model says str | None (comma-separated), Schema says list[str]
            # We treat model as truth source here
            vars_list = []
            if isinstance(brand.variations, str):
                vars_list = [v.strip().lower() for v in brand.variations.split(",") if v.strip()]
            elif isinstance(brand.variations, list):
                vars_list = [v.strip().lower() for v in brand.variations if v.strip()]
                
            for v in vars_list:
                if v in text:
                    is_mentioned = True
                    break
        
        if is_mentioned:
            # Estimate position: find first occurrence index
            # This is a very rough estimation. Lower index = better visibility.
            # In a real SERP scraper, we'd have list item ranks.
            # Here we map text index to a 1-10 scale somewhat arbitrarily if not structured.
            
            # Simple heuristic: 
            # 0-500 chars -> pos 1
            # 500-1000 chars -> pos 2, etc.
            first_idx = text.find(brand.name.lower())
            if first_idx == -1 and brand.variations:
                 # Find min index of variations
                 indices = []
                 vars_list = []
                 if isinstance(brand.variations, str):
                    vars_list = [v.strip().lower() for v in brand.variations.split(",") if v.strip()]
                 for v in vars_list:
                     idx = text.find(v)
                     if idx != -1:
                         indices.append(idx)
                 if indices:
                     first_idx = min(indices)
            
            position = 1
            if first_idx > -1:
                # Rough position estimation
                position = min(10, (first_idx // 300) + 1)
            
            mention = PromptBrandMention(
                prompt_id=prompt.id,
                brand_id=brand.id,
                mentioned=True,
                position=position,
                sentiment="neutral" # Default
            )
            session.add(mention)
        else:
            # Create a record for "not mentioned" if needed for queries, 
            # or just skip. The frontend queries `mentioned=True`.
            # But get_run_data queries all mentions for this prompt.
            # We should probably create a record with mentioned=False so it exists?
            # get_run_data handles missing mentions (returns False/0).
            # So we only need to add positive mentions.
            pass
            
    session.commit()

async def run_scrape_logic(job_id: int, config: dict):
    """Internal logic to execute a scrape job (extracted from API endpoint)."""
    try:
        # Construct request payload with profile support
        profile = config.get("profile", "desktop_1080p")
        
        # Map device_type to profile if no explicit profile set
        if profile == "desktop_1080p" and config.get("device_type"):
            device_type = config.get("device_type", "desktop").lower()
            if device_type == "mobile":
                profile = "iphone_14"  # Default mobile profile
            elif device_type == "tablet":
                profile = "ipad_air"   # Default tablet profile
            # else keep desktop_1080p
        
        payload = {
            "query": config.get("query"),
            "country": config.get("country"),
            "num_results": config.get("num_results", 10),
            "scraper_type": config.get("scraper_type", "google_ai"),
            "job_id": job_id,  # Pass job_id for log correlation
            "proxy_layer": config.get("proxy_layer", "auto"),  # Pass proxy layer preference
            "anti_detect_config": {
                "enabled": config.get("antidetect_enabled", True),
                "target_country": config.get("country", "us").upper(),
                "device_type": config.get("device_type", "desktop"),
                "os": config.get("os_type", "windows"),
                "browser": config.get("browser_type", "chrome"),
                "human_typing": config.get("human_behavior", True),
                "human_mouse": config.get("human_behavior", True),
                "random_delays": config.get("human_behavior", True)
            },
            "take_screenshot": config.get("take_screenshot", True),  # Always take screenshots for debugging
            "headless": config.get("run_in_background", True),
            "use_residential_proxy": config.get("use_residential_proxy", False),
            "use_scraping_browser": config.get("use_scraping_browser", False),
            "human_behavior": config.get("human_behavior", True),
            # Scraping Browser specific settings
            "profile": profile,
            "custom_viewport": config.get("custom_viewport"),
            "scroll_full_page": config.get("scroll_full_page", True),
        }
        
        # Log job start
        print(f"[job:{job_id}] START query=\"{payload['query']}\" country={payload['country']} scraper={payload['scraper_type']} layer={payload['proxy_layer']} profile={payload['profile']}")
        
        # Call scraper service
        # Increased timeout for Bright Data SDK or browser wait
        start_time = datetime.utcnow()
        response = requests.post(
            f"{SCRAPER_API_URL}/scrape",
            json=payload,
            timeout=600 
        )
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        if response.status_code != 200:
            raise Exception(f"Scraper error: {response.text}")
            
        result = response.json()
        
        with Session(engine) as session:
            scrape_job = session.get(ScrapeJob, job_id)
            if scrape_job:
                # Always save HTML if available, regardless of status
                if result.get("html_content"):
                     scrape_job.html_snapshot = result.get("html_content")[:1000000]
                     scrape_job.response_size_kb = len(result.get("html_content", "")) / 1024
                
                # Update metadata
                scrape_job.proxy_used = result.get("metadata", {}).get("proxy_used")
                scrape_job.profile_data = json.dumps(result.get("metadata", {}))
                scrape_job.completed_at = end_time
                scrape_job.duration_seconds = duration
                
                # Extract proxy layer info from metadata
                proxy_layer = result.get("metadata", {}).get("proxy_layer", {})
                if proxy_layer:
                    scrape_job.layer2_mode = proxy_layer.get("layer2_mode")
                    origin = proxy_layer.get("origin", {})
                    if origin:
                        scrape_job.origin_ip = origin.get("ip")
                        scrape_job.origin_country = origin.get("country")
                        scrape_job.origin_verified = origin.get("verified", False)
                
                # Estimate cost based on layer2_mode
                cost_map = {"direct": 0, "residential": 0.004, "unlocker": 0.008, "browser": 0.025}
                scrape_job.estimated_cost_usd = cost_map.get(scrape_job.layer2_mode, 0)

                if result.get("status") == "failed":
                    scrape_job.status = "failed"
                    scrape_job.error = result.get("error", "Unknown scraper error")
                    session.add(scrape_job)
                    session.commit()
                    return None
                
                # Success path
                scrape_job.status = "completed"
                
                # Create Prompt
                prompt = Prompt(
                    query=scrape_job.query,
                    response_text=result.get("response_text"),
                    scraped_at=datetime.utcnow()
                )
                session.add(prompt)
                session.commit()
                session.refresh(prompt)
                
                scrape_job.prompt_id = prompt.id
                session.add(scrape_job)
                
                # Save Sources
                for src_data in result.get("data", []):
                    source = session.exec(select(Source).where(Source.url == src_data["url"])).first()
                    if not source:
                        source = Source(
                            domain=src_data.get("publisher", "unknown"),
                            url=src_data["url"],
                            title=src_data.get("title"),
                            description=src_data.get("description"),
                            published_date=src_data.get("date")
                        )
                        session.add(source)
                        session.commit()
                        session.refresh(source)
                    
                    link = PromptSource(
                        prompt_id=prompt.id,
                        source_id=source.id,
                        citation_order=result.get("data", []).index(src_data) + 1
                    )
                    session.add(link)
                
                # Analyze Brand Mentions
                analyze_brand_mentions(session, prompt)
                
                session.commit()
                
                return prompt.id
                
    except Exception as e:
        print(f"Scheduled job {job_id} failed: {e}")
        with Session(engine) as session:
            scrape_job = session.get(ScrapeJob, job_id)
            if scrape_job:
                scrape_job.status = "failed"
                scrape_job.error = str(e)[:500]  # Truncate long errors
                scrape_job.completed_at = datetime.utcnow()
                # Calculate duration if start_time was set
                if 'start_time' in dir():
                    scrape_job.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
                session.add(scrape_job)
                session.commit()
        return None

@app.on_event("startup")
async def on_startup_scheduler():
    """Start the scheduler loop."""
    asyncio.create_task(scheduler_loop())


# VPN & Scraper Integration

@app.get(
    "/api/vpn/servers",
    tags=["system"],
    summary="Get VPN servers",
    description="""
    Fetch available ProtonVPN servers from the official Gluetun repository.
    
    Returns:
    - VPN provider name
    - List of available countries
    - Total server count
    - Active proxy countries configured in this system
    
    Used to see which VPN locations are available for scraping.
    """,
    responses={
        200: {
            "description": "VPN server information",
            "content": {
                "application/json": {
                    "example": {
                        "provider": "protonvpn",
                        "countries": ["Afghanistan", "Albania", "..."],
                        "total_servers": 1600,
                        "active_proxies": ["fr", "de", "nl", "it", "es", "uk", "ch", "se"]
                    }
                }
            }
        },
        503: {
            "description": "Failed to fetch server list",
        }
    }
)
def get_vpn_servers():
    """
    Fetch available ProtonVPN servers from Gluetun upstream.
    
    Retrieves the latest server list from GitHub and returns
    available countries and active proxy configuration.
    """
    try:
        # Try to get active proxies from scraper service first
        active_proxies = []
        try:
            resp = requests.get(f"{SCRAPER_API_URL}/config", timeout=2)
            if resp.status_code == 200:
                active_proxies = resp.json().get("proxies", [])
        except:
            active_proxies = ["fr", "de", "nl", "it", "es", "uk", "ch", "se"] # Fallback

        url = "https://raw.githubusercontent.com/qdm12/gluetun/master/internal/storage/servers.json"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            raise HTTPException(status_code=503, detail="Failed to fetch upstream server list")
        
        data = resp.json()
        proton_servers = data.get("protonvpn", {}).get("servers", [])
        
        # Format for frontend
        countries = sorted(list(set(s.get("country") for s in proton_servers if s.get("country"))))
        
        return {
            "provider": "protonvpn",
            "countries": countries,
            "total_servers": len(proton_servers),
            # Return configured servers from our setup
            "active_proxies": active_proxies
        }
    except Exception as e:
        # Fallback to hardcoded list if scraper service is unavailable
        return {
            "provider": "protonvpn",
            "active_proxies": ["fr", "de", "nl", "it", "es", "uk", "ch", "se"],
            "error": str(e)
        }

@app.get(
    "/api/config",
    tags=["system"],
    summary="Get system configuration",
    description="""
    Get system configuration including available scrapers and proxies.
    
    Returns:
    - Available scraper types
    - Configured proxy countries
    - Default scraper selection
    
    This endpoint proxies the scraper service config endpoint.
    """,
    responses={
        200: {
            "description": "System configuration",
            "content": {
                "application/json": {
                    "example": {
                        "scrapers": ["google_ai", "perplexity"],
                        "proxies": ["fr", "de", "nl", "it", "es", "uk", "ch", "se"],
                        "default_scraper": "google_ai"
                    }
                }
            }
        }
    }
)
def get_system_config():
    """
    Get system configuration including available scrapers and proxies.
    
    Fetches configuration from the scraper service or returns
    fallback configuration if service is unavailable.
    """
    try:
        response = requests.get(f"{SCRAPER_API_URL}/config", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
        
    return {
        "scrapers": ["google_ai", "perplexity", "brightdata", "chatgpt"],
        "proxies": ["ch", "de", "es", "fr", "it", "nl", "se", "uk"],
        "default_scraper": "google_ai"
    }

class JobRequest(BaseModel):
    """Request model for creating scraping jobs"""
    query: str = Field(..., description="Search query to scrape", example="best seo tools")
    country: str = Field(default="us", description="Country code for geolocation", example="us")
    num_results: int = Field(default=10, description="Number of results to return", example=10)
    scraper_type: str = Field(default="google_ai", description="Type of scraper: google_ai, perplexity, brightdata", example="google_ai")
    device_type: str = Field(default="desktop", description="Device type: desktop, mobile, tablet", example="desktop")
    os_type: str = Field(default="windows", description="OS type: windows, mac, linux, android, ios", example="windows")
    browser_type: str = Field(default="chrome", description="Browser type: chrome, firefox, safari", example="chrome")
    human_behavior: bool = Field(default=True, description="Enable human-like behavior (typing, mouse movements)", example=True)
    
    # Scheduling - supported frequencies
    frequency: str | None = Field(
        default=None, 
        description="""Schedule frequency. Options:
        - None: One-time job (no repeat)
        - 'hourly': Every hour
        - '2_per_day': Every 12 hours
        - '1_per_day' or 'daily': Every 24 hours
        - '2_per_week': Every 3.5 days
        - '1_per_week' or 'weekly': Every 7 days
        - 'monthly': Every 30 days
        """,
        example="1_per_day"
    )
    start_date: datetime | None = Field(default=None, description="Start date for scheduled jobs (ISO format). Defaults to now if not provided", example=None)
    
    # Proxy Layer Selection
    proxy_layer: str = Field(
        default="auto",
        description="""Proxy layer to use. Options:
        - 'auto': Automatically select best layer (unlocker for google_ai, browser for chatgpt)
        - 'direct': VPN only - cheapest but may hit CAPTCHA (~70% success)
        - 'residential': VPN + residential proxy (~85% success, $0.004/req)
        - 'unlocker': Web Unlocker API (~95% success, $0.008/req)
        - 'browser': Cloud Browser with JS execution (~98% success, $0.025/req)
        """,
        example="unlocker"
    )
    
    # Debugging
    take_screenshot: bool = Field(default=True, description="Capture screenshot during scraping (always on for debugging)", example=True)
    run_in_background: bool = Field(default=True, description="Run browser in headless mode. Set false to see browser", example=True)
    use_residential_proxy: bool = Field(default=False, description="[DEPRECATED] Use proxy_layer='residential' instead", example=False)
    use_scraping_browser: bool = Field(default=False, description="[DEPRECATED] Use proxy_layer='browser' instead", example=False)
    antidetect_enabled: bool = Field(default=True, description="Enable anti-detection browser fingerprinting", example=True)
    
    # Viewport/Profile settings for Scraping Browser
    profile: str = Field(
        default="desktop_1080p", 
        description="""Device viewport profile for Scraping Browser. Options:
        - Types: 'phone', 'tablet', 'desktop' (uses default for that type)
        - Phones: 'iphone_14', 'iphone_15_pro', 'pixel_7', 'samsung_s23'
        - Tablets: 'ipad_pro_12', 'ipad_air', 'galaxy_tab_s8'  
        - Desktops: 'desktop_1080p', 'desktop_1440p', 'macbook_pro_14', 'macbook_air_13', 'linux_desktop'
        """,
        example="desktop_1080p"
    )
    custom_viewport: dict | None = Field(
        default=None,
        description="Custom viewport dimensions (overrides profile). Format: {'width': int, 'height': int}",
        example=None
    )
    scroll_full_page: bool = Field(
        default=True, 
        description="Scroll page to load all dynamic content for full text extraction",
        example=True
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "best seo tools",
                "country": "us",
                "num_results": 10,
                "scraper_type": "google_ai",
                "device_type": "desktop",
                "os_type": "windows",
                "browser_type": "chrome",
                "human_behavior": True,
                "take_screenshot": False,
                "run_in_background": True,
                "use_residential_proxy": False,
                "use_scraping_browser": True,
                "antidetect_enabled": True,
                "profile": "desktop_1080p",
                "scroll_full_page": True
            }
        }

@app.post(
    "/api/jobs/scrape",
    tags=["jobs"],
    summary="Create scraping job",
    description="""
    Create a new scraping job that executes immediately or on a schedule.
    
    ## Job Types
    
    ### One-time Job
    - Set `frequency` to `null` or omit it
    - Executes immediately
    - Returns job_id and prompt_id when complete
    
    ### Scheduled Job
    - Set `frequency` to `daily`, `weekly`, or `hourly`
    - Optionally set `start_date` (defaults to now)
    - Returns job_id and next_run_at
    - Scheduler automatically creates new runs
    
    ## Scraper Types
    - **google_ai**: Google AI Overview (default)
    - **perplexity**: Perplexity AI
    - **brightdata**: BrightData residential proxy
    
    ## Proxy Options
    - **Datacenter VPN**: Standard VPN proxy (use_residential_proxy=false)
    - **Residential Proxy**: Residential IP proxy (use_residential_proxy=true, requires sidecar)
    
    ## Anti-Detection
    Configure browser fingerprinting via device_type, os_type, browser_type,
    and human_behavior settings.
    """,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Job created successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "one_time": {
                            "summary": "One-time job",
                            "value": {
                                "job_id": 123,
                                "status": "completed",
                                "prompt_id": 456
                            }
                        },
                        "scheduled": {
                            "summary": "Scheduled job",
                            "value": {
                                "job_id": 124,
                                "status": "scheduled",
                                "next_run_at": "2026-02-01T09:00:00"
                            }
                        }
                    }
                }
            }
        },
        500: {
            "description": "Scraping failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Scrape failed: Error message"
                    }
                }
            }
        }
    }
)
async def create_scrape_job(job: JobRequest, background_tasks: BackgroundTasks):
    """
    Trigger a scraping job via the internal scraper service.
    
    Creates a job record and either executes immediately (one-time)
    or schedules for future execution (recurring).
    
    For one-time jobs, waits for completion and returns prompt_id.
    For scheduled jobs, returns immediately with next_run_at timestamp.
    """
    
    # Snapshot config
    config_snapshot = job.model_dump_json()

    # Determine status and schedule
    status = "running"
    next_run_at = None
    
    if job.frequency:
        status = "scheduled"
        next_run_at = job.start_date if job.start_date else datetime.utcnow()
        # If start date is in future, wait. If now/past, scheduler picks it up.

    # Create Job Record
    scrape_job = ScrapeJob(
        query=job.query,
        country=job.country,
        scraper_type=job.scraper_type,
        status=status,
        config_snapshot=config_snapshot,
        frequency=job.frequency,
        next_run_at=next_run_at,
        schedule_type="recurring" if job.frequency else "once"
    )
    
    with Session(engine) as session:
        session.add(scrape_job)
        session.commit()
        session.refresh(scrape_job)
        job_id = scrape_job.id

    # If scheduled/recurring, return early (scheduler handles it)
    if job.frequency:
        return {"job_id": job_id, "status": "scheduled", "next_run_at": next_run_at}

    # Execute immediately in background task to avoid timeout
    background_tasks.add_task(run_scrape_logic_background, job_id, job.model_dump())
    
    return {"job_id": job_id, "status": "pending", "message": "Job started in background"}

async def run_scrape_logic_background(job_id: int, config: dict):
    """Wrapper for background execution."""
    await run_scrape_logic(job_id, config)

@app.get(
    "/api/jobs/{job_id}",
    tags=["jobs"],
    summary="Get job details",
    description="Get detailed information about a specific scrape job including HTML snapshot.",
)
def get_job(job_id: int):
    """Get details for a specific scrape job."""
    with Session(engine) as session:
        job = session.get(ScrapeJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {
            "id": job.id,
            "query": job.query,
            "country": job.country,
            "scraper_type": job.scraper_type,
            "status": job.status,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
            "error": job.error,
            "proxy_used": job.proxy_used,
            "profile_data": json.loads(job.profile_data) if job.profile_data else None,
            "config_snapshot": json.loads(job.config_snapshot) if job.config_snapshot else None,
            "html_snapshot_size": len(job.html_snapshot) if job.html_snapshot else 0,
            "prompt_id": job.prompt_id,
            "schedule_type": job.schedule_type,
            "frequency": job.frequency,
            "next_run_at": job.next_run_at,
            "is_active": job.is_active,
        }


@app.get(
    "/api/jobs/{job_id}/html",
    tags=["jobs"],
    summary="Get job HTML snapshot",
    description="Get the raw HTML snapshot captured during scraping. Returns HTML content directly.",
)
def get_job_html(job_id: int):
    """Get HTML snapshot for a scrape job."""
    from fastapi.responses import HTMLResponse
    with Session(engine) as session:
        job = session.get(ScrapeJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if not job.html_snapshot:
            raise HTTPException(status_code=404, detail="No HTML snapshot available for this job")
        return HTMLResponse(content=job.html_snapshot, media_type="text/html")


@app.get(
    "/api/jobs",
    tags=["jobs"],
    summary="List scraping jobs",
    description="""
    List all scraping jobs with optional status filter.
    
    **Status Values:**
    - `pending`: Job is queued but not started
    - `running`: Job is currently executing
    - `completed`: Job finished successfully
    - `failed`: Job encountered an error
    - `scheduled`: Recurring job waiting for next run
    
    **Query Parameters:**
    - `status`: Filter jobs by status (optional)
    
    Returns list of jobs with:
    - Job ID, query, status, country
    - Scraper type, frequency (if scheduled)
    - Creation time, next run time (if scheduled)
    """,
    response_model=List[dict],
    responses={
        200: {
            "description": "List of jobs",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 123,
                            "query": "best seo tools",
                            "status": "completed",
                            "country": "us",
                            "scraper_type": "google_ai",
                            "frequency": None,
                            "next_run_at": None,
                            "created_at": "2026-01-31T18:00:00"
                        }
                    ]
                }
            }
        }
    }
)
def list_jobs(status: str | None = None, limit: int = 200):
    """
    List all scrape jobs.
    
    Optionally filter by status. Results are ordered by creation time descending.
    """
    with Session(engine) as session:
        query = select(ScrapeJob).order_by(ScrapeJob.created_at.desc()).limit(limit)
        if status:
            query = query.where(ScrapeJob.status == status)
        
        jobs = session.exec(query).all()
        return [
            {
                "id": job.id,
                "query": job.query,
                "status": job.status,
                "country": job.country,
                "frequency": job.frequency,
                "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "scraper_type": job.scraper_type,
                "is_active": job.is_active,
                "error": job.error,
                "duration_seconds": job.duration_seconds,
                "estimated_cost_usd": job.estimated_cost_usd,
                "layer2_mode": job.layer2_mode,
                "origin_verified": job.origin_verified,
                "screenshot_path": job.screenshot_path,
            }
            for job in jobs
        ]


@app.get(
    "/api/scheduled-jobs",
    tags=["jobs"],
    summary="List scheduled/recurring jobs",
    description="""
    List all active scheduled jobs that will run periodically.
    
    **Supported Frequencies:**
    - `hourly`: Every hour
    - `2_per_day`: Every 12 hours
    - `1_per_day` / `daily`: Every 24 hours
    - `2_per_week`: Every 3.5 days
    - `weekly`: Every 7 days
    - `monthly`: Every 30 days
    """,
)
def list_scheduled_jobs():
    """List all active scheduled jobs."""
    with Session(engine) as session:
        jobs = session.exec(
            select(ScrapeJob).where(
                ScrapeJob.is_active == True,
                ScrapeJob.frequency != None
            ).order_by(ScrapeJob.next_run_at)
        ).all()
        
        now = datetime.utcnow()
        
        return {
            "scheduled_jobs": [
                {
                    "id": job.id,
                    "query": job.query,
                    "country": job.country,
                    "scraper_type": job.scraper_type,
                    "frequency": job.frequency,
                    "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
                    "time_until_next_run": str(job.next_run_at - now) if job.next_run_at and job.next_run_at > now else "Due now",
                    "is_active": job.is_active,
                }
                for job in jobs
            ],
            "total_scheduled": len(jobs),
            "current_time": now.isoformat(),
            "supported_frequencies": [
                "hourly", "2_per_day", "1_per_day", "daily", 
                "2_per_week", "1_per_week", "weekly", "monthly"
            ],
        }


@app.get(
    "/api/scheduler-status",
    tags=["system"],
    summary="Get scheduler status",
    description="Check if the background scheduler is running and view upcoming jobs.",
)
def get_scheduler_status():
    """Get scheduler status and upcoming jobs."""
    with Session(engine) as session:
        now = datetime.utcnow()
        
        # Get jobs due in the next hour
        upcoming = session.exec(
            select(ScrapeJob).where(
                ScrapeJob.is_active == True,
                ScrapeJob.frequency != None,
                ScrapeJob.next_run_at <= now + timedelta(hours=1)
            ).order_by(ScrapeJob.next_run_at)
        ).all()
        
        # Get total active scheduled jobs
        total_active = session.exec(
            select(func.count(ScrapeJob.id)).where(
                ScrapeJob.is_active == True,
                ScrapeJob.frequency != None
            )
        ).one()
        
        # Get jobs that ran in the last hour
        recent = session.exec(
            select(ScrapeJob).where(
                ScrapeJob.completed_at >= now - timedelta(hours=1),
                ScrapeJob.parent_job_id != None  # Only scheduled runs
            ).order_by(ScrapeJob.completed_at.desc())
        ).all()
        
        return {
            "status": "running",
            "current_time": now.isoformat(),
            "total_scheduled_jobs": total_active,
            "jobs_due_next_hour": [
                {
                    "id": job.id,
                    "query": job.query[:50],
                    "frequency": job.frequency,
                    "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
                }
                for job in upcoming
            ],
            "recent_runs_last_hour": [
                {
                    "id": job.id,
                    "query": job.query[:50],
                    "status": job.status,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                }
                for job in recent[:10]
            ],
            "scheduler_info": {
                "check_interval": "60 seconds",
                "supported_frequencies": [
                    {"name": "hourly", "interval": "1 hour"},
                    {"name": "2_per_day", "interval": "12 hours"},
                    {"name": "1_per_day", "interval": "24 hours"},
                    {"name": "daily", "interval": "24 hours"},
                    {"name": "2_per_week", "interval": "3.5 days"},
                    {"name": "weekly", "interval": "7 days"},
                    {"name": "monthly", "interval": "30 days"},
                ],
            },
        }


@app.put(
    "/api/scheduled-jobs/{job_id}/pause",
    tags=["jobs"],
    summary="Pause a scheduled job",
    description="Pause a recurring job. It will not run until resumed.",
)
def pause_scheduled_job(job_id: int):
    """Pause a scheduled job."""
    with Session(engine) as session:
        job = session.get(ScrapeJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        if not job.frequency:
            raise HTTPException(status_code=400, detail="This is not a recurring job")
        
        job.is_active = False
        session.add(job)
        session.commit()
        
        return {
            "id": job_id,
            "query": job.query[:50],
            "status": "paused",
            "message": "Job paused successfully. It will not run until resumed.",
        }


@app.put(
    "/api/scheduled-jobs/{job_id}/resume",
    tags=["jobs"],
    summary="Resume a paused job",
    description="Resume a paused recurring job.",
)
def resume_scheduled_job(job_id: int):
    """Resume a paused scheduled job."""
    with Session(engine) as session:
        job = session.get(ScrapeJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        if not job.frequency:
            raise HTTPException(status_code=400, detail="This is not a recurring job")
        
        job.is_active = True
        # If next_run_at is in the past, update to now
        if job.next_run_at and job.next_run_at < datetime.utcnow():
            job.next_run_at = datetime.utcnow()
        
        session.add(job)
        session.commit()
        
        return {
            "id": job_id,
            "query": job.query[:50],
            "status": "active",
            "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
            "message": "Job resumed successfully.",
        }


@app.delete(
    "/api/scheduled-jobs/{job_id}",
    tags=["jobs"],
    summary="Delete a scheduled job",
    description="Delete a recurring job. This will stop all future runs.",
)
def delete_scheduled_job(job_id: int):
    """Delete a scheduled job."""
    with Session(engine) as session:
        job = session.get(ScrapeJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        query_preview = job.query[:50]
        session.delete(job)
        session.commit()
        
        return {
            "id": job_id,
            "query": query_preview,
            "message": "Scheduled job deleted successfully.",
        }


@app.get(
    "/api/scheduled-jobs/{job_id}",
    tags=["jobs"],
    summary="Get scheduled job details",
    description="Get details of a specific scheduled job.",
)
def get_scheduled_job(job_id: int):
    """Get scheduled job details."""
    with Session(engine) as session:
        job = session.get(ScrapeJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Get child jobs (executions)
        child_jobs = session.exec(
            select(ScrapeJob).where(ScrapeJob.parent_job_id == job_id).order_by(ScrapeJob.created_at.desc()).limit(10)
        ).all()
        
        return {
            "id": job.id,
            "query": job.query,
            "country": job.country,
            "scraper_type": job.scraper_type,
            "status": job.status,
            "is_active": job.is_active,
            "frequency": job.frequency,
            "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
            "created_at": job.created_at.isoformat(),
            "layer2_mode": job.layer2_mode,
            "recent_executions": [
                {
                    "id": c.id,
                    "status": c.status,
                    "created_at": c.created_at.isoformat(),
                    "completed_at": c.completed_at.isoformat() if c.completed_at else None,
                    "duration_seconds": c.duration_seconds,
                    "origin_ip": c.origin_ip,
                    "origin_verified": c.origin_verified,
                }
                for c in child_jobs
            ],
        }


# =============================================================================
# DAILY STATISTICS & MONITORING
# =============================================================================

def get_or_create_daily_stats(session: Session, date_str: str = None) -> DailyStats:
    """Get or create daily stats for a given date."""
    if not date_str:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
    
    stats = session.exec(
        select(DailyStats).where(DailyStats.date == date_str)
    ).first()
    
    if not stats:
        stats = DailyStats(date=date_str)
        session.add(stats)
        session.commit()
        session.refresh(stats)
    
    return stats


def update_daily_stats_from_job(session: Session, job: ScrapeJob):
    """Update daily stats when a job completes."""
    date_str = job.completed_at.strftime("%Y-%m-%d") if job.completed_at else datetime.utcnow().strftime("%Y-%m-%d")
    stats = get_or_create_daily_stats(session, date_str)
    
    if job.status == "completed":
        stats.prompts_completed += 1
        
        # Update by scraper type
        if job.scraper_type == "google_ai":
            stats.jobs_google_ai += 1
        elif job.scraper_type == "chatgpt":
            stats.jobs_chatgpt += 1
        elif job.scraper_type == "perplexity":
            stats.jobs_perplexity += 1
        
        # Update cost by layer
        if job.layer2_mode:
            cost = job.estimated_cost_usd or 0
            if job.layer2_mode == "direct":
                stats.cost_vpn_direct += cost
            elif job.layer2_mode == "residential":
                stats.cost_residential += cost
            elif job.layer2_mode == "unlocker":
                stats.cost_unlocker += cost
            elif job.layer2_mode == "browser":
                stats.cost_browser += cost
            stats.total_cost_usd += cost
        
        # Update performance
        if job.duration_seconds:
            # Running average
            total_jobs = stats.prompts_completed
            stats.avg_duration_seconds = (
                (stats.avg_duration_seconds * (total_jobs - 1) + job.duration_seconds) / total_jobs
            )
        
        if job.response_size_kb:
            stats.total_data_kb += job.response_size_kb
            
    elif job.status == "failed":
        stats.prompts_failed += 1
    
    stats.quota_remaining = max(0, stats.daily_quota - stats.prompts_completed - stats.prompts_scheduled)
    stats.updated_at = datetime.utcnow()
    
    session.add(stats)
    session.commit()


@app.get(
    "/api/daily-stats",
    tags=["analytics"],
    summary="Get daily statistics",
    description="""
    Get statistics for today or a specific date.
    
    Includes:
    - Prompt counts (scheduled, completed, failed)
    - Jobs by scraper type
    - Cost breakdown by proxy layer
    - Performance metrics
    - Quota status
    """,
)
def get_daily_stats(date: str = None):
    """Get daily statistics for monitoring."""
    with Session(engine) as session:
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        
        stats = get_or_create_daily_stats(session, date)
        
        # Also get real-time counts from jobs
        today_start = datetime.strptime(date, "%Y-%m-%d")
        today_end = today_start + timedelta(days=1)
        
        # Count actual jobs for today
        jobs_today = session.exec(
            select(ScrapeJob).where(
                ScrapeJob.created_at >= today_start,
                ScrapeJob.created_at < today_end
            )
        ).all()
        
        completed = sum(1 for j in jobs_today if j.status == "completed")
        failed = sum(1 for j in jobs_today if j.status == "failed")
        running = sum(1 for j in jobs_today if j.status == "running")
        pending = sum(1 for j in jobs_today if j.status in ("pending", "scheduled"))
        
        # Get active sessions (running jobs)
        active_sessions = session.exec(
            select(ScrapeJob).where(ScrapeJob.status == "running")
        ).all()
        
        return {
            "date": date,
            "summary": {
                "total_jobs": len(jobs_today),
                "completed": completed,
                "failed": failed,
                "running": running,
                "pending": pending,
                "success_rate": round(completed / len(jobs_today) * 100, 1) if jobs_today else 0,
            },
            "quota": {
                "daily_limit": stats.daily_quota,
                "used": completed + running + pending,
                "remaining": max(0, stats.daily_quota - completed - running - pending),
                "percentage_used": round((completed + running + pending) / stats.daily_quota * 100, 1),
            },
            "by_scraper": {
                "google_ai": sum(1 for j in jobs_today if j.scraper_type == "google_ai"),
                "chatgpt": sum(1 for j in jobs_today if j.scraper_type == "chatgpt"),
                "perplexity": sum(1 for j in jobs_today if j.scraper_type == "perplexity"),
            },
            "by_country": {
                country: sum(1 for j in jobs_today if j.country == country)
                for country in set(j.country for j in jobs_today)
            },
            "costs": {
                "vpn_direct": stats.cost_vpn_direct,
                "residential": stats.cost_residential,
                "unlocker": stats.cost_unlocker,
                "browser": stats.cost_browser,
                "total_usd": stats.total_cost_usd,
            },
            "performance": {
                "avg_duration_seconds": round(stats.avg_duration_seconds, 2),
                "total_data_kb": round(stats.total_data_kb, 2),
            },
            "active_sessions": [
                {
                    "id": j.id,
                    "query": j.query[:50],
                    "country": j.country,
                    "scraper_type": j.scraper_type,
                    "started_at": j.created_at.isoformat(),
                    "running_for_seconds": (datetime.utcnow() - j.created_at).total_seconds(),
                }
                for j in active_sessions
            ],
        }


@app.get(
    "/api/active-sessions",
    tags=["analytics"],
    summary="Get active scraping sessions",
    description="Get all currently running scraping sessions with real-time status.",
)
def get_active_sessions():
    """Get all active scraping sessions."""
    with Session(engine) as session:
        active = session.exec(
            select(ScrapeJob).where(ScrapeJob.status == "running")
        ).all()
        
        return {
            "count": len(active),
            "sessions": [
                {
                    "id": j.id,
                    "query": j.query,
                    "country": j.country,
                    "scraper_type": j.scraper_type,
                    "layer2_mode": j.layer2_mode,
                    "started_at": j.created_at.isoformat(),
                    "running_for_seconds": round((datetime.utcnow() - j.created_at).total_seconds(), 1),
                    "parent_job_id": j.parent_job_id,
                }
                for j in active
            ],
        }


@app.get(
    "/api/job-history",
    tags=["analytics"],
    summary="Get job execution history",
    description="Get recent job history with timing and performance data.",
)
def get_job_history(
    limit: int = 50,
    status: str = None,
    scraper_type: str = None,
    country: str = None,
):
    """Get job execution history with filters."""
    with Session(engine) as session:
        query = select(ScrapeJob).order_by(ScrapeJob.created_at.desc())
        
        if status:
            query = query.where(ScrapeJob.status == status)
        if scraper_type:
            query = query.where(ScrapeJob.scraper_type == scraper_type)
        if country:
            query = query.where(ScrapeJob.country == country)
        
        query = query.limit(limit)
        jobs = session.exec(query).all()
        
        return {
            "count": len(jobs),
            "jobs": [
                {
                    "id": j.id,
                    "query": j.query[:80],
                    "country": j.country,
                    "scraper_type": j.scraper_type,
                    "status": j.status,
                    "layer2_mode": j.layer2_mode,
                    "created_at": j.created_at.isoformat(),
                    "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                    "duration_seconds": j.duration_seconds,
                    "response_size_kb": j.response_size_kb,
                    "estimated_cost_usd": j.estimated_cost_usd,
                    "origin_ip": j.origin_ip,
                    "origin_country": j.origin_country,
                    "origin_verified": j.origin_verified,
                    "error": j.error[:100] if j.error else None,
                }
                for j in jobs
            ],
        }


# =============================================================================
# PROMPT TEMPLATES & BATCH SCHEDULING
# =============================================================================

# Supported countries with VPN containers
SUPPORTED_VPN_COUNTRIES = ["it", "ch", "uk", "de", "fr", "es", "nl", "us"]

class PromptTemplateCreate(BaseModel):
    """Request model for creating prompt templates.
    
    Each query will be executed in EACH specified country using that country's
    VPN container (Layer 1). The origin IP will be verified and tracked.
    
    Example: If countries="it,ch,uk", the query will run 3 times - once through
    each country's VPN, giving you geo-specific results.
    """
    name: str = Field(
        ..., 
        description="Template name for identification",
        example="SEO Tools Query"
    )
    query: str = Field(
        ..., 
        description="The search query to execute",
        example="best seo tools 2026"
    )
    category: str = Field(
        default="general", 
        description="Category for organizing templates",
        example="seo"
    )
    countries: str = Field(
        default="it,ch,uk", 
        description=f"""Comma-separated country codes. Each query runs in EACH country's VPN.
        
Supported countries: {', '.join(SUPPORTED_VPN_COUNTRIES)}

Example: "it,ch,uk" = 3 separate jobs, one per country VPN.
The job will route: Client → VPN-{'{country}'} → Layer2 → Target""",
        example="it,ch,uk"
    )
    scraper_type: str = Field(
        default="google_ai", 
        description="""Scraper type to use.
        
Options:
- google_ai: Google AI Mode (recommended: unlocker layer)
- chatgpt: ChatGPT (recommended: browser layer)
- perplexity: Perplexity AI (recommended: browser layer)""",
        example="google_ai"
    )
    frequency: str = Field(
        default="1_per_day", 
        description="""How often to run this query.
        
Options:
- hourly: Every 1 hour (24 runs/day)
- 2_per_day: Every 12 hours (2 runs/day)
- 1_per_day: Every 24 hours (1 run/day)
- daily: Same as 1_per_day
- 2_per_week: Every 3.5 days
- weekly: Every 7 days
- monthly: Every 30 days""",
        example="1_per_day"
    )
    priority: int = Field(
        default=1, 
        description="Priority level: 1=high (run first), 2=medium, 3=low",
        ge=1, le=3
    )
    preferred_layer2: str = Field(
        default="auto", 
        description="""Layer 2 proxy mode (on top of VPN).
        
Options:
- auto: Automatically select based on scraper_type
- direct: VPN only (free, ~70% success)
- residential: VPN + Bright Data residential IP (~$0.004/req, ~85% success)
- unlocker: VPN + Web Unlocker with CAPTCHA solving (~$0.008/req, ~95% success)
- browser: VPN + Cloud browser automation (~$0.025/req, ~98% success)

Recommendations:
- google_ai → unlocker
- chatgpt → browser
- perplexity → browser""",
        example="unlocker"
    )


@app.post(
    "/api/templates",
    tags=["scheduling"],
    summary="Create prompt template",
    description="""Create a reusable prompt template for scheduled scraping.

## How Country Routing Works

Each query is executed separately in EACH specified country:

```
Template: "best seo tools" with countries="it,ch,uk"

Creates 3 jobs:
1. Job IT: Client → VPN-IT (Italy IP) → Layer2 → Google
2. Job CH: Client → VPN-CH (Swiss IP) → Layer2 → Google  
3. Job UK: Client → VPN-UK (UK IP) → Layer2 → Google
```

## Tracking

Each job tracks:
- `country`: Target country code
- `origin_ip`: Actual IP used (verified)
- `origin_country`: Actual country of IP
- `origin_verified`: True if IP matches target country
- `layer2_mode`: Which proxy layer was used
- `duration_seconds`: Execution time
- `estimated_cost_usd`: Cost estimate

## Example Request

```json
{
  "name": "SEO Competition",
  "query": "best e-commerce platform comparison",
  "countries": "it,ch,uk",
  "scraper_type": "google_ai",
  "frequency": "1_per_day",
  "preferred_layer2": "unlocker"
}
```

This creates a template that will:
- Run the query once per day
- Execute in Italy, Switzerland, and UK (3 jobs)
- Use Web Unlocker for reliable Google scraping
- Track origin IPs to verify geo-targeting
""",
)
def create_template(template: PromptTemplateCreate):
    """Create a new prompt template."""
    # Validate countries
    requested_countries = [c.strip().lower() for c in template.countries.split(",")]
    invalid_countries = [c for c in requested_countries if c not in SUPPORTED_VPN_COUNTRIES]
    
    if invalid_countries:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid countries: {invalid_countries}. Supported: {SUPPORTED_VPN_COUNTRIES}"
        )
    
    # Validate scraper type
    valid_scrapers = ["google_ai", "chatgpt", "perplexity"]
    if template.scraper_type not in valid_scrapers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scraper_type: {template.scraper_type}. Supported: {valid_scrapers}"
        )
    
    # Validate layer2 mode
    valid_layers = ["auto", "direct", "residential", "unlocker", "browser"]
    if template.preferred_layer2 not in valid_layers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid preferred_layer2: {template.preferred_layer2}. Supported: {valid_layers}"
        )
    
    # Validate frequency
    valid_frequencies = ["hourly", "2_per_day", "1_per_day", "daily", "2_per_week", "weekly", "monthly"]
    if template.frequency not in valid_frequencies:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid frequency: {template.frequency}. Supported: {valid_frequencies}"
        )
    
    # Normalize countries (lowercase, no spaces)
    normalized_countries = ",".join(requested_countries)
    
    with Session(engine) as session:
        db_template = PromptTemplate(
            name=template.name,
            query=template.query,
            category=template.category,
            countries=normalized_countries,
            scraper_type=template.scraper_type,
            frequency=template.frequency,
            priority=template.priority,
            preferred_layer2=template.preferred_layer2,
        )
        session.add(db_template)
        session.commit()
        session.refresh(db_template)
        
        # Calculate jobs that will be created
        jobs_per_run = len(requested_countries)
        frequency_runs = {
            "hourly": 24, "2_per_day": 2, "1_per_day": 1, "daily": 1,
            "2_per_week": 0.29, "weekly": 0.14, "monthly": 0.03
        }
        daily_jobs = jobs_per_run * frequency_runs.get(template.frequency, 1)
        
        # Estimate costs
        layer_costs = {"direct": 0, "residential": 0.004, "unlocker": 0.008, "browser": 0.025, "auto": 0.008}
        layer2 = template.preferred_layer2
        if layer2 == "auto":
            layer2 = {"google_ai": "unlocker", "chatgpt": "browser", "perplexity": "browser"}.get(template.scraper_type, "direct")
        daily_cost = daily_jobs * layer_costs.get(layer2, 0)
        
        return {
            "id": db_template.id,
            "name": db_template.name,
            "query": db_template.query,
            "countries": requested_countries,
            "scraper_type": db_template.scraper_type,
            "frequency": db_template.frequency,
            "preferred_layer2": db_template.preferred_layer2,
            "message": "Template created successfully",
            "routing_info": {
                "jobs_per_run": jobs_per_run,
                "daily_jobs_estimate": round(daily_jobs, 1),
                "daily_cost_estimate_usd": round(daily_cost, 3),
                "vpn_containers": [f"vpn-{c}" for c in requested_countries],
            },
            "tracking_fields": [
                "origin_ip - Actual IP used",
                "origin_country - Actual country of IP",
                "origin_verified - True if IP matches target",
                "duration_seconds - Execution time",
                "layer2_mode - Proxy layer used",
                "estimated_cost_usd - Cost for this job",
            ],
        }


@app.get(
    "/api/templates",
    tags=["scheduling"],
    summary="List prompt templates",
    description="""Get all prompt templates with routing information.

Each template shows:
- Which countries the query will run in
- The VPN container used for each country
- Estimated daily jobs and costs
""",
)
def list_templates(active_only: bool = True):
    """List all prompt templates."""
    with Session(engine) as session:
        query = select(PromptTemplate)
        if active_only:
            query = query.where(PromptTemplate.is_active == True)
        
        templates = session.exec(query.order_by(PromptTemplate.priority)).all()
        
        # Calculate totals
        total_daily_jobs = 0
        total_daily_cost = 0
        
        template_list = []
        for t in templates:
            countries = t.countries.split(",")
            frequency_runs = {
                "hourly": 24, "2_per_day": 2, "1_per_day": 1, "daily": 1,
                "2_per_week": 0.29, "weekly": 0.14, "monthly": 0.03
            }
            layer_costs = {"direct": 0, "residential": 0.004, "unlocker": 0.008, "browser": 0.025, "auto": 0.008}
            
            jobs_per_run = len(countries)
            daily_jobs = jobs_per_run * frequency_runs.get(t.frequency, 1)
            
            layer2 = t.preferred_layer2
            if layer2 == "auto":
                layer2 = {"google_ai": "unlocker", "chatgpt": "browser", "perplexity": "browser"}.get(t.scraper_type, "direct")
            daily_cost = daily_jobs * layer_costs.get(layer2, 0)
            
            total_daily_jobs += daily_jobs
            total_daily_cost += daily_cost
            
            template_list.append({
                "id": t.id,
                "name": t.name,
                "query": t.query,
                "category": t.category,
                "countries": countries,
                "scraper_type": t.scraper_type,
                "frequency": t.frequency,
                "priority": t.priority,
                "preferred_layer2": t.preferred_layer2,
                "is_active": t.is_active,
                "routing": {
                    "vpn_containers": [f"vpn-{c}" for c in countries],
                    "jobs_per_run": jobs_per_run,
                    "daily_jobs": round(daily_jobs, 1),
                    "daily_cost_usd": round(daily_cost, 3),
                },
            })
        
        return {
            "count": len(templates),
            "totals": {
                "daily_jobs": round(total_daily_jobs, 1),
                "daily_cost_usd": round(total_daily_cost, 2),
                "monthly_cost_usd": round(total_daily_cost * 30, 2),
            },
            "supported_countries": SUPPORTED_VPN_COUNTRIES,
            "templates": template_list,
        }


@app.get(
    "/api/templates/{template_id}",
    tags=["scheduling"],
    summary="Get template by ID",
    description="Get a single template by its ID with full details.",
)
def get_template(template_id: int):
    """Get a template by ID."""
    with Session(engine) as session:
        template = session.get(PromptTemplate, template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        countries = template.countries.split(",")
        frequency_runs = {
            "hourly": 24, "2_per_day": 2, "1_per_day": 1, "daily": 1,
            "2_per_week": 0.29, "weekly": 0.14, "monthly": 0.03
        }
        layer_costs = {"direct": 0, "residential": 0.004, "unlocker": 0.008, "browser": 0.025, "auto": 0.008}
        
        jobs_per_run = len(countries)
        daily_jobs = jobs_per_run * frequency_runs.get(template.frequency, 1)
        
        layer2 = template.preferred_layer2
        if layer2 == "auto":
            layer2 = {"google_ai": "unlocker", "chatgpt": "browser", "perplexity": "browser"}.get(template.scraper_type, "direct")
        daily_cost = daily_jobs * layer_costs.get(layer2, 0)
        
        return {
            "id": template.id,
            "name": template.name,
            "query": template.query,
            "category": template.category,
            "countries": countries,
            "scraper_type": template.scraper_type,
            "frequency": template.frequency,
            "priority": template.priority,
            "preferred_layer2": template.preferred_layer2,
            "is_active": template.is_active,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "routing": {
                "vpn_containers": [f"vpn-{c}" for c in countries],
                "jobs_per_run": jobs_per_run,
                "daily_jobs": round(daily_jobs, 1),
                "daily_cost_usd": round(daily_cost, 3),
            },
        }


class PromptTemplateUpdate(BaseModel):
    """Request model for updating prompt templates"""
    name: str = Field(default=None, description="Template name")
    query: str = Field(default=None, description="The search query")
    category: str = Field(default=None, description="Category")
    countries: str = Field(default=None, description="Comma-separated country codes")
    scraper_type: str = Field(default=None, description="Scraper type")
    frequency: str = Field(default=None, description="Scheduling frequency")
    priority: int = Field(default=None, description="Priority 1=high, 2=medium, 3=low")
    preferred_layer2: str = Field(default=None, description="Preferred Layer 2 mode")
    is_active: bool = Field(default=None, description="Whether template is active")


@app.put(
    "/api/templates/{template_id}",
    tags=["scheduling"],
    summary="Update template",
    description="Update an existing template. Only provided fields will be updated.",
)
def update_template(template_id: int, update: PromptTemplateUpdate):
    """Update a template."""
    with Session(engine) as session:
        template = session.get(PromptTemplate, template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Validate countries if provided
        if update.countries:
            requested_countries = [c.strip().lower() for c in update.countries.split(",")]
            invalid_countries = [c for c in requested_countries if c not in SUPPORTED_VPN_COUNTRIES]
            if invalid_countries:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid countries: {invalid_countries}. Supported: {SUPPORTED_VPN_COUNTRIES}"
                )
            template.countries = ",".join(requested_countries)
        
        # Validate scraper_type if provided
        if update.scraper_type:
            valid_scrapers = ["google_ai", "chatgpt", "perplexity"]
            if update.scraper_type not in valid_scrapers:
                raise HTTPException(status_code=400, detail=f"Invalid scraper_type. Supported: {valid_scrapers}")
            template.scraper_type = update.scraper_type
        
        # Validate layer2 if provided
        if update.preferred_layer2:
            valid_layers = ["auto", "direct", "residential", "unlocker", "browser"]
            if update.preferred_layer2 not in valid_layers:
                raise HTTPException(status_code=400, detail=f"Invalid preferred_layer2. Supported: {valid_layers}")
            template.preferred_layer2 = update.preferred_layer2
        
        # Validate frequency if provided
        if update.frequency:
            valid_frequencies = ["hourly", "2_per_day", "1_per_day", "daily", "2_per_week", "weekly", "monthly"]
            if update.frequency not in valid_frequencies:
                raise HTTPException(status_code=400, detail=f"Invalid frequency. Supported: {valid_frequencies}")
            template.frequency = update.frequency
        
        # Update other fields
        if update.name is not None:
            template.name = update.name
        if update.query is not None:
            template.query = update.query
        if update.category is not None:
            template.category = update.category
        if update.priority is not None:
            template.priority = update.priority
        if update.is_active is not None:
            template.is_active = update.is_active
        
        session.add(template)
        session.commit()
        session.refresh(template)
        
        return {
            "id": template.id,
            "name": template.name,
            "message": "Template updated successfully",
            "updated_fields": [k for k, v in update.dict().items() if v is not None],
        }


@app.delete(
    "/api/templates/{template_id}",
    tags=["scheduling"],
    summary="Delete template",
    description="Delete a template. This will NOT delete any scheduled jobs created from this template.",
)
def delete_template(template_id: int):
    """Delete a template."""
    with Session(engine) as session:
        template = session.get(PromptTemplate, template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        template_name = template.name
        session.delete(template)
        session.commit()
        
        return {
            "message": f"Template '{template_name}' (ID: {template_id}) deleted successfully",
            "id": template_id,
        }


class BatchScheduleRequest(BaseModel):
    """Request model for batch scheduling"""
    template_ids: list[int] = Field(default=None, description="Template IDs to schedule (None = all active)")
    countries: list[str] = Field(default=None, description="Override countries (None = use template)")
    start_time: datetime = Field(default=None, description="When to start (None = spread throughout day)")
    daily_quota: int = Field(default=100, description="Maximum jobs per day")


@app.post(
    "/api/schedule-batch",
    tags=["scheduling"],
    summary="Schedule batch of prompts",
    description="""
    Schedule a batch of prompts from templates across multiple countries.
    
    Optimizes scheduling to:
    - Spread jobs throughout the day
    - Respect daily quota
    - Balance across countries
    - Minimize costs
    
    For 100 prompts/day across 3 countries with 3 runs each:
    - 100 prompts ÷ 3 countries = ~33 prompts per country
    - 33 prompts × 3 runs = ~11 unique queries per country
    """,
)
def schedule_batch(request: BatchScheduleRequest):
    """Schedule a batch of prompts."""
    with Session(engine) as session:
        # Get templates
        if request.template_ids:
            templates = session.exec(
                select(PromptTemplate).where(
                    PromptTemplate.id.in_(request.template_ids),
                    PromptTemplate.is_active == True
                )
            ).all()
        else:
            templates = session.exec(
                select(PromptTemplate).where(PromptTemplate.is_active == True)
            ).all()
        
        if not templates:
            raise HTTPException(status_code=400, detail="No active templates found")
        
        # Calculate schedule
        now = datetime.utcnow()
        today = now.strftime("%Y-%m-%d")
        stats = get_or_create_daily_stats(session, today)
        
        # Check quota
        available_quota = stats.daily_quota - stats.prompts_scheduled - stats.prompts_completed
        if available_quota <= 0:
            raise HTTPException(status_code=429, detail="Daily quota exceeded")
        
        # Build job list
        jobs_to_create = []
        for template in templates:
            countries = request.countries or template.countries.split(",")
            
            for country in countries:
                country = country.strip().lower()
                
                # Map frequency to runs per day
                runs_map = {
                    "hourly": 24,
                    "2_per_day": 2,
                    "1_per_day": 1,
                    "daily": 1,
                    "2_per_week": 0.29,  # ~2/week
                    "weekly": 0.14,
                    "monthly": 0.03,
                }
                runs_today = runs_map.get(template.frequency, 1)
                
                for run in range(int(max(1, runs_today))):
                    if len(jobs_to_create) >= available_quota:
                        break
                    
                    jobs_to_create.append({
                        "template": template,
                        "country": country,
                        "run": run + 1,
                    })
        
        # Spread jobs throughout the day
        jobs_created = []
        hours_remaining = 24 - now.hour
        interval_minutes = (hours_remaining * 60) / len(jobs_to_create) if jobs_to_create else 60
        
        for i, job_info in enumerate(jobs_to_create):
            template = job_info["template"]
            
            # Calculate start time
            if request.start_time:
                start = request.start_time + timedelta(minutes=i * interval_minutes)
            else:
                start = now + timedelta(minutes=i * interval_minutes)
            
            # Create job
            job = ScrapeJob(
                query=template.query,
                country=job_info["country"],
                scraper_type=template.scraper_type,
                status="scheduled",
                schedule_type="recurring",
                frequency=template.frequency,
                next_run_at=start,
                is_active=True,
                layer2_mode=template.preferred_layer2 if template.preferred_layer2 != "auto" else None,
                config_snapshot=json.dumps({
                    "template_id": template.id,
                    "template_name": template.name,
                    "run_number": job_info["run"],
                    "priority": template.priority,
                }),
            )
            session.add(job)
            jobs_created.append({
                "query": template.query[:50],
                "country": job_info["country"],
                "scheduled_at": start.isoformat(),
            })
        
        # Update stats
        stats.prompts_scheduled += len(jobs_created)
        stats.quota_remaining = stats.daily_quota - stats.prompts_scheduled - stats.prompts_completed
        session.add(stats)
        session.commit()
        
        return {
            "scheduled": len(jobs_created),
            "quota_remaining": stats.quota_remaining,
            "first_job_at": jobs_created[0]["scheduled_at"] if jobs_created else None,
            "last_job_at": jobs_created[-1]["scheduled_at"] if jobs_created else None,
            "jobs": jobs_created[:20],  # Show first 20
            "message": f"Scheduled {len(jobs_created)} jobs across {len(set(j['country'] for j in jobs_created))} countries",
        }


@app.get(
    "/api/cost-estimate",
    tags=["analytics"],
    summary="Estimate daily costs",
    description="""
    Estimate costs for running prompts with different configurations.
    
    Cost breakdown:
    - VPN Direct: Free (after VPN subscription)
    - Residential: ~$8.40/GB (~$0.004 per request @ 500KB)
    - Unlocker: ~$3-10/1000 requests ($0.003-0.01 per request)
    - Browser: ~$0.01-0.03 per request
    """,
)
def estimate_costs(
    prompts: int = 100,
    countries: int = 3,
    runs_per_prompt: int = 3,
    scraper_type: str = "google_ai",
):
    """Estimate daily costs for different configurations."""
    total_jobs = prompts * runs_per_prompt
    jobs_per_country = total_jobs / countries
    
    # Cost per request by layer
    costs = {
        "direct": 0.0,  # Free
        "residential": 0.004,  # ~$8.40/GB @ 500KB avg
        "unlocker": 0.008,  # ~$8/1000 for Google
        "browser": 0.025,  # ~$0.025 avg
    }
    
    # Recommended layer by scraper
    recommended = {
        "google_ai": "unlocker",
        "chatgpt": "browser",
        "perplexity": "browser",
    }
    
    rec_layer = recommended.get(scraper_type, "direct")
    rec_cost = costs[rec_layer]
    
    return {
        "configuration": {
            "prompts": prompts,
            "countries": countries,
            "runs_per_prompt": runs_per_prompt,
            "total_jobs": total_jobs,
            "jobs_per_country": jobs_per_country,
            "scraper_type": scraper_type,
        },
        "recommended": {
            "layer": rec_layer,
            "cost_per_request": rec_cost,
            "daily_cost": round(total_jobs * rec_cost, 2),
            "monthly_cost": round(total_jobs * rec_cost * 30, 2),
        },
        "alternatives": {
            "vpn_direct": {
                "cost_per_request": 0,
                "daily_cost": 0,
                "monthly_cost": 0,
                "success_rate": "~70% (may hit CAPTCHA)",
            },
            "residential": {
                "cost_per_request": costs["residential"],
                "daily_cost": round(total_jobs * costs["residential"], 2),
                "monthly_cost": round(total_jobs * costs["residential"] * 30, 2),
                "success_rate": "~85%",
            },
            "unlocker": {
                "cost_per_request": costs["unlocker"],
                "daily_cost": round(total_jobs * costs["unlocker"], 2),
                "monthly_cost": round(total_jobs * costs["unlocker"] * 30, 2),
                "success_rate": "~95%",
            },
            "browser": {
                "cost_per_request": costs["browser"],
                "daily_cost": round(total_jobs * costs["browser"], 2),
                "monthly_cost": round(total_jobs * costs["browser"] * 30, 2),
                "success_rate": "~98%",
            },
        },
        "optimization_tips": [
            "Use VPN Direct for simple sites (free)",
            "Use Unlocker for Google (~$0.008/req, 95% success)",
            "Use Browser only for ChatGPT/Perplexity (~$0.025/req)",
            "Run low-priority prompts at night (lower traffic)",
            "Batch similar queries to reduce overhead",
        ],
    }


@app.put(
    "/api/daily-quota",
    tags=["analytics"],
    summary="Update daily quota",
    description="Update the daily prompt quota.",
)
def update_daily_quota(quota: int = 100):
    """Update daily quota."""
    with Session(engine) as session:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        stats = get_or_create_daily_stats(session, today)
        stats.daily_quota = quota
        stats.quota_remaining = quota - stats.prompts_completed - stats.prompts_scheduled
        session.add(stats)
        session.commit()
        
        return {
            "daily_quota": quota,
            "quota_remaining": stats.quota_remaining,
            "prompts_used": stats.prompts_completed + stats.prompts_scheduled,
        }


# =============================================================================
# API REFERENCE & DOCUMENTATION
# =============================================================================

@app.get(
    "/api/reference",
    tags=["documentation"],
    summary="API Reference",
    description="Complete API reference with all options and examples.",
)
def get_api_reference():
    """Get complete API reference."""
    return {
        "overview": {
            "description": "AISEO Scraping API with geo-targeted VPN routing",
            "architecture": {
                "layer1": "VPN (ProtonVPN per country) - Always active",
                "layer2": "Optional proxy enhancement (direct/residential/unlocker/browser)",
            },
            "flow": "Client → VPN-{country} → Layer2 → Target Website",
        },
        "supported_options": {
            "countries": {
                "description": "VPN exit countries",
                "options": SUPPORTED_VPN_COUNTRIES,
                "example": "it,ch,uk",
                "note": "Each country has its own VPN container (vpn-it, vpn-ch, etc.)",
            },
            "scraper_types": {
                "description": "Target websites to scrape",
                "options": {
                    "google_ai": {
                        "description": "Google AI Mode (AI-generated answers)",
                        "recommended_layer2": "unlocker",
                        "success_rate": "~95%",
                    },
                    "chatgpt": {
                        "description": "ChatGPT (requires browser automation)",
                        "recommended_layer2": "browser",
                        "success_rate": "~98%",
                    },
                    "perplexity": {
                        "description": "Perplexity AI search",
                        "recommended_layer2": "browser",
                        "success_rate": "~98%",
                    },
                },
            },
            "layer2_modes": {
                "description": "Proxy layer on top of VPN",
                "options": {
                    "auto": {
                        "description": "Auto-select based on scraper_type",
                        "cost": "Varies",
                    },
                    "direct": {
                        "description": "VPN only, no additional proxy",
                        "cost": "$0.00/request",
                        "success_rate": "~70%",
                        "best_for": "Simple sites, testing",
                    },
                    "residential": {
                        "description": "VPN + Bright Data residential IP",
                        "cost": "~$0.004/request",
                        "success_rate": "~85%",
                        "best_for": "Sites blocking datacenter IPs",
                    },
                    "unlocker": {
                        "description": "VPN + Web Unlocker with CAPTCHA solving",
                        "cost": "~$0.008/request",
                        "success_rate": "~95%",
                        "best_for": "Google, protected sites",
                    },
                    "browser": {
                        "description": "VPN + Cloud browser automation",
                        "cost": "~$0.025/request",
                        "success_rate": "~98%",
                        "best_for": "ChatGPT, JavaScript-heavy sites",
                    },
                },
            },
            "frequencies": {
                "description": "How often to run scheduled jobs",
                "options": {
                    "hourly": {"interval": "1 hour", "runs_per_day": 24},
                    "2_per_day": {"interval": "12 hours", "runs_per_day": 2},
                    "1_per_day": {"interval": "24 hours", "runs_per_day": 1},
                    "daily": {"interval": "24 hours", "runs_per_day": 1},
                    "2_per_week": {"interval": "3.5 days", "runs_per_day": 0.29},
                    "weekly": {"interval": "7 days", "runs_per_day": 0.14},
                    "monthly": {"interval": "30 days", "runs_per_day": 0.03},
                },
            },
        },
        "tracking_fields": {
            "description": "Fields tracked for each job execution",
            "fields": {
                "country": "Target country code (e.g., 'it')",
                "origin_ip": "Actual IP address used",
                "origin_country": "Actual country of the IP",
                "origin_verified": "True if origin matches target country",
                "layer2_mode": "Which Layer 2 mode was used",
                "duration_seconds": "Time to complete the job",
                "response_size_kb": "Size of response in KB",
                "estimated_cost_usd": "Estimated cost for this job",
                "status": "pending/running/completed/failed/scheduled",
            },
        },
        "endpoints": {
            "templates": {
                "POST /api/templates": {
                    "description": "Create a prompt template",
                    "example": {
                        "name": "SEO Competition",
                        "query": "best e-commerce platform comparison",
                        "countries": "it,ch,uk",
                        "scraper_type": "google_ai",
                        "frequency": "1_per_day",
                        "preferred_layer2": "unlocker",
                    },
                },
                "GET /api/templates": "List all templates with routing info",
            },
            "scheduling": {
                "POST /api/schedule-batch": "Schedule batch of prompts from templates",
                "GET /api/scheduled-jobs": "List active scheduled jobs",
                "GET /api/scheduler-status": "Scheduler health and upcoming jobs",
            },
            "monitoring": {
                "GET /api/daily-stats": "Today's statistics, quota, and costs",
                "GET /api/active-sessions": "Currently running jobs",
                "GET /api/job-history": "Recent job execution history",
                "GET /api/cost-estimate": "Estimate costs for a configuration",
            },
            "scraping": {
                "POST /api/jobs/scrape": "Create and run a scrape job",
                "GET /api/jobs/{job_id}": "Get job details and results",
            },
        },
        "examples": {
            "100_prompts_3_countries": {
                "description": "Run 100 prompts daily across IT, CH, UK",
                "setup": [
                    "1. Create templates for your queries",
                    "2. Set countries='it,ch,uk' on each template",
                    "3. Use frequency='1_per_day' for daily runs",
                    "4. Schedule batch to spread throughout day",
                ],
                "cost_estimate": {
                    "total_jobs": "100 prompts × 3 countries = 300 jobs/day",
                    "with_unlocker": "$2.40/day, $72/month",
                    "with_browser": "$7.50/day, $225/month",
                },
            },
        },
    }


# ==============================================================================
# DOCKER LOGS & ADMIN ENDPOINTS
# ==============================================================================

@app.get(
    "/api/docker/logs/{container}",
    tags=["system"],
    summary="Get Docker container logs",
    description="Fetch logs from a Docker container. Useful for debugging and monitoring.",
)
async def get_docker_logs(container: str, lines: int = 100, since: str = None):
    """
    Get logs from a Docker container.
    
    Args:
        container: Container name (e.g., 'aiseo-scraper', 'vpn-it')
        lines: Number of lines to return (default 100, max 1000)
        since: Only return logs since this time (e.g., '10m', '1h')
    
    Returns:
        Container logs as text
    """
    import subprocess
    
    # Validate container name to prevent command injection
    allowed_containers = [
        'aiseo-scraper', 'aiseo-api', 'aiseo-admin', 'aiseo-db-ui', 'aiseo-api-tester',
        'vpn-it', 'vpn-fr', 'vpn-de', 'vpn-uk', 'vpn-es', 'vpn-nl', 'vpn-ch', 'vpn-se',
        'vpn-manager',
        'residential-proxy-it', 'residential-proxy-fr', 'residential-proxy-de',
        'residential-proxy-uk', 'residential-proxy-es', 'residential-proxy-nl',
        'residential-proxy-ch', 'residential-proxy-se',
    ]
    
    if container not in allowed_containers:
        raise HTTPException(status_code=400, detail=f"Invalid container. Allowed: {', '.join(allowed_containers)}")
    
    lines = min(lines, 1000)  # Cap at 1000 lines
    
    cmd = ["docker", "logs", container, f"--tail={lines}"]
    if since:
        cmd.extend(["--since", since])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        logs = result.stdout + result.stderr
        
        return {
            "container": container,
            "lines_requested": lines,
            "logs": logs,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout fetching logs")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/docker/containers",
    tags=["system"],
    summary="List Docker containers",
    description="List all running Docker containers with their status.",
)
async def list_docker_containers():
    """List all Docker containers with status."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True, text=True, timeout=10
        )
        
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                containers.append({
                    "name": parts[0] if len(parts) > 0 else "",
                    "status": parts[1] if len(parts) > 1 else "",
                    "ports": parts[2] if len(parts) > 2 else "",
                })
        
        return {"containers": containers, "count": len(containers)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# VPN MONITORING ENDPOINTS
# ==============================================================================

@app.get(
    "/api/vpn/ip/{country}",
    tags=["vpn"],
    summary="Get VPN container IP",
    description="Get the current public IP address of a VPN container.",
)
async def get_vpn_ip(country: str):
    """Get the current public IP of a VPN container."""
    import subprocess
    
    allowed_countries = ['it', 'fr', 'de', 'uk', 'es', 'nl', 'ch', 'se']
    if country.lower() not in allowed_countries:
        raise HTTPException(status_code=400, detail=f"Invalid country. Allowed: {', '.join(allowed_countries)}")
    
    container = f"vpn-{country.lower()}"
    
    try:
        # Use api.ipify.org which returns plain IP (works with wget in Alpine)
        result = subprocess.run(
            ["docker", "exec", container, "wget", "-q", "-O", "-", "-T", "5", "http://api.ipify.org"],
            capture_output=True, text=True, timeout=15
        )
        ip = result.stdout.strip()
        
        if not ip or result.returncode != 0:
            # Try alternative service
            result = subprocess.run(
                ["docker", "exec", container, "wget", "-q", "-O", "-", "-T", "5", "http://icanhazip.com"],
                capture_output=True, text=True, timeout=15
            )
            ip = result.stdout.strip()
        
        # Validate IP format (basic check for IPv4)
        if ip and len(ip) <= 15 and ip.count('.') == 3:
            return {
                "container": container,
                "country": country.lower(),
                "ip": ip,
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            return {
                "container": container,
                "country": country.lower(),
                "ip": "unavailable",
                "raw_output": ip[:50] if ip else "empty",
                "timestamp": datetime.utcnow().isoformat(),
            }
    except subprocess.TimeoutExpired:
        return {"container": container, "country": country.lower(), "ip": "timeout", "error": "Request timed out"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/vpn/rotate/{country}",
    tags=["vpn"],
    summary="Rotate VPN IP",
    description="Trigger IP rotation for a VPN container by restarting it.",
)
async def rotate_vpn_ip(country: str):
    """Rotate IP address for a VPN container."""
    import subprocess
    
    allowed_countries = ['it', 'fr', 'de', 'uk', 'es', 'nl', 'ch', 'se']
    if country.lower() not in allowed_countries:
        raise HTTPException(status_code=400, detail=f"Invalid country. Allowed: {', '.join(allowed_countries)}")
    
    container = f"vpn-{country.lower()}"
    
    try:
        # Restart the VPN container to get new IP
        result = subprocess.run(
            ["docker", "restart", container],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            return {
                "container": container,
                "status": "rotating",
                "message": f"Container {container} is restarting for IP rotation",
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to restart: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Restart command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/vpn/status",
    tags=["vpn"],
    summary="Get all VPN status",
    description="Get status of all VPN containers including health and uptime.",
)
async def get_all_vpn_status():
    """Get status of all VPN containers."""
    import subprocess
    
    countries = ['it', 'fr', 'de', 'uk', 'es', 'nl', 'ch', 'se']
    vpn_status = []
    
    try:
        # Get all container statuses
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=vpn-", "--format", "{{.Names}}\t{{.Status}}\t{{.State}}"],
            capture_output=True, text=True, timeout=10
        )
        
        status_map = {}
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                name = parts[0] if len(parts) > 0 else ""
                status_map[name] = {
                    "status": parts[1] if len(parts) > 1 else "",
                    "state": parts[2] if len(parts) > 2 else "",
                }
        
        for country in countries:
            container = f"vpn-{country}"
            info = status_map.get(container, {})
            
            is_running = "Up" in info.get("status", "")
            is_healthy = "healthy" in info.get("status", "")
            
            vpn_status.append({
                "country": country,
                "container": container,
                "running": is_running,
                "healthy": is_healthy,
                "status": info.get("status", "not found"),
            })
        
        healthy_count = sum(1 for v in vpn_status if v["healthy"])
        running_count = sum(1 for v in vpn_status if v["running"])
        
        return {
            "vpns": vpn_status,
            "summary": {
                "total": len(countries),
                "running": running_count,
                "healthy": healthy_count,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# DATABASE STATISTICS ENDPOINT
# ==============================================================================

@app.get(
    "/api/stats/database",
    tags=["system"],
    summary="Get database statistics",
    description="Get comprehensive statistics about jobs, prompts, and sources in the database.",
)
async def get_database_stats():
    """
    Get database statistics for the admin dashboard.
    
    Returns counts, success rates, and recent activity.
    """
    from datetime import timedelta
    
    with Session(engine) as session:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=7)
        
        # Total counts
        total_jobs = session.exec(select(func.count(ScrapeJob.id))).one()
        total_prompts = session.exec(select(func.count(Prompt.id))).one()
        total_sources = session.exec(select(func.count(Source.id))).one()
        total_templates = session.exec(select(func.count(PromptTemplate.id))).one()
        total_brands = session.exec(select(func.count(Brand.id))).one()
        
        # Jobs by status
        jobs_by_status = {}
        for status in ["completed", "failed", "running", "pending", "scheduled"]:
            count = session.exec(
                select(func.count(ScrapeJob.id)).where(ScrapeJob.status == status)
            ).one()
            jobs_by_status[status] = count
        
        # Today's jobs
        today_jobs = session.exec(
            select(func.count(ScrapeJob.id)).where(ScrapeJob.created_at >= today_start)
        ).one()
        today_completed = session.exec(
            select(func.count(ScrapeJob.id)).where(
                ScrapeJob.created_at >= today_start,
                ScrapeJob.status == "completed"
            )
        ).one()
        today_failed = session.exec(
            select(func.count(ScrapeJob.id)).where(
                ScrapeJob.created_at >= today_start,
                ScrapeJob.status == "failed"
            )
        ).one()
        
        # Week stats
        week_jobs = session.exec(
            select(func.count(ScrapeJob.id)).where(ScrapeJob.created_at >= week_start)
        ).one()
        week_completed = session.exec(
            select(func.count(ScrapeJob.id)).where(
                ScrapeJob.created_at >= week_start,
                ScrapeJob.status == "completed"
            )
        ).one()
        
        # Average duration
        avg_duration = session.exec(
            select(func.avg(ScrapeJob.duration_seconds)).where(
                ScrapeJob.duration_seconds != None,
                ScrapeJob.status == "completed"
            )
        ).one() or 0
        
        # Total cost (estimated)
        total_cost = session.exec(
            select(func.sum(ScrapeJob.estimated_cost_usd)).where(
                ScrapeJob.estimated_cost_usd != None
            )
        ).one() or 0
        today_cost = session.exec(
            select(func.sum(ScrapeJob.estimated_cost_usd)).where(
                ScrapeJob.created_at >= today_start,
                ScrapeJob.estimated_cost_usd != None
            )
        ).one() or 0
        
        # Jobs by country
        jobs_by_country = {}
        for country in ["it", "fr", "de", "uk", "es", "nl", "ch", "se"]:
            count = session.exec(
                select(func.count(ScrapeJob.id)).where(ScrapeJob.country == country)
            ).one()
            if count > 0:
                jobs_by_country[country] = count
        
        # Jobs by scraper type
        jobs_by_scraper = {}
        for scraper in ["google_ai", "chatgpt", "perplexity"]:
            count = session.exec(
                select(func.count(ScrapeJob.id)).where(ScrapeJob.scraper_type == scraper)
            ).one()
            if count > 0:
                jobs_by_scraper[scraper] = count
        
        # Recent failed jobs (last 5)
        recent_failed = session.exec(
            select(ScrapeJob).where(ScrapeJob.status == "failed")
            .order_by(ScrapeJob.created_at.desc()).limit(5)
        ).all()
        
        return {
            "totals": {
                "jobs": total_jobs,
                "prompts": total_prompts,
                "sources": total_sources,
                "templates": total_templates,
                "brands": total_brands,
            },
            "jobs_by_status": jobs_by_status,
            "today": {
                "total": today_jobs,
                "completed": today_completed,
                "failed": today_failed,
                "success_rate": round(today_completed / today_jobs * 100, 1) if today_jobs > 0 else 100,
                "cost_usd": round(today_cost, 4),
            },
            "week": {
                "total": week_jobs,
                "completed": week_completed,
                "success_rate": round(week_completed / week_jobs * 100, 1) if week_jobs > 0 else 100,
            },
            "performance": {
                "avg_duration_seconds": round(avg_duration, 2),
                "total_cost_usd": round(total_cost, 4),
            },
            "jobs_by_country": jobs_by_country,
            "jobs_by_scraper": jobs_by_scraper,
            "recent_failures": [
                {
                    "id": j.id,
                    "query": j.query[:50] if j.query else "",
                    "error": j.error[:100] if j.error else "Unknown",
                    "created_at": j.created_at.isoformat() if j.created_at else None,
                }
                for j in recent_failed
            ],
            "generated_at": now.isoformat(),
        }


# ==============================================================================
# SCREENSHOTS & JOB DETAILS ENDPOINTS
# ==============================================================================

SCREENSHOTS_DIR = os.environ.get("SCREENSHOTS_DIR", "/app/data/screenshots")


@app.get(
    "/api/screenshots/{filename}",
    tags=["system"],
    summary="Get screenshot image",
    description="Serve a screenshot file by filename.",
)
async def get_screenshot(filename: str):
    """
    Serve a screenshot image file.
    
    Args:
        filename: Screenshot filename (e.g., 'job_123_error_20260201_123456.png')
    
    Returns:
        PNG image file
    """
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    # Security: validate filename (no path traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Check multiple possible locations
    possible_paths = [
        Path(SCREENSHOTS_DIR) / filename,
        Path("/app/data/screenshots") / filename,
        Path("data/screenshots") / filename,
    ]
    
    for filepath in possible_paths:
        if filepath.exists() and filepath.is_file():
            return FileResponse(
                path=str(filepath),
                media_type="image/png",
                filename=filename,
            )
    
    raise HTTPException(status_code=404, detail=f"Screenshot not found: {filename}")


@app.get(
    "/api/screenshots",
    tags=["system"],
    summary="List all screenshots",
    description="List all available screenshots with metadata.",
)
async def list_screenshots(job_id: int = None, limit: int = 50):
    """
    List available screenshots.
    
    Args:
        job_id: Filter by job ID (optional)
        limit: Maximum number of results (default 50)
    
    Returns:
        List of screenshot files with metadata
    """
    from pathlib import Path
    import os
    
    screenshots = []
    possible_dirs = [
        Path(SCREENSHOTS_DIR),
        Path("/app/data/screenshots"),
        Path("data/screenshots"),
    ]
    
    screenshots_dir = None
    for d in possible_dirs:
        if d.exists():
            screenshots_dir = d
            break
    
    if not screenshots_dir:
        return {"screenshots": [], "count": 0, "directory": None}
    
    for f in sorted(screenshots_dir.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True):
        # Parse filename to extract job_id if present
        name = f.stem
        file_job_id = None
        if name.startswith("job_"):
            parts = name.split("_")
            if len(parts) >= 2:
                try:
                    file_job_id = int(parts[1])
                except:
                    pass
        
        # Filter by job_id if specified
        if job_id is not None and file_job_id != job_id:
            continue
        
        stat = f.stat()
        screenshots.append({
            "filename": f.name,
            "job_id": file_job_id,
            "size_kb": round(stat.st_size / 1024, 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "url": f"/api/screenshots/{f.name}",
        })
        
        if len(screenshots) >= limit:
            break
    
    return {
        "screenshots": screenshots,
        "count": len(screenshots),
        "directory": str(screenshots_dir),
    }


@app.get(
    "/api/jobs/{job_id}/details",
    tags=["jobs"],
    summary="Get detailed job information",
    description="Get comprehensive job details including config, logs, screenshots, and error info.",
)
async def get_job_details(job_id: int):
    """
    Get detailed information about a job for debugging.
    
    Returns:
        - Basic job info (status, query, country, etc.)
        - Configuration snapshot (parsed JSON)
        - Profile data (parsed JSON)
        - Error message and traceback
        - Screenshot URL (if available)
        - HTML snapshot size
        - Network chain info
        - Cost and duration
    """
    with Session(engine) as session:
        job = session.get(ScrapeJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Parse JSON fields
        config = {}
        profile = {}
        try:
            if job.config_snapshot:
                config = json.loads(job.config_snapshot)
        except:
            pass
        try:
            if job.profile_data:
                profile = json.loads(job.profile_data)
        except:
            pass
        
        # Find screenshots for this job
        screenshots = []
        from pathlib import Path
        for d in [Path(SCREENSHOTS_DIR), Path("/app/data/screenshots"), Path("data/screenshots")]:
            if d.exists():
                for f in d.glob(f"job_{job_id}_*.png"):
                    screenshots.append({
                        "filename": f.name,
                        "url": f"/api/screenshots/{f.name}",
                        "size_kb": round(f.stat().st_size / 1024, 2),
                    })
                # Also check for error screenshots without job_id prefix
                for f in d.glob(f"*error*{job_id}*.png"):
                    if f.name not in [s["filename"] for s in screenshots]:
                        screenshots.append({
                            "filename": f.name,
                            "url": f"/api/screenshots/{f.name}",
                            "size_kb": round(f.stat().st_size / 1024, 2),
                        })
                break
        
        return {
            "id": job.id,
            "status": job.status,
            "query": job.query,
            "country": job.country,
            "scraper_type": config.get("scraper_type", "unknown"),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "duration_seconds": job.duration_seconds,
            
            "error": {
                "message": job.error,
                "has_error": bool(job.error),
            } if job.error else None,
            
            "network": {
                "layer2_mode": job.layer2_mode,
                "proxy_used": job.proxy_used,
                "origin_ip": job.origin_ip,
                "origin_country": job.origin_country,
                "origin_verified": job.origin_verified,
            },
            
            "cost": {
                "estimated_usd": job.estimated_cost_usd,
                "response_size_kb": job.response_size_kb,
            },
            
            "config": config,
            "profile": profile,
            
            "screenshots": screenshots,
            "screenshot_count": len(screenshots),
            
            "html_snapshot": {
                "available": bool(job.html_snapshot),
                "size_kb": round(len(job.html_snapshot) / 1024, 2) if job.html_snapshot else 0,
                "url": f"/api/jobs/{job_id}/html" if job.html_snapshot else None,
            },
            
            "links": {
                "sqladmin": f"/admin/scrape-job/details/{job_id}",
                "html_snapshot": f"/api/jobs/{job_id}/html" if job.html_snapshot else None,
                "screenshots": screenshots,
            },
        }


@app.get(
    "/api/jobs/{job_id}/html",
    tags=["jobs"],
    summary="Get job HTML snapshot",
    description="Get the raw HTML content captured during the scrape.",
)
async def get_job_html(job_id: int):
    """Get the HTML snapshot from a job."""
    from fastapi.responses import HTMLResponse
    
    with Session(engine) as session:
        job = session.get(ScrapeJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        if not job.html_snapshot:
            raise HTTPException(status_code=404, detail="No HTML snapshot available for this job")
        
        return HTMLResponse(content=job.html_snapshot)


@app.get(
    "/api/admin/docs",
    tags=["system"],
    summary="Admin Dashboard Documentation",
    description="Complete documentation for the admin dashboard interface.",
)
async def get_admin_documentation():
    """
    Returns comprehensive documentation for the admin dashboard.
    """
    return {
        "version": "1.2.0",
        "last_updated": "2026-02-01",
        "dashboard_url": "http://localhost:9091",
        
        "sections": {
            "dashboard": {
                "title": "Dashboard",
                "description": "Real-time system overview with quick stats and actions",
                "features": [
                    "Active jobs count - Jobs currently running in background",
                    "Today's jobs - Total jobs created today with completion count",
                    "VPN status - Status of all 8 country VPN containers",
                    "Cost estimate - Estimated Bright Data costs based on completed jobs",
                    "Network chain visualization - Layer 1 → Layer 2 → Layer 3 flow",
                    "Quick scrape form - Create one-time scrape jobs instantly",
                    "Recent jobs list - Last 8 jobs with status indicators",
                ],
                "keyboard_shortcuts": {
                    "R": "Refresh dashboard data",
                },
                "auto_refresh": "Every 5 seconds (configurable in Settings)",
            },
            
            "jobs_manager": {
                "title": "Jobs Manager",
                "description": "Create, monitor, and manage all scraping jobs",
                "features": [
                    "Filter by status: All, Running, Scheduled, Completed, Failed",
                    "Search jobs by query text",
                    "View job details in SQLAdmin",
                    "View HTML snapshots for completed jobs",
                    "Create new jobs with full configuration",
                ],
                "api_endpoints": {
                    "GET /api/jobs": "List all jobs (optional ?status= filter)",
                    "GET /api/jobs/{id}": "Get job details including metadata",
                    "GET /api/jobs/{id}/html": "Get raw HTML snapshot",
                    "POST /api/jobs/scrape": "Create new scrape job",
                },
                "code_reference": "backend/main.py:2328-2500",
            },
            
            "layer1_vpn": {
                "title": "Layer 1: VPN Network",
                "description": "ProtonVPN connections via Gluetun containers providing datacenter IPs",
                "countries": {
                    "it": {"name": "Italy", "container": "vpn-it", "proxy_port": 8888, "control_port": 9004},
                    "fr": {"name": "France", "container": "vpn-fr", "proxy_port": 8888, "control_port": 9001},
                    "de": {"name": "Germany", "container": "vpn-de", "proxy_port": 8888, "control_port": 9002},
                    "uk": {"name": "United Kingdom", "container": "vpn-uk", "proxy_port": 8888, "control_port": 9007},
                    "es": {"name": "Spain", "container": "vpn-es", "proxy_port": 8888, "control_port": 9005},
                    "nl": {"name": "Netherlands", "container": "vpn-nl", "proxy_port": 8888, "control_port": 9003},
                    "ch": {"name": "Switzerland", "container": "vpn-ch", "proxy_port": 8888, "control_port": 9008},
                    "se": {"name": "Sweden", "container": "vpn-se", "proxy_port": 8888, "control_port": 9006},
                },
                "features": [
                    "Auto IP rotation every 10 minutes via vpn-manager",
                    "Health check monitoring",
                    "Manual IP rotation via control server",
                    "View container logs",
                ],
                "useful_commands": {
                    "check_ip": "docker exec vpn-it curl -s ifconfig.me",
                    "restart_vpn": "docker restart vpn-it",
                    "view_logs": "docker logs vpn-it --tail=50",
                    "rotate_ip": "curl http://localhost:9004/v1/openvpn/portforwarded",
                },
                "code_reference": "docker-compose.yml:46-200",
            },
            
            "layer2_proxy": {
                "title": "Layer 2: Bright Data Proxy",
                "description": "Residential proxies and Scraping Browser for anti-detection",
                "services": {
                    "residential_proxy": {
                        "description": "Real residential IPs from ISPs worldwide",
                        "zone": "aiseo_1",
                        "host": "brd.superproxy.io",
                        "port": 33335,
                        "cost": "$8.40/GB",
                        "use_case": "Perplexity, rate-limited sites, stealth scraping",
                        "auth_format": "brd-customer-{customer_id}-zone-{zone}-country-{country}:{password}",
                    },
                    "scraping_browser": {
                        "description": "Cloud browser with CAPTCHA solving and fingerprint management",
                        "zone": "scraping_browser1",
                        "endpoint": "wss://brd.superproxy.io:9222",
                        "cost": "$0.01 base + $0.02 per CAPTCHA",
                        "use_case": "Google AI Mode, ChatGPT, JavaScript-heavy sites",
                        "features": [
                            "Automatic CAPTCHA solving",
                            "Browser fingerprint management",
                            "Proxy rotation",
                            "Session recovery",
                            "Anti-bot bypass",
                        ],
                    },
                },
                "geo_targeting": {
                    "format": "-country-{code}",
                    "example": "wss://brd-customer-hl_0d78e46f-zone-scraping_browser1-country-it:password@brd.superproxy.io:9222",
                },
                "code_reference": "config/scraper_defaults.json:191-231",
            },
            
            "layer3_profiles": {
                "title": "Layer 3: Device Profiles",
                "description": "Viewport, user agent, and device emulation configurations",
                "profile_types": {
                    "phones": {
                        "iphone_14": {
                            "width": 390, "height": 844, "scale": 3,
                            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
                            "is_mobile": True, "has_touch": True,
                        },
                        "iphone_15_pro": {
                            "width": 393, "height": 852, "scale": 3,
                            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
                            "is_mobile": True, "has_touch": True,
                        },
                        "pixel_7": {
                            "width": 412, "height": 915, "scale": 2.625,
                            "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36",
                            "is_mobile": True, "has_touch": True,
                        },
                        "samsung_s23": {
                            "width": 360, "height": 780, "scale": 3,
                            "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36",
                            "is_mobile": True, "has_touch": True,
                        },
                    },
                    "tablets": {
                        "ipad_pro_12": {
                            "width": 1024, "height": 1366, "scale": 2,
                            "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
                            "is_mobile": True, "has_touch": True,
                        },
                        "ipad_air": {
                            "width": 820, "height": 1180, "scale": 2,
                            "user_agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
                            "is_mobile": True, "has_touch": True,
                        },
                        "galaxy_tab_s8": {
                            "width": 800, "height": 1280, "scale": 2,
                            "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-X700) AppleWebKit/537.36",
                            "is_mobile": True, "has_touch": True,
                        },
                    },
                    "desktops": {
                        "desktop_1080p": {
                            "width": 1920, "height": 1080, "scale": 1,
                            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
                            "is_mobile": False, "has_touch": False,
                        },
                        "desktop_1440p": {
                            "width": 2560, "height": 1440, "scale": 1,
                            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
                            "is_mobile": False, "has_touch": False,
                        },
                        "macbook_pro_14": {
                            "width": 1512, "height": 982, "scale": 2,
                            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/604.1",
                            "is_mobile": False, "has_touch": False,
                        },
                        "macbook_air_13": {
                            "width": 1470, "height": 956, "scale": 2,
                            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/604.1",
                            "is_mobile": False, "has_touch": False,
                        },
                        "linux_desktop": {
                            "width": 1920, "height": 1080, "scale": 1,
                            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0",
                            "is_mobile": False, "has_touch": False,
                        },
                    },
                },
                "code_reference": "config/scraper_defaults.json:6-32",
            },
            
            "scrapers": {
                "title": "Scraper Configurations",
                "description": "Available scraper types and their configurations",
                "types": {
                    "google_ai": {
                        "name": "Google AI Mode",
                        "status": "working",
                        "description": "Google Search with AI Overviews (udm=50 parameter)",
                        "layer2_mode": "scraping_browser",
                        "features": [
                            "Geolocation verification via IP check",
                            "Auto CAPTCHA solving",
                            "Full text extraction",
                            "Source link extraction",
                            "Cookie consent handling",
                        ],
                        "cost_per_request": "$0.015-0.035",
                        "code_file": "src/scrapers/brightdata_browser_scraper.py",
                    },
                    "chatgpt": {
                        "name": "ChatGPT",
                        "status": "working",
                        "description": "Direct ChatGPT scraping via chatgpt.com",
                        "layer2_mode": "scraping_browser",
                        "features": [
                            "Login popup auto-dismiss",
                            "CAPTCHA solving",
                            "Response extraction",
                        ],
                        "cost_per_request": "$0.02-0.04",
                        "code_file": "src/scrapers/chatgpt_scraper.py",
                    },
                    "perplexity": {
                        "name": "Perplexity AI",
                        "status": "working",
                        "description": "Perplexity AI search via perplexity.ai",
                        "layer2_mode": "residential",
                        "vpn_required": True,
                        "features": [
                            "Stealth mode",
                            "VPN + Residential proxy chain",
                            "Response extraction from .prose elements",
                        ],
                        "cost_per_request": "~$0.01-0.05 (bandwidth based)",
                        "code_file": "src/scrapers/perplexity_scraper.py",
                    },
                },
            },
            
            "templates": {
                "title": "Prompt Templates",
                "description": "Reusable templates for batch scheduling",
                "fields": {
                    "name": "Template identifier",
                    "query": "The search query to run",
                    "countries": "Comma-separated country codes (e.g., 'it,ch,uk')",
                    "scraper_type": "google_ai, chatgpt, or perplexity",
                    "frequency": "1_per_day, 2_per_day, hourly, weekly, monthly",
                    "is_active": "Whether template is enabled",
                    "priority": "1=high, 2=medium, 3=low",
                    "preferred_layer2": "auto, direct, residential, unlocker, browser",
                },
                "api_endpoints": {
                    "GET /api/templates": "List all templates",
                    "POST /api/templates": "Create new template",
                    "PUT /api/templates/{id}": "Update template",
                    "DELETE /api/templates/{id}": "Delete template",
                },
                "code_reference": "backend/models.py:143-159",
            },
            
            "brands": {
                "title": "Brand Management",
                "description": "Track brand visibility and mentions in AI responses",
                "fields": {
                    "id": "Unique brand identifier (e.g., 'shopify')",
                    "name": "Display name",
                    "type": "'primary' or 'competitor'",
                    "color": "Hex color for UI (e.g., '#06b6d4')",
                    "variations": "Comma-separated search terms",
                },
                "api_endpoints": {
                    "GET /api/brands": "List all brands with visibility metrics",
                    "GET /api/brands/details": "Detailed brand analytics",
                    "POST /api/brands": "Create new brand",
                    "DELETE /api/brands/{id}": "Delete brand",
                },
                "code_reference": "backend/models.py:6-16",
            },
            
            "docker_logs": {
                "title": "Docker Logs",
                "description": "Real-time container log viewer",
                "available_containers": [
                    "aiseo-scraper - Main scraper API service",
                    "aiseo-api - FastAPI backend",
                    "vpn-{country} - VPN containers (it, fr, de, uk, es, nl, ch, se)",
                    "residential-proxy-{country} - GOST proxy sidecars",
                ],
                "api_endpoint": "GET /api/docker/logs/{container}?lines=100",
                "parameters": {
                    "container": "Container name",
                    "lines": "Number of lines (default 100, max 1000)",
                    "since": "Time filter (e.g., '10m', '1h')",
                },
            },
            
            "settings": {
                "title": "Settings",
                "description": "Dashboard configuration and system URLs",
                "options": {
                    "auto_refresh": "Enable/disable 5-second auto-refresh",
                    "verbose_logs": "Show debug information in logs",
                },
                "service_urls": {
                    "backend_api": "http://localhost:8000",
                    "scraper_api": "http://localhost:5000",
                    "sqladmin": "http://localhost:8000/admin",
                    "api_docs": "http://localhost:8000/docs",
                    "admin_dashboard": "http://localhost:9091",
                },
            },
        },
        
        "tips": {
            "quick_start": [
                "1. Check Dashboard for system health",
                "2. Use Quick Scrape for one-time jobs",
                "3. Create Templates for recurring scrapes",
                "4. Monitor Docker Logs for debugging",
            ],
            "debugging": [
                "Check aiseo-scraper logs for scraping errors",
                "Verify VPN status if geolocation fails",
                "Use SQLAdmin to inspect job metadata",
                "HTML snapshots show exactly what was scraped",
            ],
            "cost_optimization": [
                "Use VPN Direct for testing (free)",
                "Residential proxy for rate-limited sites",
                "Scraping Browser for CAPTCHA-protected sites",
                "Batch similar jobs to reduce overhead",
            ],
        },
    }
