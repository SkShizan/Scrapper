# scrapers/duckduckgo.py
from ddgs import DDGS
from .base_scraper import BaseScraper
from curl_cffi import requests
from bs4 import BeautifulSoup
import re
import time
import concurrent.futures
from urllib.parse import urlparse, urljoin

class DuckDuckGoScraper(BaseScraper):
    # Improved Regex: Limits TLD length to 6 chars (e.g., .com, .museum) to stop "comHOMESERVICES"
    # Also stops capturing if it hits an uppercase letter after the dot (e.g. .comTel -> .com)
    EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,10}\b"

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

        # Regex findall
        emails = re.findall(self.EMAIL_REGEX, text, re.IGNORECASE)

        for email in emails:
            # 1. Clean whitespace and path characters
            email = email.strip()
            email = email.lstrip('/.:') 
            email = email.rstrip('.,;:|')

            # 2. Remove known attached garbage words
            # This handles cases where regex might have grabbed a bit too much
            for suffix in self.GARBAGE_SUFFIXES:
                if email.endswith(suffix):
                    email = email[:-len(suffix)]
                # Check for Uppercase suffix sticking to lowercase TLD (e.g. .comTel)
                # If we have .comTel, split at the capital T
                match = re.search(r'(\.[a-z]+)([A-Z].*)', email)
                if match:
                    email = email.replace(match.group(2), "")

            # 3. Final clean
            email = email.rstrip('.,;:|')

            if '@' not in email: continue

            domain = email.split('@')[-1].lower()
            if domain not in self.JUNK_DOMAINS:
                if not email.lower().endswith(('.png', '.jpg', '.gif', '.svg', '.webp')):
                    return email
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
        if not url or url.lower().endswith(self.JUNK_EXTENSIONS): return None
        try:
            domain = urlparse(url).netloc
            if any(junk in domain for junk in self.JUNK_DOMAINS): return None

            found_candidates = set()

            soup = self._get_page_content(url)
            if not soup: return None

            # --- FIX: Use separator=' ' to prevent text merging ---
            page_text = soup.get_text(separator=' ')

            # Scrape Links
            for link in soup.select('a[href^="mailto:"]'):
                raw = link.get('href').replace('mailto:', '').split('?')[0]
                cleaned = self._extract_email(raw)
                if cleaned: found_candidates.add(cleaned)

            # Scrape Text (using the separated text)
            text_email = self._extract_email(page_text)
            if text_email: found_candidates.add(text_email)

            # Level 2: Contact Page
            contact_url = self._find_contact_link(soup, url)
            if contact_url:
                soup_contact = self._get_page_content(contact_url)
                if soup_contact:
                    # Scrape Links
                    for link in soup_contact.select('a[href^="mailto:"]'):
                        raw = link.get('href').replace('mailto:', '').split('?')[0]
                        cleaned = self._extract_email(raw)
                        if cleaned: found_candidates.add(cleaned)

                    # Scrape Text (using separator)
                    page_text_sub = soup_contact.get_text(separator=' ')
                    text_email_sub = self._extract_email(page_text_sub)
                    if text_email_sub: found_candidates.add(text_email_sub)

            return self._get_best_email(found_candidates, domain)

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
                        new_count = 0
                        for res in results:
                            link = res.get('href', 'N/A')
                            if link != 'N/A' and link not in seen_urls:
                                seen_urls.add(link)
                                raw_results.append(res)
                                new_count += 1
                    time.sleep(1)
                except Exception:
                    pass

        print(f"   --> Total Unique Websites Found: {len(raw_results)}")

        sites_to_visit = []
        for res in raw_results:
            title = res.get('title', 'Unknown')
            link = res.get('href', 'N/A')
            # Note: We rely on Deep Scraping for clean emails, bypassing the snippet check
            # because snippets often contain the same "merged text" issues.
            sites_to_visit.append({"link": link, "title": title})

        if sites_to_visit:
            total_sites = len(sites_to_visit)
            print(f"   --> Deep Scraping {total_sites} websites (Smart Cleaning)...")

            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                future_to_site = {
                    executor.submit(self._visit_website, site['link']): site 
                    for site in sites_to_visit
                }

                completed_count = 0
                for future in concurrent.futures.as_completed(future_to_site):
                    site = future_to_site[future]
                    completed_count += 1

                    if completed_count % 10 == 0:
                        print(f"      [{completed_count}/{total_sites}] Scanned {site['link'][:40]}...")

                    try:
                        email = future.result()
                        if email and email not in found_emails:
                            found_emails.add(email)
                            leads.append({
                                "Name": site['title'],
                                "Email": email,
                                "Website": site['link'],
                                "Location": location,
                                "Source": "DuckDuckGo (Deep)"
                            })
                    except Exception:
                        pass

        print(f"   --> Finished! Total Extracted: {len(leads)} leads.")
        return leads