# Lead Scraper Application

## Overview
A Flask-based web application for scraping business leads from multiple sources including Google Search, LinkedIn, Facebook, Instagram, and Yellow Pages. Users can search for businesses by query and location, extract contact information, and export results to CSV.

## Recent Changes (December 1, 2025)
- **Project Setup**: Configured for Replit environment
- **Dependencies**: Added python-dotenv and curl-cffi to requirements.txt
- **Code Fixes**: Fixed method signature compatibility in scraper classes
- **Workflow**: Configured Flask app to run on port 5000
- **Documentation**: Created .gitignore for Python project

## Project Architecture

### Technology Stack
- **Backend**: Flask (Python 3.11)
- **Web Scraping**: BeautifulSoup4, curl-cffi, requests
- **Data Processing**: pandas
- **APIs**: Google Custom Search API
- **Task Queue**: RQ (Redis Queue) - configured but not actively used

### Directory Structure
```
.
├── app.py                  # Main Flask application
├── config.py               # Configuration with environment variables
├── requirements.txt        # Python dependencies
├── scrapers/              # Scraper modules
│   ├── __init__.py
│   ├── base_scraper.py    # Abstract base class
│   ├── google.py          # Google Search scraper
│   ├── social.py          # Social media X-ray search scraper
│   └── yellow_pages.py    # Yellow Pages direct scraper
└── templates/
    └── index.html         # Frontend UI

```

### Key Features
1. **Multi-Platform Search**:
   - Google Search (requires API key)
   - LinkedIn X-Ray Search (via Google)
   - Facebook/Instagram (via Google)
   - Yellow Pages (direct scraping, no API needed)

2. **Email Extraction**:
   - Regex-based email detection
   - Cloudflare email protection decoder
   - Junk email filtering

3. **Data Export**:
   - CSV download of all collected leads
   - Structured data with Name, Email, Website, Location, Source

### Environment Variables
Required in `.env` file (not tracked in git):
- `GOOGLE_API_KEY` - Google Custom Search API key
- `GOOGLE_CX` - Google Custom Search Engine ID
- `SECRET_KEY` - Flask secret key (optional, has default)
- `FLASK_DEBUG` - Debug mode (optional, default: False)
- `REDIS_HOST` - Redis host (optional, default: localhost)
- `REDIS_PORT` - Redis port (optional, default: 6379)

### Flask Routes
- `GET /` - Main application interface
- `POST /search` - Execute search and return results
- `GET /download` - Download all collected leads as CSV

### How It Works
1. User enters search credentials and query via web interface
2. User selects platform (Google, LinkedIn, Facebook, Instagram, Yellow Pages)
3. Backend routes request to appropriate scraper class
4. Scraper extracts contact information from search results
5. Results are displayed in a table and accumulated in memory
6. User can download all results as CSV file

## Development Notes

### Running Locally
The app is configured to run on `0.0.0.0:5000` which is required for Replit's proxy system. The workflow automatically starts the Flask development server.

### Known Limitations
- Results are stored in memory (cleared on server restart)
- Yellow Pages scraping may be blocked by IP bans
- Google API has rate limits and requires valid credentials
- No database persistence (by design)

### Security Considerations
- API keys should be stored in environment variables
- Never commit `.env` file to git
- Flask secret key should be set for production use

## User Preferences
None specified yet.
