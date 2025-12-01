import re
import time
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from flask import (
    Flask, render_template, request, jsonify, send_file
)
#AIzaSyDMKSv6R1-GaCUmQLWrHDmxH1dThLoIDts
#AIzaSyBAN4xVIH1lX7Hy-7IagxLUQbEsTxi_jZ0
#AIzaSyARuL3o6NskWBH3AjkDZPdcejuu4srvqK0
#AIzaSyB71NSc0iaTy5UnN61g5zeymui_lqQzH10
#AIzaSyDMKSv6R1-GaCUmQLWrHDmxH1dThLoIDts
#AIzaSyAm8-a8CtA8fBgYze5LnEgsShwdtlj5J-E
#AIzaSyDMKSv6R1-GaCUmQLWrHDmxH1dThLoIDts ---MAIN--
# --- Flask App Setup ---
app = Flask(__name__)
ALL_COLLECTED_LEADS = []

# --- Junk filter and Regex (from your script) ---
JUNK_DOMAINS = {
    'example.com', 'sentry.io', 'wixpress.com', 'google.com',
    'schema.org', 'wordpress.org', '.gov'
}
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
# ---------------------

def filter_email(email):
    """
    Checks if an email is not in our JUNK_DOMAINS list.
    """
    try:
        domain = email.split('@')[-1]
        if domain in JUNK_DOMAINS:
            return False
        return True
    except Exception:
        return False

def run_google_api_search(query, api_key, cx, location_tag):
    """
    Searches Google API for all available pages (up to 10)
    and extracts emails from snippets.

    MODIFIED: This function now RETURNS the list of leads
    instead of saving to a file.
    """
    print("--- Starting Google API Request ---")
    print(f"Query: {query}")

    new_leads_from_this_search = []
    found_emails_this_search = set()

    try:
        service = build("customsearch", "v1", developerKey=api_key)
        page = 0
        while True:
            start_index = (page * 10) + 1
            print(f"\n--- Searching Page {page + 1} (Results {start_index} - {start_index + 9}) ---")

            result = service.cse().list(
                q=query,
                cx=cx,
                num=10,
                start=start_index
            ).execute()

            if 'items' not in result:
                print("No more results found for this query.")
                break

            print(f"API Call Successful for page {page + 1}.")

            for item in result['items']:
                snippet_text = item.get('snippet', '')
                html_snippet = item.get('htmlSnippet', '')
                full_text_to_search = snippet_text + " " + html_snippet
                website_url = item.get('link')

                # --- THIS IS THE FIX FOR 'NAME' ---
                # We get the title of the search result
                name = item.get('title', 'N/A')

                emails_in_snippet = set(re.findall(EMAIL_REGEX, full_text_to_search))

                if emails_in_snippet:
                    for email in emails_in_snippet:
                        if filter_email(email) and email not in found_emails_this_search:
                            found_emails_this_search.add(email)

                            new_leads_from_this_search.append({
                                "Name": name, # <-- FIXED
                                "Email": email,
                                "Website": website_url,
                                "Location": location_tag # <-- FIXED
                            })

            time.sleep(0.5)
            page += 1
            if page >= 10:
                print("\nReached 10-page (100 result) hard limit from Google API.")
                break

        print(f"\n--- Search Complete! Found {len(new_leads_from_this_search)} new leads ---")
        return new_leads_from_this_search # Return the list

    except HttpError as e:
        print(f"\n--- API REQUEST FAILED (HttpError) ---")
        print(f"ERROR DETAILS: {e}")
        return {"error": str(e)}

    except Exception as e:
        print(f"\n--- An Unknown Error Occurred ---")
        print(f"Error: {e}")
        return {"error": str(e)}

# --- NEW: FLASK WEB ROUTES ---

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def handle_search():
    """
    This is the API endpoint our JavaScript will call.
    It runs the search and returns the *new* leads.
    """
    global ALL_COLLECTED_LEADS

    data = request.json
    query = data.get('query')
    api_key = data.get('apiKey')
    cx = data.get('cx')
    # --- THIS IS THE FIX FOR 'LOCATION' ---
    # We get the location from the new UI field
    location = data.get('location')

    if not query or not api_key or not cx or not location:
        return jsonify({"error": "Missing query, API Key, CX ID, or Location."}), 400

    # We no longer need to "guess" the location.
    # We pass the user-provided location to the search function.
    new_leads = run_google_api_search(query, api_key, cx, location)

    if isinstance(new_leads, dict) and "error" in new_leads:
        return jsonify(new_leads), 400

    # --- STACKING LOGIC ---
    ALL_COLLECTED_LEADS.extend(new_leads)

    return jsonify(new_leads)

@app.route('/download')
def handle_download():
    """
    This is the API endpoint for the download button.
    It takes *all* stacked leads and sends them as a CSV.
    """
    global ALL_COLLECTED_LEADS

    if not ALL_COLLECTED_LEADS:
        return "No leads to download.", 404

    df = pd.DataFrame(ALL_COLLECTED_LEADS)
    df = df[['Name', 'Email', 'Website', 'Location']]

    mem_file = io.BytesIO()
    df.to_csv(mem_file, index=False, encoding='utf-8')
    mem_file.seek(0)

    return send_file(
        mem_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name='all_stacked_leads.csv'
    )

# --- This makes the script runnable as a server ---
if __name__ == "__main__":
    print("Starting Flask server... Go to http://127.0.0.1:5000")
    app.run(debug=True, port=5000)

