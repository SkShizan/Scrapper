from .base_scraper import BaseScraper
from .google import GoogleScraper

class SocialMediaScraper(BaseScraper):
    def __init__(self, platform):
        self.platform = platform
        self.google_scraper = GoogleScraper() # Composition: We use the existing tool!

    def search(self, query, location, api_key=None, cx=None):
        # 1. Determine the "Dork" (search operator)
        site_operator = ""
        if self.platform == 'linkedin':
            # Target profiles (in) or public pages (pub)
            site_operator = "site:linkedin.com/in/ OR site:linkedin.com/pub/"
        elif self.platform == 'facebook':
            site_operator = "site:facebook.com"
        elif self.platform == 'instagram':
            site_operator = "site:instagram.com"
        
        # 2. Construct the X-Ray Query
        # We look for the site + user query + location + email keywords
        dork_query = f'{site_operator} "{query}" ("@gmail.com" OR "@yahoo.com" OR "contact")'
        
        print(f"--- [SocialScraper] X-Ray Search for {self.platform} ---")
        
        # 3. Delegate the hard work to GoogleScraper
        # Note: We pass 'dork_query' as the query and 'location' just for tagging the result
        return self.google_scraper.search(dork_query, location, api_key, cx)