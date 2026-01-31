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
    status: str = "pending"  # pending, running, completed, failed
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
    frequency: str | None = None # daily, weekly, monthly
    next_run_at: datetime | None = None
    is_active: bool = True
    parent_job_id: int | None = Field(default=None, foreign_key="scrapejob.id")

