"""
DC Apartment Scraper
Scrapes Craigslist, Zillow, and Realtor.com for DC rentals
and pushes new listings to Google Sheets.
"""

import requests
import gspread
import time
import re
import logging
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials
from config import (
    GOOGLE_SHEETS_ID,
    GOOGLE_CREDENTIALS_FILE,
    RAPIDAPI_KEY,
    MIN_PRICE,
    MAX_PRICE,
    MIN_BEDS,
    SEARCH_RADIUS_MILES,
)

logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

SHEET_HEADERS = [
    "Date Added", "Source", "Title", "Price", "Beds", "Baths", "Address", "Link", "Status"
]


# ─── Google Sheets ────────────────────────────────────────────────────────────

def get_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEETS_ID).sheet1
    return sheet


def get_existing_links(sheet):
    try:
        links = sheet.col_values(8)  # Column H = Link
        return set(links[1:])        # Skip header
    except Exception as e:
        logging.error(f"Error fetching existing links: {e}")
        return set()


def ensure_headers(sheet):
    first_row = sheet.row_values(1)
    if first_row != SHEET_HEADERS:
        sheet.clear()
        sheet.insert_row(SHEET_HEADERS, 1)
        sheet.format("A1:I1", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.7},
        })
        sheet.freeze(rows=1)


def append_listings(sheet, listings, existing_links):
    new_count = 0
    for listing in listings:
        if listing["link"] not in existing_links:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                listing["source"],
                listing["title"],
                listing["price"],
                listing["beds"],
                listing["baths"],
                listing["address"],
                listing["link"],
                "New",
            ]
            sheet.append_row(row)
            existing_links.add(listing["link"])
            new_count += 1
            time.sleep(0.5)
    return new_count


# ─── Craigslist ───────────────────────────────────────────────────────────────

