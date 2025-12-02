import time
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .base_scraper import BaseScraper

class GoogleScraper(BaseScraper):
    # Moved constants here to keep them organized
    JUNK_DOMAINS = {
        'example.com', 'sentry.io', 'wixpress.com', 'google.com',
        'schema.org', 'wordpress.org', '.gov'
    }
    EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    def _filter_email(self, email):
        """Helper to check if email is valid."""
        try:
            domain = email.split('@')[-1]
            if domain in self.JUNK_DOMAINS:
                return False
            return True
        except Exception:
            return False

    def search(self, query, location, api_key=None, cx=None):
        print(f"--- [GoogleScraper] Starting Search for: {query} in {location} ---")
        
        # Combine query if location isn't already inside it
        full_query = f"{query} {location}"
        
        leads = []
        found_emails = set()

        try:
            service = build("customsearch", "v1", developerKey=api_key)
            page = 0
            
            # Limiting to 5 pages (50 results) to save credits, adjust as needed
            while page < 10: 
                start_index = (page * 10) + 1
                print(f"Searching Page {page + 1}...")

                result = service.cse().list(
                    q=full_query, cx=cx, num=10, start=start_index
                ).execute()

                if 'items' not in result:
                    break

                for item in result['items']:
                    snippet = item.get('snippet', '')
                    html_snippet = item.get('htmlSnippet', '')
                    full_text = snippet + " " + html_snippet
                    
                    # Extract Emails
                    emails = set(re.findall(self.EMAIL_REGEX, full_text))
                    
                    if emails:
                        title = item.get('title', 'N/A')
                        link = item.get('link', 'N/A')
                        
                        for email in emails:
                            if self._filter_email(email) and email not in found_emails:
                                found_emails.add(email)
                                leads.append({
                                    "Name": title,
                                    "Email": email,
                                    "Website": link,
                                    "Location": location,
                                    "Source": "Google"
                                })
                
                time.sleep(1) # Be polite to the API
                page += 1

            return leads

        except HttpError as e:
            print(f"Google API Error: {e}")
            return {"error": str(e)}
        except Exception as e:
            print(f"Unknown Error: {e}")
            return {"error": str(e)}