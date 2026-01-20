from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, func
from datetime import datetime, timedelta
from collections import Counter
from itertools import groupby

from .database import create_db_and_tables, get_session
from .models import Brand, Prompt, PromptBrandMention, Source, PromptSource
from .schemas import (
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

app = FastAPI(title="AiSEO API", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    seed_brands()


def seed_brands():
    """Seed initial brand data if not exists"""
    from sqlmodel import Session
    from .database import engine

    brands_data = [
        {"id": "wix", "name": "Wix", "type": "primary", "color": "#06b6d4"},
        {"id": "shopify", "name": "Shopify", "type": "competitor", "color": "#f59e0b"},
        {"id": "woocommerce", "name": "WooCommerce", "type": "competitor", "color": "#8b5cf6"},
        {"id": "bigcommerce", "name": "BigCommerce", "type": "competitor", "color": "#ec4899"},
        {"id": "squarespace", "name": "Squarespace", "type": "competitor", "color": "#10b981"},
    ]

    with Session(engine) as session:
        for brand_data in brands_data:
            existing = session.get(Brand, brand_data["id"])
            if not existing:
                session.add(Brand(**brand_data))
        session.commit()


def get_run_data(session: Session, prompt: Prompt, brands: list[Brand]) -> RunResponse:
    """Build run response for a single prompt/run"""
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

    # Calculate visibility based on Wix's position (primary brand)
    wix_mention = next((b for b in brand_responses if b.brandId == "wix"), None)
    if wix_mention and wix_mention.mentioned and wix_mention.position > 0:
        # Position 1 = 100%, Position 2 = 80%, Position 3 = 60%, etc.
        visibility = max(0, 100 - (wix_mention.position - 1) * 20)
    else:
        visibility = 0  # Not mentioned

    # Use Wix's position (primary brand), not average of all brands
    avg_position = wix_mention.position if wix_mention and wix_mention.mentioned else 0

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


@app.get("/api/brands", response_model=list[BrandResponse])
def get_brands(session: Session = Depends(get_session)):
    """Get all brands with computed metrics (January 2026 only, trend based on Jan vs Dec)"""
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


@app.get("/api/brands/details", response_model=BrandListResponse)
def get_brands_details(session: Session = Depends(get_session)):
    """Get detailed brand analytics for brand management page"""
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


@app.post("/api/brands", response_model=BrandDetailResponse)
def create_brand(brand_data: BrandCreate, session: Session = Depends(get_session)):
    """Create a new brand and sync mentions from existing prompts"""
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


@app.delete("/api/brands/{brand_id}")
def delete_brand(brand_id: str, session: Session = Depends(get_session)):
    """Delete a brand and all its mentions"""
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


@app.get("/api/prompts", response_model=list[PromptResponse])
def get_prompts(session: Session = Depends(get_session)):
    """Get all unique queries with aggregated stats across runs"""
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


@app.get("/api/prompts/{query_id}", response_model=PromptDetailResponse)
def get_prompt_detail(query_id: str, session: Session = Depends(get_session)):
    """Get detailed prompt info with all runs"""
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


@app.get("/api/sources", response_model=list[SourceResponse])
def get_sources(session: Session = Depends(get_session)):
    """Get all sources with usage metrics"""
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


@app.get("/api/metrics", response_model=DashboardMetricsResponse)
def get_metrics(session: Session = Depends(get_session)):
    """Get dashboard KPIs with month-over-month changes (Jan vs Dec)"""
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


@app.get("/api/visibility", response_model=list[DailyVisibilityResponse])
def get_visibility_data(session: Session = Depends(get_session)):
    """Get monthly visibility data for charts (Sep 2025 - Jan 2026)"""
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


@app.get("/api/sources/analytics", response_model=SourcesAnalyticsResponse)
def get_sources_analytics(session: Session = Depends(get_session)):
    """Get detailed analytics for citation sources"""
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


@app.get("/api/suggestions", response_model=SuggestionsResponse)
def get_suggestions(session: Session = Depends(get_session)):
    """Get AI SEO improvement suggestions based on source data analysis"""
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


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
