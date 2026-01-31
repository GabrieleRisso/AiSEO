import os
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, func
from datetime import datetime, timedelta
from collections import Counter
from itertools import groupby
import requests
import json
from pydantic import BaseModel, Field

from database import create_db_and_tables, get_session, engine
from models import Brand, Prompt, PromptBrandMention, Source, PromptSource, ScrapeJob
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
    Backend API for AiSEO platform. Provides endpoints for managing brands, prompts, sources,
    analytics, and scraping jobs.
    
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
    """,
    version="1.0.0",
    contact={
        "name": "AiSEO API Support",
    },
    tags_metadata=[
        {
            "name": "health",
            "description": "Health check endpoints",
        },
        {
            "name": "system",
            "description": "System configuration and VPN server information",
        },
        {
            "name": "brands",
            "description": "Brand management and analytics endpoints",
        },
        {
            "name": "prompts",
            "description": "Prompt and query management endpoints",
        },
        {
            "name": "sources",
            "description": "Source and citation management endpoints",
        },
        {
            "name": "analytics",
            "description": "Analytics, metrics, and reporting endpoints",
        },
        {
            "name": "jobs",
            "description": "Scraping job management endpoints",
        },
    ],
)

# CORS for frontend - read from environment variable
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    seed_brands()


def seed_brands():
    """
    Seed initial brand data if database is empty.
    
    Creates default brands for tracking:
    - Primary brand: Wix
    - Competitors: Shopify, WooCommerce, BigCommerce, Squarespace
    
    Handles race conditions when multiple workers start simultaneously.
    Uses merge() to safely insert/update brands.
    """
    from sqlmodel import Session
    from database import engine

    brands_data = [
        {"id": "wix", "name": "Wix", "type": "primary", "color": "#06b6d4"},
        {"id": "shopify", "name": "Shopify", "type": "competitor", "color": "#f59e0b"},
        {"id": "woocommerce", "name": "WooCommerce", "type": "competitor", "color": "#8b5cf6"},
        {"id": "bigcommerce", "name": "BigCommerce", "type": "competitor", "color": "#ec4899"},
        {"id": "squarespace", "name": "Squarespace", "type": "competitor", "color": "#10b981"},
    ]

    with Session(engine) as session:
        for brand_data in brands_data:
            # Use merge to handle race condition with multiple workers
            # merge() will insert if not exists, or update if exists
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
    """Calculate next run time based on frequency."""
    if not job.next_run_at:
        job.next_run_at = datetime.utcnow()
        
    if job.frequency == "daily":
        job.next_run_at += timedelta(days=1)
    elif job.frequency == "weekly":
        job.next_run_at += timedelta(weeks=1)
    elif job.frequency == "hourly":
        job.next_run_at += timedelta(hours=1)
    else:
        # Default fallback
        job.next_run_at += timedelta(days=1)

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
            "take_screenshot": config.get("take_screenshot", False),
            "headless": config.get("run_in_background", True),
            "use_residential_proxy": config.get("use_residential_proxy", False),
            "use_scraping_browser": config.get("use_scraping_browser", False),
            "human_behavior": config.get("human_behavior", True),
            # Scraping Browser specific settings
            "profile": profile,
            "custom_viewport": config.get("custom_viewport"),
            "scroll_full_page": config.get("scroll_full_page", True),
        }
        
        # Log the full request config
        print(f"\n[Scrape Job {job_id}] Request Config:")
        print(f"  Query: {payload['query']}")
        print(f"  Country: {payload['country']}")
        print(f"  Scraper: {payload['scraper_type']}")
        print(f"  Profile: {payload['profile']}")
        print(f"  Scraping Browser: {payload['use_scraping_browser']}")
        print(f"  Residential Proxy: {payload['use_residential_proxy']}")
        
        # Call scraper service
        # Increased timeout for Bright Data SDK or browser wait
        response = requests.post(
            "http://aiseo-scraper:5000/scrape",
            json=payload,
            timeout=600 
        )
        
        if response.status_code != 200:
            raise Exception(f"Scraper error: {response.text}")
            
        result = response.json()
        
        with Session(engine) as session:
            scrape_job = session.get(ScrapeJob, job_id)
            if scrape_job:
                # Always save HTML if available, regardless of status
                if result.get("html_content"):
                     scrape_job.html_snapshot = result.get("html_content")[:1000000]
                
                # Update metadata
                scrape_job.proxy_used = result.get("metadata", {}).get("proxy_used")
                scrape_job.profile_data = json.dumps(result.get("metadata", {}))
                scrape_job.completed_at = datetime.utcnow()

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
                            scrape_job.error = str(e)
                            scrape_job.completed_at = datetime.utcnow()
                            
                            # Try to save HTML even on failure if returned in exception-like dict or accessible
                            # Since we don't have access to result here if request failed, this is tricky.
                            # But if the scraper service returned a 200 with status="failed", we handled it above.
                            # This block catches exceptions in run_scrape_logic itself (like connection errors).
                            # If scraper returned 200 but failed status, it's handled in the try block logic (raising Exception).
                            # We should extract HTML from that exception message if possible, or result if available?
                            # Actually, we should refactor run_scrape_logic to handle the failed result properly without raising immediately.
                            
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
            resp = requests.get("http://aiseo-scraper:5000/config", timeout=2)
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
        response = requests.get("http://aiseo-scraper:5000/config", timeout=5)
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
    
    # Scheduling
    frequency: str | None = Field(default=None, description="Schedule frequency: daily, weekly, hourly. None for one-time job", example=None)
    start_date: datetime | None = Field(default=None, description="Start date for scheduled jobs (ISO format). Defaults to now if not provided", example=None)
    
    # Debugging
    take_screenshot: bool = Field(default=False, description="Capture screenshot during scraping", example=False)
    run_in_background: bool = Field(default=True, description="Run browser in headless mode. Set false to see browser", example=True)
    use_residential_proxy: bool = Field(default=False, description="Use residential proxy instead of datacenter VPN", example=False)
    use_scraping_browser: bool = Field(default=False, description="Use Bright Data Scraping Browser (cloud browser with CAPTCHA solving)", example=False)
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
def list_jobs(status: str | None = None):
    """
    List all scrape jobs.
    
    Optionally filter by status. Results are ordered by creation time descending.
    """
    with Session(engine) as session:
        query = select(ScrapeJob).order_by(ScrapeJob.created_at.desc())
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
                "next_run_at": job.next_run_at,
                "created_at": job.created_at,
                "scraper_type": job.scraper_type
            }
            for job in jobs
        ]
