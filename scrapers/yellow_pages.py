# scrapers/yellow_pages.py
from curl_cffi import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from .base_scraper import BaseScraper

class YellowPagesScraper(BaseScraper):
    EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    
    JUNK_EMAILS = {
        'dmca', 'privacy', 'accessibility', 'abuse', 'noreply', 
        'webmaster', 'admin', 'help', 'jobs', 'careers'
    }

    def _is_junk_email(self, email):
        """Filter out obvious bad emails."""
        email_lower = email.lower()
        for junk in self.JUNK_EMAILS:
            if junk in email_lower: return True
        if email_lower.endswith(('.png', '.jpg', '.js', '.css', '.svg')): return True
        return False

    def _decode_cf_email(self, cf_email_link):
        """
        Decodes Cloudflare's encrypted email string.
        Input: "/cdn-cgi/l/email-protection#690a0607..."
        Output: "contact@example.com"
        """
        try:
            # Extract the hash part after the #
            if '#' in cf_email_link:
                encoded_string = cf_email_link.split('#')[1]
            else:
                # Sometimes it's just the raw hex string
                encoded_string = cf_email_link

            # The first 2 hex chars are the "key"
            r = int(encoded_string[:2], 16)
            email = ''.join([chr(int(encoded_string[i:i+2], 16) ^ r) 
                             for i in range(2, len(encoded_string), 2)])
            return email
        except Exception:
            return None

    def _scrape_yp_internal_profile(self, yp_url):
        if not yp_url: return None
        
        print(f"   --> Checking YP Profile: {yp_url}")
        try:
            response = requests.get(yp_url, impersonate="chrome110", timeout=10)
            if response.status_code != 200: return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Check for Cloudflare Encrypted Links first
            # They look like: <a href="/cdn-cgi/l/email-protection#...">
            cf_link = soup.select_one('a[href*="/cdn-cgi/l/email-protection"]')
            if cf_link:
                decoded = self._decode_cf_email(cf_link['href'])
                if decoded and not self._is_junk_email(decoded):
                    print(f"       [Success] Decoded Cloudflare Email: {decoded}")
                    return decoded

            # 2. Check for standard 'Email Business' button
            email_btn = soup.select_one('a.email-business')
            if email_btn and email_btn.get('href'):
                email = email_btn.get('href').replace('mailto:', '').split('?')[0]
                print(f"       [Success] Found Hidden YP Email: {email}")
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
        if not url or "yellowpages.com" in url or url == "N/A": return None

        print(f"   --> Fallback: Deep Scraping Website {url}")
        try:
            response = requests.get(url, impersonate="chrome110", timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Check for Cloudflare Encrypted Links on external site
            cf_links = soup.select('a[href*="/cdn-cgi/l/email-protection"]')
            for link in cf_links:
                decoded = self._decode_cf_email(link['href'])
                if decoded and not self._is_junk_email(decoded):
                    print(f"       [Success] Decoded External CF Email: {decoded}")
                    return decoded

            # 2. Check Home Page for 'mailto:'
            for link in soup.select('a[href^="mailto:"]'):
                email = link.get('href').replace('mailto:', '').split('?')[0]
                if not self._is_junk_email(email):
                    return email
            
            # 3. Check regex in text
            text_emails = set(re.findall(self.EMAIL_REGEX, soup.get_text()))
            for email in text_emails:
                if not self._is_junk_email(email):
                    return email

        except Exception:
            pass
        return None

    def search(self, query, location, api_key=None, cx=None):
        results = []
        base_url = "https://www.yellowpages.com/search"
        params = {"search_terms": query, "geo_location_terms": location}
        
        print(f"--- [YellowPages] Double-Deep + Cloudflare Decoder ---")
        
        try:
            response = requests.get(
                base_url, 
                params=params, 
                impersonate="chrome110", 
                timeout=15
            )
            
            if response.status_code == 403:
                print("--- BLOCKED: IP Ban. Restart router or wait. ---")
                return []
                
            soup = BeautifulSoup(response.content, 'html.parser')
            cards = soup.select('.result')
            
            if not cards: print("--- No results found. ---")
            
            for card in cards:
                # 1. Basic Info
                name_tag = card.select_one('.business-name')
                name = name_tag.get_text(strip=True) if name_tag else "Unknown"
                phone = card.select_one('.phones').get_text(strip=True) if card.select_one('.phones') else "N/A"
                
                # Get URLs
                yp_suffix = name_tag['href'] if name_tag else None
                yp_full_url = urljoin("https://www.yellowpages.com", yp_suffix) if yp_suffix else None
                
                web_tag = card.select_one('.links a.track-visit-website')
                external_website = web_tag['href'] if web_tag else "N/A"
                
                email = "N/A"

                # 2. STRATEGY A: Check Internal YP Profile First
                if yp_full_url:
                    email = self._scrape_yp_internal_profile(yp_full_url)
                
                # 3. STRATEGY B: Fallback to External Website
                if not email or email == "N/A":
                    if external_website != "N/A":
                        found = self._scrape_external_website(external_website)
                        if found: email = found
                
                results.append({
                    "Name": name,
                    "Email": email,
                    "Website": external_website,
                    "Location": f"{location} (Ph: {phone})",
                    "Source": "YellowPages"
                })
                
            return results

        except Exception as e:
            print(f"YP Scrape Error: {e}")
            return []