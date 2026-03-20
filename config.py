# ─────────────────────────────────────────────
#  DC Apartment Scraper — Configuration
#  Fill in each value before running scraper.py
# ─────────────────────────────────────────────

# ── Google Sheets ──────────────────────────────
# Your Google Sheet ID (from the URL):
# https://docs.google.com/spreadsheets/d/THIS_PART_HERE/edit
GOOGLE_SHEETS_ID = "YOUR_GOOGLE_SHEET_ID_HERE"

# Path to your Google Service Account credentials JSON file
# (see SETUP.md for how to create this)
GOOGLE_CREDENTIALS_FILE = "credentials.json"

# ── RapidAPI ───────────────────────────────────
# Sign up free at https://rapidapi.com
# Subscribe to:
#   - "Zillow Com" by apimaker  (free tier)
#   - "Apartments Com" by apimaker  (free tier)
# Then paste your key here:
RAPIDAPI_KEY = "YOUR_RAPIDAPI_KEY_HERE"

# ── Search Filters ─────────────────────────────
MIN_PRICE = 1200          # Minimum monthly rent ($)
MAX_PRICE = 2800          # Maximum monthly rent ($)
MIN_BEDS  = 2             # Minimum bedrooms (set to 1 for studios/1br too)

# Radius for Craigslist search (in miles from DC center)
SEARCH_RADIUS_MILES = 10
