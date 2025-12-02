# Lead Scraper Application

## Overview
A Flask-based web application for scraping business leads from multiple sources including Google Search, LinkedIn, Facebook, Instagram, and Yellow Pages. Features user authentication with email OTP verification and admin approval workflow.

## Recent Changes (December 2, 2025)
- **User Authentication**: Added complete signup/login system with email OTP verification
- **Admin Approval**: New accounts require admin approval before accessing the app
- **Per-User Data**: Each user's scraped leads are stored separately in SQLite database
- **Admin Dashboard**: Superuser panel for managing user approvals and accounts
- **SMTP Integration**: Email service for sending OTP verification codes
- **Security Improvements**: Password hashing, secure sessions, route protection

## Project Architecture

### Technology Stack
- **Backend**: Flask (Python 3.11)
- **Database**: SQLite with Flask-SQLAlchemy
- **Authentication**: Flask-Login with custom OTP verification
- **Forms**: Flask-WTF with validation
- **Web Scraping**: BeautifulSoup4, curl-cffi, requests
- **Data Processing**: pandas
- **APIs**: Google Custom Search API

### Directory Structure
```
.
├── app.py                  # Main Flask application with auth routes
├── config.py               # Configuration with environment variables
├── models.py               # SQLAlchemy models (User, Lead)
├── forms.py                # WTForms for authentication
├── email_service.py        # SMTP service for OTP emails
├── requirements.txt        # Python dependencies
├── scrapers/               # Scraper modules
│   ├── __init__.py
│   ├── base_scraper.py     # Abstract base class
│   ├── google.py           # Google Search scraper
│   ├── social.py           # Social media X-ray search scraper
│   └── yellow_pages.py     # Yellow Pages direct scraper
└── templates/
    ├── base.html           # Base template with navbar
    ├── login.html          # Login page
    ├── signup.html         # Registration page
    ├── verify_otp.html     # OTP verification page
    ├── pending_approval.html # Waiting for approval page
    ├── admin.html          # Admin dashboard
    └── index.html          # Main scraper interface
```

### Authentication Flow
1. User signs up with name, email, password
2. System sends 6-digit OTP to email
3. User enters OTP to verify email
4. Account waits for admin approval
5. Admin approves account via dashboard
6. User can now login and use the scraper

### Key Features
1. **Multi-Platform Search**:
   - Google Search (requires API key)
   - LinkedIn X-Ray Search (via Google)
   - Facebook/Instagram (via Google)
   - Yellow Pages (direct scraping, pagination supported)

2. **User Management**:
   - Email/password authentication
   - OTP email verification
   - Admin approval workflow
   - User enable/disable
   - Admin role management

3. **Data Export**:
   - Per-user lead storage
   - CSV download of user's leads
   - Clear leads functionality

### Environment Variables / Secrets
Required secrets (set in Replit Secrets tab):

**Admin Account:**
- `ADMIN_EMAIL` - Admin login email (default: admin@example.com)
- `ADMIN_PASSWORD` - Admin login password (default: admin123)

**SMTP Configuration (for OTP emails):**
- `SMTP_HOST` - SMTP server hostname (e.g., smtp.gmail.com)
- `SMTP_PORT` - SMTP port (default: 587)
- `SMTP_USER` - SMTP username/email
- `SMTP_PASSWORD` - SMTP password or app password
- `SMTP_FROM_EMAIL` - From email address (optional, uses SMTP_USER)
- `SMTP_FROM_NAME` - From name (default: Lead Scraper)

**Optional:**
- `SECRET_KEY` - Flask session secret (auto-generated if not set)
- `GOOGLE_API_KEY` - Google Custom Search API key
- `GOOGLE_CX` - Google Custom Search Engine ID

### Flask Routes

**Authentication:**
- `GET/POST /signup` - User registration
- `GET/POST /verify-otp` - Email verification
- `POST /resend-otp` - Resend verification code
- `GET/POST /login` - User login
- `GET /logout` - User logout

**Main App (requires login + approval):**
- `GET /` - Main scraper interface
- `POST /search` - Execute search and save leads
- `GET /download` - Download user's leads as CSV
- `POST /clear-leads` - Clear user's leads

**Admin (requires admin role):**
- `GET /admin` - Admin dashboard
- `POST /admin/approve/<id>` - Approve user
- `POST /admin/reject/<id>` - Reject and delete user
- `POST /admin/toggle-status/<id>` - Enable/disable user
- `POST /admin/toggle-admin/<id>` - Grant/revoke admin

## Development Notes

### Default Admin Account
On first run, a superuser is created:
- Email: admin@example.com (or ADMIN_EMAIL env var)
- Password: admin123 (or ADMIN_PASSWORD env var)

**Important:** Change the admin credentials in production!

### SMTP Setup
If SMTP is not configured, OTP codes will be displayed on screen (development only). For production, configure SMTP secrets.

For Gmail:
1. Enable 2FA on your Google account
2. Generate an App Password
3. Use the app password as SMTP_PASSWORD

### Database
SQLite database (leadscaper.db) is created automatically. Contains:
- `users` table - User accounts
- `leads` table - Scraped leads per user

## User Preferences
None specified yet.
