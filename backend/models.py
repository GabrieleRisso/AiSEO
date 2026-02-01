from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime


class Brand(SQLModel, table=True):
    """Brand being tracked (e.g., Shopify, WooCommerce)"""
    id: str = Field(primary_key=True)  # e.g., 'shopify'
    name: str
    type: str = "competitor"  # 'primary' or 'competitor'
    color: str
    variations: str | None = None  # Comma-separated search terms (e.g., "Shopify,shopify.com")

    # Relationships
    mentions: list["PromptBrandMention"] = Relationship(back_populates="brand")


class Prompt(SQLModel, table=True):
    """A single scrape/run of a query to Google AI Mode"""
    id: int | None = Field(default=None, primary_key=True)
    query: str  # Not unique - multiple runs of same query allowed
    run_number: int = 1  # Which run/pass this is (1, 2, 3, etc.)
    response_text: str | None = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    brand_mentions: list["PromptBrandMention"] = Relationship(back_populates="prompt")
    sources: list["PromptSource"] = Relationship(back_populates="prompt")


class PromptBrandMention(SQLModel, table=True):
    """Records which brands are mentioned in which prompts"""
    id: int | None = Field(default=None, primary_key=True)
    prompt_id: int = Field(foreign_key="prompt.id")
    brand_id: str = Field(foreign_key="brand.id")
    mentioned: bool = False
    position: int | None = None  # 1=first, 2=second, etc. NULL if not mentioned
    sentiment: str | None = None  # 'positive', 'neutral', 'negative'
    context: str | None = None  # Excerpt where brand is mentioned

    # Relationships
    prompt: Prompt = Relationship(back_populates="brand_mentions")
    brand: Brand = Relationship(back_populates="mentions")


class Source(SQLModel, table=True):
    """A source website cited by Google AI Mode"""
    id: int | None = Field(default=None, primary_key=True)
    domain: str  # e.g., "shopify.com"
    url: str = Field(unique=True)
    title: str | None = None
    description: str | None = None  # Snippet from Google
    published_date: str | None = None  # e.g., "24 Oct 2025"

    # Relationships
    prompt_links: list["PromptSource"] = Relationship(back_populates="source")


class PromptSource(SQLModel, table=True):
    """Links prompts to their cited sources"""
    id: int | None = Field(default=None, primary_key=True)
    prompt_id: int = Field(foreign_key="prompt.id")
    source_id: int = Field(foreign_key="source.id")
    citation_order: int  # Order of appearance in sources list

    # Relationships
    prompt: Prompt = Relationship(back_populates="sources")
    source: Source = Relationship(back_populates="prompt_links")


class ScrapeJob(SQLModel, table=True):
    """Tracks asynchronous scraping jobs"""
    id: int | None = Field(default=None, primary_key=True)
    query: str
    country: str
    scraper_type: str = "google_ai"
    status: str = "pending"  # pending, running, completed, failed, scheduled
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str | None = None
    proxy_used: str | None = None
    profile_data: str | None = None  # JSON string of profile metadata
    config_snapshot: str | None = None # JSON string of request config
    html_snapshot: str | None = None # Full HTML content of the page
    prompt_id: int | None = Field(default=None, foreign_key="prompt.id")
    
    # Scheduling fields
    schedule_type: str = "once" # once, recurring
    frequency: str | None = None # daily, weekly, monthly, 2_per_day, etc.
    next_run_at: datetime | None = None
    is_active: bool = True
    parent_job_id: int | None = Field(default=None, foreign_key="scrapejob.id")
    
    # Performance tracking
    duration_seconds: float | None = None  # Time to complete
    response_size_kb: float | None = None  # Response size in KB
    
    # Cost tracking  
    layer2_mode: str | None = None  # direct, residential, unlocker, browser
    estimated_cost_usd: float | None = None  # Estimated cost for this job
    
    # Origin verification
    origin_ip: str | None = None
    origin_country: str | None = None
    origin_verified: bool = False


class DailyStats(SQLModel, table=True):
    """Daily statistics for quota and monitoring"""
    id: int | None = Field(default=None, primary_key=True)
    date: str = Field(unique=True)  # YYYY-MM-DD format
    
    # Prompt counts
    prompts_scheduled: int = 0
    prompts_completed: int = 0
    prompts_failed: int = 0
    
    # Job counts by scraper type
    jobs_google_ai: int = 0
    jobs_chatgpt: int = 0
    jobs_perplexity: int = 0
    
    # Cost tracking by layer
    cost_vpn_direct: float = 0.0  # Free
    cost_residential: float = 0.0  # ~$8.40/GB
    cost_unlocker: float = 0.0  # ~$3-10/1000 req
    cost_browser: float = 0.0  # ~$0.01-0.03/req
    total_cost_usd: float = 0.0
    
    # Performance
    avg_duration_seconds: float = 0.0
    total_data_kb: float = 0.0
    
    # Quota
    daily_quota: int = 100  # Default daily limit
    quota_remaining: int = 100
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PromptTemplate(SQLModel, table=True):
    """Reusable prompt templates for batch scheduling"""
    id: int | None = Field(default=None, primary_key=True)
    name: str  # Template name
    query: str  # The actual query/prompt
    category: str | None = None  # e.g., "seo", "competitor", "brand"
    countries: str = "it,ch,uk"  # Comma-separated country codes
    scraper_type: str = "google_ai"
    frequency: str = "1_per_day"  # How often to run
    is_active: bool = True
    priority: int = 1  # 1=high, 2=medium, 3=low
    
    # Cost optimization
    preferred_layer2: str = "auto"  # auto, direct, residential, unlocker, browser
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

