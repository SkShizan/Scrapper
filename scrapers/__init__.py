# scrapers/__init__.py
from .google import GoogleScraper
from .social import SocialMediaScraper
from .yellow_pages import YellowPagesScraper
from .duckduckgo import DuckDuckGoScraper

__all__ = ['GoogleScraper', 'SocialMediaScraper', 'YellowPagesScraper', 'DuckDuckGoScraper']