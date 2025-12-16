import os
import json
import google.generativeai as genai
import time
from urllib.parse import urlparse

def extract_business_info(page_text, url):
    """
    Uses Google Gemini 1.5 Flash with STRICT rules for Name and Email accuracy.
    """
    api_key = os.environ.get('GEMINI_API_KEY')

    # Fail fast if no key
    if not api_key:
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # 1. Extract domain to help AI filter garbage emails
        # (e.g. if site is eliteplumbing.com, we want emails ending in @eliteplumbing.com)
        domain = urlparse(url).netloc.replace('www.', '')

        # 2. Limit text to save tokens, but keep enough for footer (where names usually are)
        # 15k characters is usually enough for the whole homepage.
        clean_text = page_text[:15000]

        prompt = f"""
        You are a Data Extraction Expert. Analyze this website text for: {url}
        Domain: {domain}

        Extract the following fields into a JSON object. Follow these STRICT rules:

        1. "business_name": 
           - Look for the text next to the Copyright symbol (©) in the footer.
           - Look for the main header on the "About Us" section.
           - INVALID NAMES: "Home", "Index", "Welcome", "Page 1", "My Website", "Loading".
           - If unclear, use the domain name formatted as a Title.

        2. "email": 
           - Find the best CONTACT email for a sales lead.
           - PRIORITY: Emails matching the domain @{domain}.
           - IGNORE: generic hosting emails like 'support@wix.com', 'admin@wordpress.com', 'abuse@'.
           - Return null if only garbage emails are found.

        3. "phone": 
           - The main business phone number formatted cleanly.

        4. "location": 
           - The full physical address (Street, City, State, Zip). 

        5. "industry": 
           - A short 2-3 word classification (e.g. "HVAC Contractor", "Dental Clinic").

        Website Text:
        {clean_text}

        Return ONLY valid JSON.
        """

        # Small delay to respect free tier limits (15 Requests Per Minute)
        time.sleep(2) 

        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})

        return json.loads(response.text)

    except Exception:
        return None