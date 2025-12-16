# scrapers/duckduckgo.py
from ddgs import DDGS
from .base_scraper import BaseScraper
from curl_cffi import requests
from bs4 import BeautifulSoup
import re
import time
import concurrent.futures
from urllib.parse import urlparse, urljoin
import os
from ai_extractor import extract_business_info

class DuckDuckGoScraper(BaseScraper):
    # Improved Regex: Limits TLD length to 6 chars
    EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,10}\b"

    # Regex for Phone (Matches common US/International formats)
    PHONE_REGEX = r"(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"

    JUNK_DOMAINS = {
        'duckduckgo.com', 'google.com', 'microsoft.com', 'yahoo.com', 
        'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
        'youtube.com', 'w3.org', 'yandex.com', 'wix.com', 'sentry.io',
        'outlook.office.com', 'accounts.google.com', 'signin.aws.amazon.com',
        'cloudflare.com', 'github.com', 'wordpress.org', 'gravatar.com',
        'healthjobsnationwide.com', 'registertovote.ca.gov', 'caring.com',
        'yelp.com', 'yellowpages.com', 'superpages.com', 'mapquest.com',
        'ussearch.com', 'webfecto.com', 'cybo.com', 'findbusinessaddress.com'
    }

    JUNK_EXTENSIONS = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.gif', '.xml', '.zip', '.css', '.js', '.mp4')
    GARBAGE_SUFFIXES = ['None', 'Website', '.Website', 'Contact', 'Email', 'null', 'undefined', 'Tel', 'Phone', 'Fax', 'Hours', 'Home', 'Services', 'About', 'Menu']

    def _extract_email(self, text):
        """Extracts and cleans the first valid email found in text."""
        if not text: return None
        emails = re.findall(self.EMAIL_REGEX, text, re.IGNORECASE)

        for email in emails:
            email = email.strip().lstrip('/.:').rstrip('.,;:|')
            for suffix in self.GARBAGE_SUFFIXES:
                if email.endswith(suffix):
                    email = email[:-len(suffix)]
                match = re.search(r'(\.[a-z]+)([A-Z].*)', email)
                if match:
                    email = email.replace(match.group(2), "")

            email = email.rstrip('.,;:|')
            if '@' not in email: continue

            domain = email.split('@')[-1].lower()
            if domain not in self.JUNK_DOMAINS:
                if not email.lower().endswith(('.png', '.jpg', '.gif', '.svg', '.webp')):
                    return email
        return None

    def _extract_phone(self, text):
        """Extracts the first valid looking phone number via Regex."""
        if not text: return None
        # Use a simpler regex to grab the most common format (xxx-xxx-xxxx)
        matches = re.findall(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", text)
        if matches:
            return matches[0].strip()
        return None

    def _get_page_content(self, url):
        try:
            response = requests.get(
                url, 
                impersonate="chrome110", 
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
            if response.status_code == 200:
                return BeautifulSoup(response.content, 'html.parser')
        except Exception:
            pass
        return None

    def _find_contact_link(self, soup, base_url):
        if not soup: return None
        keywords = ['contact', 'about', 'team', 'connect', 'support', 'staff']
        for a in soup.select('a[href]'):
            href = a['href']
            text = a.get_text().lower()
            if href.startswith(('mailto:', 'tel:', 'javascript:', '#')): continue
            if any(k in text or k in href.lower() for k in keywords):
                full_url = urljoin(base_url, href)
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    return full_url
        return None

    def _get_best_email(self, email_list, website_domain):
        if not email_list: return None
        clean_domain = website_domain.lower()
        if clean_domain.startswith('www.'): 
            clean_domain = clean_domain[4:]

        for email in email_list:
            if clean_domain in email.lower():
                return email
        for email in email_list:
            if email.lower().startswith(('info', 'contact', 'admin', 'support', 'hello', 'office')):
                return email
        return list(email_list)[0]

    def _visit_website(self, url):
        """Visits website and uses AI (Gemini) or Regex to extract data."""
        if not url or url.lower().endswith(self.JUNK_EXTENSIONS): return None
        try:
            domain = urlparse(url).netloc
            if any(junk in domain for junk in self.JUNK_DOMAINS): return None

            soup = self._get_page_content(url)
            if not soup: return None

            page_text = soup.get_text(separator=' ', strip=True)

            # ---------------------------------------------------------
            # AI MODE: Gemini Integration
            # ---------------------------------------------------------
            if os.environ.get('GEMINI_API_KEY'):
                ai_data = extract_business_info(page_text, url)
                if ai_data and (ai_data.get('email') or ai_data.get('phone')):
                    return {"type": "ai", "data": ai_data}
            # ---------------------------------------------------------

            # FALLBACK: Standard Regex Mode
            found_candidates = set()
            found_phone = self._extract_phone(page_text)

            for link in soup.select('a[href^="mailto:"]'):
                raw = link.get('href').replace('mailto:', '').split('?')[0]
                cleaned = self._extract_email(raw)
                if cleaned: found_candidates.add(cleaned)

            text_email = self._extract_email(page_text)
            if text_email: found_candidates.add(text_email)

            contact_url = self._find_contact_link(soup, url)
            if contact_url:
                soup_contact = self._get_page_content(contact_url)
                if soup_contact:
                    # Try to find phone on contact page if not found on home
                    if not found_phone:
                        found_phone = self._extract_phone(soup_contact.get_text(separator=' '))

                    for link in soup_contact.select('a[href^="mailto:"]'):
                        raw = link.get('href').replace('mailto:', '').split('?')[0]
                        cleaned = self._extract_email(raw)
                        if cleaned: found_candidates.add(cleaned)

                    page_text_sub = soup_contact.get_text(separator=' ')
                    text_email_sub = self._extract_email(page_text_sub)
                    if text_email_sub: found_candidates.add(text_email_sub)

            best_email = self._get_best_email(found_candidates, domain)

            if best_email:
                return {
                    "type": "regex", 
                    "data": {
                        "email": best_email,
                        "phone": found_phone
                    }
                }

        except Exception:
            return None
        return None

    def search(self, query, location, api_key=None, cx=None, page=1):
        print(f"--- [DuckDuckGo] Ultimate Search Initiated ---")

        leads = []
        found_emails = set()
        seen_urls = set()
        raw_results = []

        base_query = f"{query} {location}"

        # We can add more specific terms to find contact pages
        permutations = [
            f"{base_query} email",
            f"{base_query} \"contact us\"",
            f"{base_query} \"@gmail.com\"",
            f"{base_query} \"info@\""
        ]

        backends = ['api', 'html']

        for q in permutations:
            print(f"   >>> Searching: {q}")
            for backend in backends:
                try:
                    with DDGS() as ddgs:
                        results = list(ddgs.text(
                            q, 
                            region='wt-wt', 
                            safesearch='off', 
                            timelimit=None, 
                            backend=backend,
                            max_results=None
                        ))

                    if results:
                        for res in results:
                            link = res.get('href', 'N/A')
                            if link != 'N/A' and link not in seen_urls:
                                seen_urls.add(link)
                                raw_results.append(res)
                    time.sleep(1)
                except Exception:
                    pass

        print(f"   --> Total Unique Websites Found: {len(raw_results)}")

        sites_to_visit = []
        for res in raw_results:
            title = res.get('title', 'Unknown')
            link = res.get('href', 'N/A')
            sites_to_visit.append({"link": link, "title": title})

        if sites_to_visit:
            total_sites = len(sites_to_visit)

            # --- IMPORTANT: THROTTLING FOR FREE AI ---
            # Gemini Free Tier allows 15 requests per minute.
            # We set max_workers=4 so we don't hit the rate limit instantly.
            workers = 4 if os.environ.get('GEMINI_API_KEY') else 20

            print(f"   --> Deep Scraping {total_sites} sites (Workers: {workers})...")

            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_site = {
                    executor.submit(self._visit_website, site['link']): site 
                    for site in sites_to_visit
                }

                completed_count = 0
                for future in concurrent.futures.as_completed(future_to_site):
                    site = future_to_site[future]
                    completed_count += 1

                    if completed_count % 5 == 0:
                        print(f"      [{completed_count}/{total_sites}] Scanned {site['link'][:40]}...")

                    try:
                        result = future.result()
                        if result:
                            data = result['data']
                            email = data.get('email')

                            if result['type'] == 'ai':
                                name = data.get('business_name') or site['title']
                                phone = data.get('phone')
                                address = data.get('location') or location
                                industry = data.get('industry')
                                source_label = f"DuckDuckGo (AI: {industry})" if industry else "DuckDuckGo (AI)"
                            else:
                                name = site['title']
                                phone = data.get('phone') # Get phone from regex
                                address = location
                                source_label = "DuckDuckGo (Deep)"

                            # We NO LONGER merge Phone into Location
                            # loc_string = f"{address} | Ph: {phone}" (DELETED)

                            if email and email not in found_emails:
                                found_emails.add(email)
                                leads.append({
                                    "Name": name,
                                    "Email": email,
                                    "Phone": phone, # <--- SEPARATE FIELD
                                    "Website": site['link'],
                                    "Location": address,
                                    "Source": source_label
                                })
                    except Exception:
                        pass

        print(f"   --> Finished! Total Extracted: {len(leads)} leads.")
        return leads