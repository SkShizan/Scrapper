# scrapers/__init__.py

from .google import GoogleScraper
from .social import SocialMediaScraper
from .yellow_pages import YellowPagesScraper

# This optional line controls what is imported if someone writes "from scrapers import *"
__all__ = ['GoogleScraper', 'SocialMediaScraper', 'YellowPagesScraper']