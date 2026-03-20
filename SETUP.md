# DC Apartment Scraper — Setup Guide (macOS)

This script scrapes Craigslist, Zillow, and Apartments.com for DC rentals
and automatically adds new listings to a Google Sheet.

---

## Step 1: Install Python

1. Open **Terminal** (Cmd + Space → type "Terminal")
2. Check if Python 3 is already installed: `python3 --version`
3. If not, install it from https://www.python.org/downloads/mac-osx/
   or via Homebrew: `brew install python`

---

## Step 2: Install Dependencies

In Terminal, navigate to this folder and run:

```bash
cd path/to/apartment_scraper
pip3 install -r requirements.txt
```

---

## Step 3: Set Up Google Sheets API

### 3a. Create a Google Cloud Project
1. Go to https://console.cloud.google.com/
2. Click **"New Project"** → name it "Apartment Scraper" → Create
3. Search **"Google Sheets API"** → Enable it
4. Search **"Google Drive API"** → Enable it too

### 3b. Create a Service Account
1. Go to **IAM & Admin → Service Accounts**
2. Click **"Create Service Account"**
3. Name: `apartment-scraper` → Create → Done

### 3c. Download Credentials
1. Click your new service account → **Keys** tab
2. **Add Key → Create new key → JSON** → Download
3. Rename the file to `credentials.json`
4. Move it into this folder (same folder as `scraper.py`)

### 3d. Create & Share Your Google Sheet
1. Go to https://sheets.google.com and create a new blank spreadsheet
2. Copy the Sheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/**THIS_IS_YOUR_ID**/edit`
3. Open `credentials.json`, find the `"client_email"` value
   (looks like: `apartment-scraper@your-project.iam.gserviceaccount.com`)
4. In your Google Sheet, click **Share** and share with that email
   (give it **Editor** access)

---

## Step 4: Get a RapidAPI Key (for Zillow & Apartments.com)

1. Go to https://rapidapi.com and create a free account
2. Subscribe to these two APIs (both have free tiers):
   - Search "Zillow Com" → Subscribe to **Basic (free)** plan
   - Search "Realtor Search" by ntd119 → Subscribe to **Basic (free)** plan
3. Go to https://rapidapi.com/developer/apps → copy your **API Key**

---

## Step 5: Fill In config.py

Open `config.py` in any text editor and fill in:

```python
GOOGLE_SHEETS_ID        = "paste-your-sheet-id-here"
GOOGLE_CREDENTIALS_FILE = "credentials.json"
RAPIDAPI_KEY            = "paste-your-rapidapi-key-here"

MIN_PRICE = 1200   # Adjust to your budget
MAX_PRICE = 2800
MIN_BEDS  = 2
```

---

## Step 6: Run the Script

In Terminal:
```bash
cd path/to/apartment_scraper
python3 scraper.py
```

Or double-click `run_scraper.sh` (if your Mac opens shell scripts in Terminal).

You should see:
```
Connecting to Google Sheets...
Scraping Craigslist...
Scraping Zillow...
Scraping Apartments.com...
Done! 24 new listings added to your sheet.
```

---

## Step 7: Schedule It to Run Every Few Hours (launchd)

Mac uses `launchd` instead of Task Scheduler. Here's how to set it up:

### 7a. Find the full path to python3
```bash
which python3
```
Copy the output (e.g. `/usr/local/bin/python3` or `/opt/homebrew/bin/python3`)

### 7b. Find the full path to your scraper folder
```bash
cd path/to/apartment_scraper && pwd
```
Copy the output (e.g. `/Users/yourname/apartment_scraper`)

### 7c. Create a launchd plist file

Create the file `~/Library/LaunchAgents/com.apartment.scraper.plist` with
this content — replacing the two paths with your actual values from above:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.apartment.scraper</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/yourname/apartment_scraper/scraper.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/yourname/apartment_scraper</string>
    <key>StartInterval</key>
    <integer>14400</integer>
    <key>StandardOutPath</key>
    <string>/Users/yourname/apartment_scraper/scraper.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/yourname/apartment_scraper/scraper.log</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

You can create this file quickly by running in Terminal
(replace paths first):

```bash
nano ~/Library/LaunchAgents/com.apartment.scraper.plist
```

Paste the XML above, then press Ctrl+O to save and Ctrl+X to exit.

### 7d. Load the schedule
```bash
launchctl load ~/Library/LaunchAgents/com.apartment.scraper.plist
```

It will now run every 4 hours (14400 seconds) automatically in the background.

### 7e. To stop the schedule later
```bash
launchctl unload ~/Library/LaunchAgents/com.apartment.scraper.plist
```

---

## Your Google Sheet Columns

| Column | Contents |
|--------|----------|
| A | Date Added |
| B | Source (Craigslist / Zillow / Apartments.com) |
| C | Title / Property Name |
| D | Price |
| E | Beds |
| F | Address |
| G | Link (clickable) |
| H | Status (starts as "New" — change to "Reviewed", "Applied", etc.) |

---

## Troubleshooting

**"ModuleNotFoundError"** → Run `pip3 install -r requirements.txt` again

**"Permission denied" on run_scraper.sh** → Run `chmod +x run_scraper.sh` in Terminal

**"No listings found"** → Check `scraper.log` for details

**"Invalid API key"** → Double-check your RapidAPI key in `config.py`

**Sheet not updating** → Make sure you shared the sheet with the service account email from `credentials.json`

---

## Files in This Folder

```
apartment_scraper/
├── scraper.py          <- Main script
├── config.py           <- Your settings & API keys
├── requirements.txt    <- Python dependencies
├── run_scraper.sh      <- Run manually from Terminal
├── credentials.json    <- (you add this) Google Service Account key
├── scraper.log         <- Auto-generated log file
└── SETUP.md            <- This file
```
