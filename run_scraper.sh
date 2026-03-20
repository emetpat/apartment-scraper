#!/bin/bash
cd "$(dirname "$0")"
echo "Running DC Apartment Scraper..."
python3 scraper.py
echo ""
echo "Done! Check your Google Sheet for new listings."
