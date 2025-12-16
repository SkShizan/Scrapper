# scrapers/google.py
import time
import re
import concurrent.futures
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from curl_cffi import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from .base_scraper import BaseScraper
from ai_extractor import extract_business_info

class GoogleScraper(BaseScraper):
    JUNK_DOMAINS = {
        'example.com', 'sentry.io', 'wixpress.com', 'google.com',
        'schema.org', 'wordpress.org', '.gov', 'facebook.com', 
        'linkedin.com', 'twitter.com', 'instagram.com', 'youtube.com',
        'amazon.com', 'ebay.com', 'yelp.com', 'yellowpages.com'
    }

    # Regex for fallback (when AI is off)
    EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,10}\b"
    PHONE_REGEX = r"(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"

    JUNK_EXTENSIONS = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.gif', '.xml', '.zip', '.css', '.js', '.mp4')

    def _extract_email_regex(self, text):
        """Fallback Regex extraction."""
        if not text: return None
        emails = set(re.findall(self.EMAIL_REGEX, text, re.IGNORECASE))
        valid_emails = []
        for email in emails:
            domain = email.split('@')[-1].lower()
            if domain not in self.JUNK_DOMAINS and not email.lower().endswith(('.png', '.jpg')):
                valid_emails.append(email)
        return valid_emails[0] if valid_emails else None

    def _extract_phone(self, text):
        """Extracts the first valid looking phone number."""
        if not text: return None
        matches = re.findall(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", text)
        if matches:
            return matches[0].strip()
        return None

    def _visit_website(self, url, title):
        """
        Deep scrapes the website using AI or Regex.
        """
        if not url or url.lower().endswith(self.JUNK_EXTENSIONS): return None

        try:
            # Check domain junk filter
            domain = urlparse(url).netloc.lower().replace('www.', '')
            if any(junk in domain for junk in self.JUNK_DOMAINS): return None

            # print(f"   --> Deep Scraping: {url}")
            response = requests.get(
                url, 
                impersonate="chrome110", 
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )

            if response.status_code != 200: return None

            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text(separator=' ', strip=True)

            # ---------------------------------------------------------
            # AI MODE
            # ---------------------------------------------------------
            if os.environ.get('GEMINI_API_KEY'):
                ai_data = extract_business_info(page_text, url)
                if ai_data and (ai_data.get('email') or ai_data.get('phone')):
                    return {
                        "type": "ai",
                        "data": ai_data
                    }

            # ---------------------------------------------------------
            # REGEX FALLBACK
            # ---------------------------------------------------------
            # 1. Check Body Text
            email = self._extract_email_regex(page_text)
            phone = self._extract_phone(page_text)

            # 2. Check Mailto Links
            if not email:
                for link in soup.select('a[href^="mailto:"]'):
                    raw = link.get('href').replace('mailto:', '').split('?')[0]
                    email = self._extract_email_regex(raw)
                    if email: break

            if email or phone:
                return {
                    "type": "regex", 
                    "email": email, 
                    "phone": phone
                }

        except Exception:
            pass
        return None

    def search(self, query, location, api_key=None, cx=None, page=1):
        print(f"--- [GoogleScraper] Official API Search: {query} in {location} ---")

        full_query = f"{query} {location}"
        leads = []
        found_emails = set()
        sites_to_visit = []

        try:
            service = build("customsearch", "v1", developerKey=api_key)

            # Fetch up to 3 pages (30 results) to process
            for p in range(0, 10): 
                start_index = (p * 10) + 1
                print(f"   >>> Fetching Page {p + 1} from Google API...")

                try:
                    result = service.cse().list(
                        q=full_query, cx=cx, num=10, start=start_index
                    ).execute()
                except HttpError as e:
                    print(f"Google API Limit/Error: {e}")
                    break

                if 'items' not in result:
                    break

                for item in result['items']:
                    link = item.get('link')
                    title = item.get('title', 'Unknown')
                    if link:
                        sites_to_visit.append({'link': link, 'title': title})

                time.sleep(1) # Be polite to API

            # --- DEEP SCRAPING PHASE ---
            if sites_to_visit:
                total = len(sites_to_visit)
                # Max 5 workers for AI (Free Tier limit), 15 for Regex
                workers = 5 if os.environ.get('GEMINI_API_KEY') else 15

                print(f"   --> Deep Scraping {total} sites (Workers: {workers})...")

                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    future_to_site = {
                        executor.submit(self._visit_website, s['link'], s['title']): s 
                        for s in sites_to_visit
                    }

                    for future in concurrent.futures.as_completed(future_to_site):
                        site_info = future_to_site[future]
                        try:
                            result = future.result()
                            if result:
                                # Prepare Lead Data
                                if result['type'] == 'ai':
                                    d = result['data']
                                    email = d.get('email')
                                    name = d.get('business_name') or site_info['title']
                                    phone = d.get('phone')
                                    loc = d.get('location') or location
                                    industry = d.get('industry')
                                    source = f"Google (AI: {industry})" if industry else "Google (AI)"
                                else:
                                    email = result.get('email')
                                    name = site_info['title']
                                    phone = result.get('phone')
                                    loc = location
                                    source = "Google (Deep)"

                                if email and email not in found_emails:
                                    found_emails.add(email)
                                    leads.append({
                                        "Name": name,
                                        "Email": email,
                                        "Phone": phone, # <--- SEPARATE FIELD
                                        "Website": site_info['link'],
                                        "Location": loc,
                                        "Source": source
                                    })
                        except Exception:
                            pass

            return leads

        except Exception as e:
            print(f"Google Scraper Critical Error: {e}")
            return {"error": str(e)}