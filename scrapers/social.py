# scrapers/social.py
from .base_scraper import BaseScraper
from .google import GoogleScraper
from ddgs import DDGS
import re
import os
from ai_extractor import extract_business_info

class SocialMediaScraper(BaseScraper):
    def __init__(self, platform, backend='google'):
        self.platform = platform
        self.backend = backend

        # We only initialize GoogleScraper because for DDG we will implement 
        # custom logic here to avoid the "Junk Domain" filters of the main DDG scraper.
        if backend == 'google':
            self.scraper = GoogleScraper()
        else:
            self.scraper = None

    def _parse_snippet_with_ai(self, snippet, title, url):
        """
        Uses AI to extract info from the search snippet text.
        """
        try:
            # We reuse the extractor but pass the Snippet as the "Page Text"
            # The AI is smart enough to understand it's a short text.
            data = extract_business_info(f"Title: {title}\nSnippet: {snippet}", url)
            return data
        except Exception:
            return None

    def search(self, query, location, api_key=None, cx=None, page=1, proxy=None):
        # 1. Determine the "Dork" (Site Operator)
        # Note: We do NOT put quotes around the site operator, otherwise search engines treat it as text.
        site_operator = ""
        if self.platform == 'linkedin':
            site_operator = "site:linkedin.com/in/ OR site:linkedin.com/pub/"
        elif self.platform == 'facebook':
            site_operator = "site:facebook.com"
        elif self.platform == 'instagram':
            site_operator = "site:instagram.com"

        # 2. Construct Query
        # Format: (site:A OR site:B) "Keyword" "Location" "email"
        # We add "email" to force results that likely have contact info in the snippet
        dork_query = f'({site_operator}) "{query}" "{location}" "email"'

        print(f"--- [SocialScraper] Search: {dork_query} (Backend: {self.backend}) ---")

        leads = []

        # ---------------------------------------------------------
        # OPTION A: GOOGLE OFFICIAL API
        # ---------------------------------------------------------
        if self.backend == 'google':
            # Delegate to existing Google Scraper
            # Note: GoogleScraper likely returns a list of dicts. 
            # If you want AI on Google results, you would need to modify GoogleScraper too.
            # For now, we assume it returns standard data.
            return self.scraper.search(dork_query, location, api_key, cx, page)

        # ---------------------------------------------------------
        # OPTION B: DUCKDUCKGO (Free & AI Enhanced)
        # ---------------------------------------------------------
        else:
            try:
                # Use DDGS directly to avoid the 'Junk Domain' filter in our main DuckDuckGoScraper
                with DDGS() as ddgs:
                    # Fetch results (approx 20 per request)
                    results = list(ddgs.text(
                        dork_query, 
                        region='wt-wt', 
                        safesearch='off', 
                        timelimit=None,
                        max_results=25 
                    ))

                print(f"   --> Found {len(results)} raw social profiles.")

                for res in results:
                    title = res.get('title', 'Unknown')
                    link = res.get('href', 'N/A')
                    snippet = res.get('body', '')

                    # Skip if no link
                    if link == 'N/A': continue

                    email = "N/A"
                    name = title
                    source_label = f"Social ({self.platform})"

                    # --- 1. AI EXTRACTION (Snippet) ---
                    if os.environ.get('GEMINI_API_KEY'):
                        # AI reads the snippet to find Name, Job Title, Email
                        ai_data = self._parse_snippet_with_ai(snippet, title, link)

                        if ai_data:
                            if ai_data.get('email'): 
                                email = ai_data.get('email')

                            if ai_data.get('business_name'): 
                                # For social, business_name often equals the Person's Name or Page Title
                                name = ai_data.get('business_name')

                            # Add Job/Industry to source
                            if ai_data.get('industry'):
                                source_label = f"{self.platform} (AI: {ai_data.get('industry')})"

                    # --- 2. FALLBACK: REGEX EXTRACTION ---
                    # If AI didn't find email (or key missing), try Regex on the snippet
                    if email == "N/A":
                        # Simple regex for finding emails in the snippet text
                        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}", snippet)
                        if emails:
                            email = emails[0] # Take the first one found

                    # Add to list if we found an email or if it's a valid profile 
                    # (You can choose to filter only those with emails)
                    if email != "N/A": 
                        leads.append({
                            "Name": name,
                            "Email": email,
                            "Website": link,
                            "Location": location, # Social profiles don't always have clear location in snippet
                            "Source": source_label
                        })

            except Exception as e:
                print(f"Social Scraper Error: {e}")
                return {"error": str(e)}

            return leads