# scrapers/yellow_pages.py
from curl_cffi import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import os
from .base_scraper import BaseScraper
from ai_extractor import extract_business_info

class YellowPagesScraper(BaseScraper):
    # Regex for finding emails in text
    EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    # Ignore these generic/junk emails
    JUNK_EMAILS = {
        'dmca', 'privacy', 'accessibility', 'abuse', 'noreply', 
        'webmaster', 'admin', 'help', 'jobs', 'careers', 'media', 
        'press', 'news', 'support'
    }

    def _is_junk_email(self, email):
        """Check if email is a generic/junk address."""
        email_lower = email.lower()
        for junk in self.JUNK_EMAILS:
            if junk in email_lower:
                return True
        # Check for image extensions or common false positives
        if email_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js', '.svg')):
            return True
        return False

    def _decode_cf_email(self, cf_email_link):
        """Decodes Cloudflare's encrypted email string."""
        try:
            # Extract the hash part after the #
            if '#' in cf_email_link:
                encoded_string = cf_email_link.split('#')[1]
            else:
                encoded_string = cf_email_link

            # The first 2 hex chars are the "key"
            r = int(encoded_string[:2], 16)
            email = ''.join([chr(int(encoded_string[i:i+2], 16) ^ r) 
                             for i in range(2, len(encoded_string), 2)])
            return email
        except Exception:
            return None

    def _scrape_yp_internal_profile(self, yp_url):
        """
        Visits the specific YellowPages.com profile page to find hidden emails.
        """
        if not yp_url: return None

        try:
            response = requests.get(yp_url, impersonate="chrome110", timeout=10)
            if response.status_code != 200: return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # 1. Check for Cloudflare Encrypted Links first
            cf_link = soup.select_one('a[href*="/cdn-cgi/l/email-protection"]')
            if cf_link:
                decoded = self._decode_cf_email(cf_link['href'])
                if decoded and not self._is_junk_email(decoded):
                    return decoded

            # 2. Check for standard 'Email Business' button
            email_btn = soup.select_one('a.email-business')
            if email_btn and email_btn.get('href'):
                email = email_btn.get('href').replace('mailto:', '').split('?')[0]
                return email

            # 3. Fallback: Any mailto link
            for link in soup.select('a[href^="mailto:"]'):
                email = link.get('href').replace('mailto:', '').split('?')[0]
                if not self._is_junk_email(email):
                    return email

        except Exception:
            pass
        return None

    def _scrape_external_website(self, url):
        """
        Visits the business's own website to find emails using AI or Regex.
        Returns a DICTIONARY with type and data.
        """
        if not url or "yellowpages.com" in url or url == "N/A": return None

        print(f"   --> Deep Scraping Website: {url}")
        try:
            response = requests.get(url, impersonate="chrome110", timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text(separator=' ', strip=True)

            # ---------------------------------------------------------
            # AI MODE: Gemini Integration
            # ---------------------------------------------------------
            if os.environ.get('GEMINI_API_KEY'):
                ai_data = extract_business_info(page_text, url)
                if ai_data and (ai_data.get('email') or ai_data.get('phone')):
                    return {
                        "type": "ai",
                        "data": ai_data
                    }
            # ---------------------------------------------------------

            # FALLBACK: Standard Logic
            found_email = None

            # 1. Check for Cloudflare Encrypted Links
            cf_links = soup.select('a[href*="/cdn-cgi/l/email-protection"]')
            for link in cf_links:
                decoded = self._decode_cf_email(link['href'])
                if decoded and not self._is_junk_email(decoded):
                    found_email = decoded
                    break

            # 2. Check Home Page for 'mailto:'
            if not found_email:
                for link in soup.select('a[href^="mailto:"]'):
                    email = link.get('href').replace('mailto:', '').split('?')[0]
                    if not self._is_junk_email(email):
                        found_email = email
                        break

            # 3. Check regex in text
            if not found_email:
                text_emails = set(re.findall(self.EMAIL_REGEX, page_text))
                for email in text_emails:
                    if not self._is_junk_email(email):
                        found_email = email
                        break

            if found_email:
                return {"type": "regex", "email": found_email}

        except Exception:
            pass
        return None

    def search(self, query, location, api_key=None, cx=None, page=1):
        """
        Scrapes a SPECIFIC page number and returns leads + metadata.
        """
        results = []
        base_url = "https://www.yellowpages.com/search"
        params = {
            "search_terms": query, 
            "geo_location_terms": location, 
            "page": page
        }

        print(f"--- [YellowPages] Scraping Page {page}... ---")

        try:
            response = requests.get(
                base_url, 
                params=params, 
                impersonate="chrome110", 
                timeout=15
            )

            if response.status_code == 403:
                return {"error": "YP Blocked your IP. Restart router or wait."}

            if response.status_code != 200:
                 return {"error": f"YP Error Code: {response.status_code}"}

            soup = BeautifulSoup(response.content, 'html.parser')
            cards = soup.select('.result')

            # --- PAGINATION ESTIMATION ---
            total_pages_estimate = 1
            pagination = soup.select_one('.pagination')
            if pagination:
                page_links = pagination.select('a')
                page_nums = []
                for link in page_links:
                    txt = link.get_text(strip=True)
                    if txt.isdigit():
                        page_nums.append(int(txt))
                if page_nums:
                    total_pages_estimate = max(page_nums)

            # --- SCRAPE CARDS ---
            for card in cards:
                # Basic Info from Yellow Pages
                name_tag = card.select_one('.business-name')
                name = name_tag.get_text(strip=True) if name_tag else "Unknown"

                phone_tag = card.select_one('.phones')
                phone = phone_tag.get_text(strip=True) if phone_tag else "N/A"

                # URLs
                yp_suffix = name_tag['href'] if name_tag else None
                yp_full_url = urljoin("https://www.yellowpages.com", yp_suffix) if yp_suffix else None

                web_tag = card.select_one('.links a.track-visit-website')
                external_website = web_tag['href'] if web_tag else "N/A"

                email = "N/A"
                source_note = f"YellowPages (Pg {page})"

                # 1. STRATEGY A: Check Internal YP Profile First
                if yp_full_url:
                    email = self._scrape_yp_internal_profile(yp_full_url) or "N/A"

                # 2. STRATEGY B: Check External Website (Deep Scrape / AI)
                if external_website != "N/A" and (email == "N/A" or os.environ.get('GEMINI_API_KEY')):
                    found_data = self._scrape_external_website(external_website)

                    if found_data:
                        if found_data['type'] == 'ai':
                            d = found_data['data']

                            # Prioritize AI Email
                            if d.get('email'): 
                                email = d.get('email')

                            # Enrich Name
                            if d.get('business_name'): 
                                name = d.get('business_name')

                            # Enrich Phone
                            if d.get('phone'):
                                phone = d.get('phone')

                            # Add Industry to Source
                            if d.get('industry'):
                                source_note = f"YP (AI: {d.get('industry')})"

                        elif found_data['type'] == 'regex':
                            if email == "N/A":
                                email = found_data['email']

                # --- FIX: Return Phone as separate key ---
                results.append({
                    "Name": name,
                    "Email": email,
                    "Phone": phone,  # <--- SEPARATE COLUMN
                    "Website": external_website,
                    "Location": location,
                    "Source": source_note
                })

            # RETURN STRUCTURE WITH METADATA
            return {
                "leads": results,
                "meta": {
                    "current_page": int(page),
                    "total_pages_estimate": total_pages_estimate,
                    "has_next": (int(page) < total_pages_estimate) or (len(cards) >= 30)
                }
            }

        except Exception as e:
            print(f"Error: {e}")
            return {"error": str(e)}