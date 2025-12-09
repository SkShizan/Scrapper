from .base_scraper import BaseScraper
from .google import GoogleScraper
from .duckduckgo import DuckDuckGoScraper

class SocialMediaScraper(BaseScraper):
    def __init__(self, platform, backend='google'):
        self.platform = platform
        self.backend = backend

        # Initialize the appropriate backend
        if backend == 'ddg':
            self.scraper = DuckDuckGoScraper()
        else:
            self.scraper = GoogleScraper()

    def search(self, query, location, api_key=None, cx=None):
        # 1. Determine the "Dork"
        site_operator = ""
        if self.platform == 'linkedin':
            site_operator = "site:linkedin.com/in/ OR site:linkedin.com/pub/"
        elif self.platform == 'facebook':
            site_operator = "site:facebook.com"
        elif self.platform == 'instagram':
            site_operator = "site:instagram.com"

        # 2. Construct Query
        dork_query = f'"{site_operator}" "{query}" "email"'

        print(f"--- [SocialScraper] using {self.backend} for {self.platform} ---")

        # 3. Delegate
        return self.scraper.search(dork_query, location, api_key, cx)