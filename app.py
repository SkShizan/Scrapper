import io
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from config import Config

# --- IMPORT OUR NEW TOOLS ---
from scrapers.google import GoogleScraper
from scrapers.social import SocialMediaScraper
from scrapers.yellow_pages import YellowPagesScraper

app = Flask(__name__)
app.config.from_object(Config)

ALL_COLLECTED_LEADS = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def handle_search():
    global ALL_COLLECTED_LEADS
    
    data = request.json
    query = data.get('query')
    location = data.get('location')
    api_key = data.get('apiKey')
    cx = data.get('cx')
    platform = data.get('platform', 'google') # Get the chosen platform

    if not query or not location:
        return jsonify({"error": "Missing query or location."}), 400

    # --- FACTORY PATTERN: Select the right tool ---
    scraper = None
    
    if platform == 'google':
        scraper = GoogleScraper()
    elif platform in ['linkedin', 'facebook', 'instagram']:
        scraper = SocialMediaScraper(platform)
    elif platform == 'yellowpages':
        scraper = YellowPagesScraper()
    else:
        return jsonify({"error": "Invalid platform selected"}), 400

    # --- EXECUTE SEARCH ---
    # Note: YellowPages ignores apiKey/cx, others use it.
    new_leads = scraper.search(query, location, api_key, cx)

    # Check for errors returned by the scraper
    if isinstance(new_leads, dict) and "error" in new_leads:
        return jsonify(new_leads), 400

    ALL_COLLECTED_LEADS.extend(new_leads)
    
    return jsonify(new_leads)

@app.route('/download')
def handle_download():
    global ALL_COLLECTED_LEADS
    if not ALL_COLLECTED_LEADS:
        return "No leads to download.", 404

    # Create CSV
    df = pd.DataFrame(ALL_COLLECTED_LEADS)
    # Ensure all columns exist even if some scrapers didn't return them
    columns = ['Name', 'Email', 'Website', 'Location', 'Source']
    for col in columns:
        if col not in df.columns:
            df[col] = ''
            
    df = df[columns] # Reorder

    mem_file = io.BytesIO()
    df.to_csv(mem_file, index=False, encoding='utf-8')
    mem_file.seek(0)

    return send_file(
        mem_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name='leads_export.csv'
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)