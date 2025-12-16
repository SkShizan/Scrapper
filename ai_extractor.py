# ai_extractor.py
import os
import json
import google.generativeai as genai
import time

def extract_business_info(page_text, url):
    """
    Uses Google Gemini Flash (Free Tier) to extract business details.
    """
    api_key = os.environ.get('GEMINI_API_KEY')

    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Limit text to first 15k chars (Gemini handles large context well)
        clean_text = page_text[:15000]

        prompt = f"""
        Analyze the text from the website {url}.
        Extract the following details in valid JSON format only:
        - business_name (The official name of the company)
        - email (The best contact email found. Return null if none.)
        - phone (The main phone number. Return null if none.)
        - location (The full physical address or city/state. Return null if none.)
        - industry (A 2-3 word summary of what they do, e.g., "Dental Clinic" or "Digital Marketing")

        Website Text:
        {clean_text}

        Output JSON:
        """

        # Add a small delay to respect the 15 RPM free limit if running in loops
        time.sleep(2) 

        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})

        return json.loads(response.text)

    except Exception as e:
        # print(f"Gemini Extraction Error: {e}")
        return None