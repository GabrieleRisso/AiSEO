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
    """Get monthly visibility data for charts (Nov 2025, Dec 2025, Jan 2026)"""
    brands = session.exec(select(Brand)).all()
    all_prompts = session.exec(select(Prompt)).all()

    # Group prompts by month
    months = {
        "Nov 2025": [],
        "Dec 2025": [],
        "Jan 2026": [],
    }

    for prompt in all_prompts:
        if prompt.scraped_at:
            month_str = prompt.scraped_at.strftime("%Y-%m")
            if month_str == "2025-11":
                months["Nov 2025"].append(prompt)
            elif month_str == "2025-12":
                months["Dec 2025"].append(prompt)
            elif month_str == "2026-01":
                months["Jan 2026"].append(prompt)

    result = []
    for month_name in ["Nov 2025", "Dec 2025", "Jan 2026"]:
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


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
