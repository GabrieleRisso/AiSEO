"""
SQLAdmin configuration for AiSEO database viewer.

Provides a web-based UI to browse all database tables including:
- ScrapeJobs (with HTML snapshot preview)
- Prompts (with response text)
- Brands and mentions
- Sources and citations
"""

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import Response
import os

from models import Brand, Prompt, PromptBrandMention, Source, PromptSource, ScrapeJob


# Optional basic auth (set ADMIN_USERNAME and ADMIN_PASSWORD env vars to enable)
class OptionalAuthBackend(AuthenticationBackend):
    """Simple optional authentication for admin panel."""
    
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        
        expected_username = os.getenv("ADMIN_USERNAME")
        expected_password = os.getenv("ADMIN_PASSWORD")
        
        if expected_username and expected_password:
            if username == expected_username and password == expected_password:
                request.session.update({"authenticated": True})
                return True
            return False
        # No auth configured - allow access
        request.session.update({"authenticated": True})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        # If no auth configured, allow all access
        if not os.getenv("ADMIN_USERNAME"):
            return True
        return request.session.get("authenticated", False)


# ============================================
# Model Views
# ============================================

class ScrapeJobAdmin(ModelView, model=ScrapeJob):
    """Admin view for scrape jobs - the main table for viewing scraped data."""
    
    name = "Scrape Job"
    name_plural = "Scrape Jobs"
    icon = "fa-solid fa-spider"
    
    # List page configuration - use string names for columns
    column_list = [
        "id",
        "query",
        "country",
        "scraper_type",
        "status",
        "created_at",
        "completed_at",
        "prompt_id",
    ]
    
    column_searchable_list = ["query", "country", "error"]
    column_sortable_list = ["id", "query", "status", "created_at", "completed_at"]
    column_default_sort = [("id", True)]  # Newest first
    
    # Detail page - show all fields
    column_details_list = [
        "id",
        "query",
        "country",
        "scraper_type",
        "status",
        "created_at",
        "completed_at",
        "error",
        "proxy_used",
        "profile_data",
        "config_snapshot",
        "html_snapshot",
        "prompt_id",
        "schedule_type",
        "frequency",
        "next_run_at",
        "is_active",
        "parent_job_id",
    ]
    
    # Format long text fields
    column_formatters = {
        "html_snapshot": lambda m, a: f"[HTML: {len(m.html_snapshot or '')} chars]" if m.html_snapshot else None,
        "config_snapshot": lambda m, a: f"[JSON: {len(m.config_snapshot or '')} chars]" if m.config_snapshot else None,
        "profile_data": lambda m, a: f"[JSON: {len(m.profile_data or '')} chars]" if m.profile_data else None,
    }
    
    # Page size
    page_size = 25
    page_size_options = [10, 25, 50, 100]
    
    # Allow export
    can_export = True
    export_types = ["csv", "json"]


class PromptAdmin(ModelView, model=Prompt):
    """Admin view for prompts/scrape results."""
    
    name = "Prompt"
    name_plural = "Prompts"
    icon = "fa-solid fa-comment"
    
    column_list = ["id", "query", "run_number", "scraped_at"]
    
    column_searchable_list = ["query", "response_text"]
    column_sortable_list = ["id", "query", "run_number", "scraped_at"]
    column_default_sort = [("id", True)]
    
    column_details_list = ["id", "query", "run_number", "response_text", "scraped_at"]
    
    column_formatters = {
        "response_text": lambda m, a: f"{(m.response_text or '')[:100]}..." if m.response_text and len(m.response_text) > 100 else m.response_text,
    }
    
    page_size = 25
    can_export = True


class BrandAdmin(ModelView, model=Brand):
    """Admin view for tracked brands."""
    
    name = "Brand"
    name_plural = "Brands"
    icon = "fa-solid fa-tag"
    
    column_list = ["id", "name", "type", "color", "variations"]
    column_searchable_list = ["id", "name", "variations"]
    column_sortable_list = ["id", "name", "type"]
    
    page_size = 25
    can_export = True


class PromptBrandMentionAdmin(ModelView, model=PromptBrandMention):
    """Admin view for brand mentions in prompts."""
    
    name = "Brand Mention"
    name_plural = "Brand Mentions"
    icon = "fa-solid fa-at"
    
    column_list = ["id", "prompt_id", "brand_id", "mentioned", "position", "sentiment"]
    
    column_searchable_list = ["context"]
    column_sortable_list = ["id", "prompt_id", "brand_id", "position"]
    column_default_sort = [("id", True)]
    
    column_formatters = {
        "context": lambda m, a: f"{(m.context or '')[:80]}..." if m.context and len(m.context) > 80 else m.context,
    }
    
    page_size = 25
    can_export = True


class SourceAdmin(ModelView, model=Source):
    """Admin view for citation sources."""
    
    name = "Source"
    name_plural = "Sources"
    icon = "fa-solid fa-link"
    
    column_list = ["id", "domain", "url", "title", "published_date"]
    
    column_searchable_list = ["domain", "url", "title", "description"]
    column_sortable_list = ["id", "domain", "title"]
    column_default_sort = [("id", True)]
    
    column_formatters = {
        "url": lambda m, a: f"{m.url[:60]}..." if len(m.url) > 60 else m.url,
        "description": lambda m, a: f"{(m.description or '')[:80]}..." if m.description and len(m.description) > 80 else m.description,
    }
    
    page_size = 25
    can_export = True


class PromptSourceAdmin(ModelView, model=PromptSource):
    """Admin view for prompt-source associations."""
    
    name = "Prompt Source"
    name_plural = "Prompt Sources"
    icon = "fa-solid fa-link"
    
    column_list = ["id", "prompt_id", "source_id", "citation_order"]
    
    column_sortable_list = ["id", "prompt_id", "source_id", "citation_order"]
    column_default_sort = [("id", True)]
    
    page_size = 25
    can_export = True


def setup_admin(app, engine):
    """
    Initialize SQLAdmin and register all model views.
    
    Args:
        app: FastAPI application instance
        engine: SQLAlchemy engine
        
    Returns:
        Admin instance
    """
    # Create admin with optional authentication
    authentication_backend = OptionalAuthBackend(secret_key=os.getenv("SECRET_KEY", "change-me-in-production"))
    
    admin = Admin(
        app,
        engine,
        title="AiSEO Database Viewer",
        authentication_backend=authentication_backend,
        base_url="/admin",
    )
    
    # Register all model views
    admin.add_view(ScrapeJobAdmin)
    admin.add_view(PromptAdmin)
    admin.add_view(BrandAdmin)
    admin.add_view(PromptBrandMentionAdmin)
    admin.add_view(SourceAdmin)
    admin.add_view(PromptSourceAdmin)
    
    return admin
