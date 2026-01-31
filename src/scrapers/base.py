from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.lib.antidetect import AntiDetectLayer

class BaseScraper(ABC):
    """Abstract base class for all scrapers."""
    
    def __init__(self, headless: bool = True, proxy: Optional[str] = None, antidetect: Optional['AntiDetectLayer'] = None):
        self.headless = headless
        self.proxy = proxy
        self.antidetect = antidetect

    @abstractmethod
    async def scrape(self, query: str, take_screenshot: bool = False) -> Dict[str, Any]:
        """
        Execute the scrape.
        Must return a dictionary with:
        - status: str
        - data: list
        - response_text: str
        - html_content: str (optional)
        - error: str (optional)
        - metadata: dict
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
