from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BrandResponse(BaseModel):
    """Brand with computed metrics"""
    id: str
    name: str
    type: str
    color: str
    visibility: float  # % of prompts mentioning this brand
    avgPosition: float  # Average position when mentioned
    trend: str  # 'up', 'down', 'stable'
    sentiment: str  # Most common sentiment


class PromptBrandMentionResponse(BaseModel):
    """Brand mention in a prompt"""
    brandId: str
    brandName: str
    position: int
    mentioned: bool
    sentiment: str


class SourceInPromptResponse(BaseModel):
    """Source as it appears in a prompt"""
    domain: str
    url: str
    title: str | None
    description: str | None
    publishedDate: str | None
    citationOrder: int


class RunResponse(BaseModel):
    """A single run/scrape of a prompt"""
    id: int
    runNumber: int
    scrapedAt: str
    visibility: float
    avgPosition: float
    totalMentions: int
    brands: list[PromptBrandMentionResponse]
    responseText: str | None
    sources: list[SourceInPromptResponse]


class PromptResponse(BaseModel):
    """Prompt with aggregated stats across all runs"""
    id: str
    query: str
    visibility: float  # Average across runs
    avgPosition: float  # Average across runs
    totalMentions: int  # Average across runs
    totalRuns: int
    brands: list[PromptBrandMentionResponse]  # Aggregated from latest run


class PromptDetailResponse(PromptResponse):
    """Detailed prompt with all runs"""
    runs: list[RunResponse]


class SourceResponse(BaseModel):
    """Source with computed metrics"""
    domain: str
    usage: float  # % of prompts citing this source
    avgCitations: float  # Average citation position


class MetricResponse(BaseModel):
    """Dashboard metric"""
    value: float | int
    change: float
    total: int | None = None


class DashboardMetricsResponse(BaseModel):
    """All dashboard KPIs"""
    visibility: MetricResponse
    totalPrompts: MetricResponse
    totalSources: MetricResponse
    avgPosition: MetricResponse


class DailyVisibilityResponse(BaseModel):
    """Daily visibility data for charts"""
    date: str
    shopify: float | None = None
    woocommerce: float | None = None
    bigcommerce: float | None = None
    wix: float | None = None
    squarespace: float | None = None


# Sources Analytics schemas
class DomainBreakdown(BaseModel):
    """Domain with citation stats"""
    domain: str
    citations: int
    percentage: float
    type: str  # 'brand', 'blog', 'community', 'news', 'official', 'other'


class SourceType(BaseModel):
    """Source type breakdown"""
    type: str
    count: int
    percentage: float


class TopSource(BaseModel):
    """Top source with detailed info"""
    id: int
    domain: str
    url: str
    title: str | None
    citations: int
    prompts: list[str]


class SourcesSummary(BaseModel):
    """Summary stats for sources"""
    totalSources: int
    totalDomains: int
    totalCitations: int
    avgCitationsPerSource: float


class SourcesAnalyticsResponse(BaseModel):
    """Full sources analytics response"""
    summary: SourcesSummary
    domainBreakdown: list[DomainBreakdown]
    sourceTypes: list[SourceType]
    topSources: list[TopSource]


# Suggestions schemas
class SuggestionExample(BaseModel):
    """Example source or prompt for a suggestion"""
    type: str  # 'source' or 'prompt'
    domain: str | None = None
    title: str | None = None
    query: str | None = None


class Suggestion(BaseModel):
    """AI SEO improvement suggestion"""
    id: int
    priority: str  # 'high', 'medium', 'low'
    category: str  # 'content', 'community', 'authority', 'technical'
    title: str
    description: str
    stat: str
    statLabel: str
    action: str
    examples: list[SuggestionExample]


class SuggestionsResponse(BaseModel):
    """Suggestions with overall score"""
    score: int
    suggestions: list[Suggestion]


# Brand Management schemas
class BrandCreate(BaseModel):
    """Create a new brand"""
    id: str  # lowercase, no spaces (e.g., "adobe-commerce")
    name: str
    type: str = "competitor"  # 'primary' or 'competitor'
    color: str
    variations: list[str] = []  # Search terms: ["Adobe Commerce", "Magento"]


class BrandPromptDetail(BaseModel):
    """Prompt detail for brand analytics"""
    query: str
    position: int | None
    sentiment: str | None
    scrapedAt: str


class BrandMonthlyVisibility(BaseModel):
    """Monthly visibility data for brand"""
    month: str
    visibility: float


class BrandDetailResponse(BaseModel):
    """Detailed brand analytics"""
    id: str
    name: str
    type: str
    color: str
    variations: list[str]
    visibility: float
    avgPosition: float
    trend: str
    sentiment: str
    totalMentions: int
    totalPrompts: int
    topPrompts: list[BrandPromptDetail]
    visibilityByMonth: list[BrandMonthlyVisibility]


class BrandListResponse(BaseModel):
    """List of all brands with details"""
    brands: list[BrandDetailResponse]