def scrape_craigslist():
    listings = []
    base_url = "https://washingtondc.craigslist.org/search/apa"
    params = {
        "min_price":        MIN_PRICE,
        "max_price":        MAX_PRICE,
        "min_bedrooms":     MIN_BEDS,
        "availabilityMode": 0,
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(base_url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        results = soup.select("li.cl-search-result, li[data-pid]")
        logging.info(f"Craigslist: found {len(results)} raw results")

        for item in results:
            try:
                link_el = (
                    item.select_one("a.cl-app-anchor") or
                    item.select_one("a.posting-title") or
                    item.select_one("a[href*='craigslist.org']")
                )
                title_el = (
                    item.select_one("[data-testid='listing-title']") or
                    item.select_one(".label") or
                    item.select_one(".titlestring")
                )
                price_el = (
                    item.select_one(".priceinfo") or
                    item.select_one(".price")
                )
                meta_el = (
                    item.select_one(".meta") or
                    item.select_one(".housing")
                )

                title = title_el.get_text(strip=True) if title_el else (
                    link_el.get_text(strip=True) if link_el else "N/A"
                )
                price = price_el.get_text(strip=True) if price_el else "N/A"
                link  = link_el["href"] if link_el and link_el.get("href") else ""
                meta  = meta_el.get_text(" ", strip=True) if meta_el else ""

                if link and link.startswith("/"):
                    link = "https://washingtondc.craigslist.org" + link

                beds_match  = re.search(r"(\d+)\s*br",       meta, re.IGNORECASE)
                baths_match = re.search(r"(\d+\.?\d*)\s*ba", meta, re.IGNORECASE)
                beds  = beds_match.group(1)  + "br" if beds_match  else "N/A"
                baths = baths_match.group(1) + "ba" if baths_match else "N/A"

                addr_match = re.search(r"[·\-]\s*(.{5,60})$", meta)
                address = addr_match.group(1).strip() if addr_match else "Washington, DC"

                if link and title != "N/A":
                    listings.append({
                        "source":  "Craigslist",
                        "title":   title,
                        "price":   price,
                        "beds":    beds,
                        "baths":   baths,
                        "address": address,
                        "link":    link,
                    })
            except Exception as e:
                logging.warning(f"Craigslist parse error on item: {e}")
                continue

        if not listings:
            snippet = resp.text[:500].replace("\n", " ")
            logging.warning(f"Craigslist 0 results. HTML snippet: {snippet}")

    except Exception as e:
        logging.error(f"Craigslist scrape failed: {e}")

    logging.info(f"Craigslist: returning {len(listings)} listings")
    return listings


# ─── Zillow (via RapidAPI — real-estate101 by usamamernrealestate) ────────────

def scrape_zillow():
    listings = []

    search_state = {
        "isMapVisible": True,
        "filterState": {
            "fr":   {"value": True},
            "fsba": {"value": False},
            "fsbo": {"value": False},
            "nc":   {"value": False},
            "cmsn": {"value": False},
            "auc":  {"value": False},
            "fore": {"value": False},
            "mp":   {"value": {"max": MAX_PRICE, "min": MIN_PRICE}},
            "beds": {"min": MIN_BEDS},
            "sort": {"value": "globalrelevanceex"},
        },
        "isListVisible": True,
        "usersSearchTerm": "Washington, DC",
        "regionSelection": [{"regionId": 26657, "regionType": 6}],
    }
    zillow_url = (
        "https://www.zillow.com/washington-dc/rentals/?"
        "searchQueryState=" + urllib.parse.quote(
            str(search_state)
            .replace("'", '"')
            .replace("True", "true")
            .replace("False", "false")
        )
    )

    url = "https://real-estate101.p.rapidapi.com/api/search/byurl"
    params = {"url": zillow_url, "page": "1"}
    headers = {
        "x-rapidapi-key":  RAPIDAPI_KEY,
        "x-rapidapi-host": "real-estate101.p.rapidapi.com",
        "Content-Type":    "application/json",
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        props = data.get("results", data.get("data", data.get("props", [])))
        if isinstance(props, dict):
            props = props.get("results", props.get("listResults", []))
        logging.info(f"Zillow: found {len(props)} raw results")

        for p in props:
            try:
                zpid    = p.get("zpid", "")
                address = p.get("address", p.get("addressStreet", "Washington, DC"))
                price   = p.get("price", p.get("unformattedPrice", "N/A"))
                beds    = p.get("beds",  p.get("bedrooms",  None))
                baths   = p.get("baths", p.get("bathrooms", None))
                beds    = f"{beds}br"  if beds  else "N/A"
                baths   = f"{baths}ba" if baths else "N/A"
                link    = p.get("detailUrl", p.get("url", ""))

                if link and not link.startswith("http"):
                    link = "https://www.zillow.com" + link
                elif not link and zpid:
                    link = f"https://www.zillow.com/homedetails/{zpid}_zpid/"

                if isinstance(price, (int, float)):
                    price = f"${price:,}/mo"

                if link:
                    listings.append({
                        "source":  "Zillow",
                        "title":   address,
                        "price":   str(price),
                        "beds":    beds,
                        "baths":   baths,
                        "address": address,
                        "link":    link,
                    })
            except Exception as e:
                logging.warning(f"Zillow parse error on item: {e}")
                continue

    except Exception as e:
        logging.error(f"Zillow scrape failed: {e}")

    logging.info(f"Zillow: returning {len(listings)} listings")
    return listings


# ─── Realtor.com (via RapidAPI — realtor-search by ntd119) ───────────────────

def scrape_realtor():
    listings = []
    url = "https://realtor-search.p.rapidapi.com/properties/search-rent"
    params = {
        "location": "city:Washington, DC",
        "sortBy":   "best_match",
    }
    headers = {
        "x-rapidapi-key":  RAPIDAPI_KEY,
        "x-rapidapi-host": "realtor-search.p.rapidapi.com",
        "Content-Type":    "application/json",
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("data", {}).get("results", [])
        logging.info(f"Realtor.com: found {len(results)} raw results")

        for item in results:
            try:
                # Address
                loc  = item.get("location", {})
                addr = loc.get("address", {}) if isinstance(loc, dict) else {}
                if isinstance(addr, dict):
                    street  = addr.get("line",      addr.get("street", ""))
                    city    = addr.get("city",       "Washington")
                    state   = addr.get("state_code", "DC")
                    address = f"{street}, {city}, {state}".strip(", ")
                else:
                    address = str(addr) if addr else "Washington, DC"

                # Price
                price_raw = item.get("list_price", None)
                if isinstance(price_raw, (int, float)):
                    if price_raw < MIN_PRICE or price_raw > MAX_PRICE:
                        continue
                    price = f"${int(price_raw):,}/mo"
                else:
                    price = "N/A"

                # Beds & Baths
                desc      = item.get("description", {})
                beds_raw  = desc.get("beds",  None) if isinstance(desc, dict) else None
                baths_raw = desc.get("baths", desc.get("baths_consolidated", None)) if isinstance(desc, dict) else None

                if isinstance(beds_raw, (int, float)) and beds_raw < MIN_BEDS:
                    continue

                beds  = f"{int(beds_raw)}br"  if beds_raw  else "N/A"
                baths = f"{int(baths_raw)}ba" if baths_raw else "N/A"

                # Title
                prop_type = desc.get("type", "Rental") if isinstance(desc, dict) else "Rental"
                title = f"{prop_type.replace('_', ' ').title()} — {address}"

                # Link
                property_id = item.get("property_id", "")
                permalink   = item.get("permalink", "")
                link = (
                    f"https://www.realtor.com/realestateandhomes-detail/{permalink}" if permalink
                    else f"https://www.realtor.com/realestateandhomes-detail/{property_id}" if property_id
                    else ""
                )

                if link:
                    listings.append({
                        "source":  "Realtor.com",
                        "title":   title,
                        "price":   price,
                        "beds":    beds,
                        "baths":   baths,
                        "address": address,
                        "link":    link,
                    })
            except Exception as e:
                logging.warning(f"Realtor.com parse error on item: {e}")
                continue

    except Exception as e:
        logging.error(f"Realtor.com scrape failed: {e}")

    logging.info(f"Realtor.com: returning {len(listings)} listings")
    return listings


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    logging.info("=" * 50)
    logging.info("Scrape run started")

    print("🔗 Connecting to Google Sheets...")
    sheet = get_sheet()
    ensure_headers(sheet)
    existing_links = get_existing_links(sheet)
    print(f"   Found {len(existing_links)} existing listings in sheet")

    all_listings = []

    print("🔍 Scraping Craigslist...")
    cl = scrape_craigslist()
    print(f"   → {len(cl)} listings found")
    all_listings.extend(cl)

    if RAPIDAPI_KEY and RAPIDAPI_KEY != "YOUR_RAPIDAPI_KEY_HERE":
        print("🔍 Scraping Zillow...")
        zl = scrape_zillow()
        print(f"   → {len(zl)} listings found")
        all_listings.extend(zl)

        print("🔍 Scraping Realtor.com...")
        rl = scrape_realtor()
        print(f"   → {len(rl)} listings found")
        all_listings.extend(rl)
    else:
        print("⚠️  Skipping Zillow & Realtor.com (no RapidAPI key set in config.py)")

    print(f"\n📋 Total listings scraped: {len(all_listings)}")
    print("📤 Pushing new listings to Google Sheets...")
    new_count = append_listings(sheet, all_listings, existing_links)

    print(f"\n✅ Done! {new_count} new listings added to your sheet.")
    logging.info(f"Run complete. {new_count} new listings added.")


if __name__ == "__main__":
    main()
