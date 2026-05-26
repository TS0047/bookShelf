"""
books_api.py — Wraps the Google Books API.

Two operations:
  1. search_title(query) -> best matching volume title
  2. fetch_isbn(title)   -> {"isbn10": ..., "isbn13": ...}

No API key required for basic volume searches (free tier, 1000 req/day).
"""

import time
import requests
import json
import os
from typing import Dict, Optional, Tuple

_BASE = "https://www.googleapis.com/books/v1/volumes"
_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")  # Optional: set env var for authenticated requests
_TIMEOUT = 8


def _get(params: dict, retries: int = 5) -> Optional[dict]:
    """
    Make a request to Google Books API with exponential backoff on rate limiting.
    If API_KEY is set, it will be used (much higher rate limits).
    """
    if _API_KEY:
        params["key"] = _API_KEY
        print(f"[DEBUG] Using authenticated request (API key set)")
    else:
        print(f"[DEBUG] Using unauthenticated request (no API key - limited to ~1000 req/day)")
    
    for attempt in range(retries):
        try:
            print(f"\n[DEBUG] API Request Attempt {attempt + 1}/{retries}")
            print(f"[DEBUG] URL: {_BASE}")
            print(f"[DEBUG] Params: {json.dumps(params, indent=2)}")
            
            r = requests.get(_BASE, params=params, timeout=_TIMEOUT)
            
            print(f"[DEBUG] Status Code: {r.status_code}")
            print(f"[DEBUG] Response Headers: {dict(r.headers)}")
            
            if r.status_code == 429:
                # Rate limited - use exponential backoff with longer delays
                delay = (2 ** attempt) * 5  # 5s, 10s, 20s, 40s, 80s
                print(f"[DEBUG] ⚠️  RATE LIMITED (429)")
                print(f"[DEBUG] Backing off for {delay} seconds (attempt {attempt + 1}/{retries})")
                print(f"[DEBUG] TIP: Set GOOGLE_BOOKS_API_KEY env var for 1M requests/day")
                time.sleep(delay)
                continue
            
            r.raise_for_status()
            data = r.json()
            
            print(f"[DEBUG] ✓ Success! Response received")
            print(f"[DEBUG] Full Response:")
            print(json.dumps(data, indent=2))
            
            return data
        except requests.RequestException as e:
            print(f"[ERROR] Google Books API request failed: {e}")
            if 'r' in locals():
                print(f"[DEBUG] Response text: {r.text[:500]}")
            if attempt == retries - 1:
                print(f"[ERROR] Failed after {retries} retries")
    
    print(f"[ERROR] Giving up after {retries} attempts")
    return None


def search_title(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Search Google Books for `query`.
    Returns (canonical_title, google_volume_id) or (None, None).
    """
    print(f"\n[SEARCH_TITLE] Query: '{query}'")
    data = _get({"q": query, "maxResults": 1, "langRestrict": "en"})
    
    if not data:
        print("[SEARCH_TITLE] No data returned from API")
        return None, None
    
    total_items = data.get("totalItems", 0)
    print(f"[SEARCH_TITLE] Total items found: {total_items}")
    
    if total_items == 0:
        print("[SEARCH_TITLE] No results found")
        return None, None

    items = data.get("items", [])
    print(f"[SEARCH_TITLE] Number of items in response: {len(items)}")
    
    if not items:
        print("[SEARCH_TITLE] Items list is empty")
        return None, None

    item = items[0]
    print(f"[SEARCH_TITLE] First item ID: {item.get('id')}")
    print(f"[SEARCH_TITLE] First item (truncated): {json.dumps(item, indent=2)[:500]}...")
    
    info = item.get("volumeInfo", {})
    title = info.get("title")
    vid = item.get("id")
    
    print(f"[SEARCH_TITLE] Extracted title: '{title}'")
    print(f"[SEARCH_TITLE] Extracted volume ID: '{vid}'")
    
    return title, vid


def fetch_isbn(title: str) -> Dict[str, str]:
    """
    Given a title, fetch ISBN-10 and ISBN-13 from Google Books.
    Returns {"isbn_10": "...", "isbn_13": "..."} with empty strings on miss.
    """
    print(f"\n[FETCH_ISBN] Title: '{title}'")
    data = _get({"q": f'intitle:"{title}"', "maxResults": 1})
    
    result = {"isbn_10": "", "isbn_13": ""}
    
    if not data:
        print("[FETCH_ISBN] No data returned from API")
        return result
    
    total_items = data.get("totalItems", 0)
    print(f"[FETCH_ISBN] Total items found: {total_items}")
    
    if total_items == 0:
        print("[FETCH_ISBN] No results found for ISBN search")
        return result

    items = data.get("items", [])
    if not items:
        print("[FETCH_ISBN] Items list is empty")
        return result

    info = items[0].get("volumeInfo", {})
    print(f"[FETCH_ISBN] Volume info found")
    
    identifiers = info.get("industryIdentifiers", [])
    print(f"[FETCH_ISBN] Industry identifiers found: {len(identifiers)}")
    print(f"[FETCH_ISBN] Full identifiers: {json.dumps(identifiers, indent=2)}")
    
    for id_entry in identifiers:
        t = id_entry.get("type", "")
        v = id_entry.get("identifier", "")
        print(f"[FETCH_ISBN] Processing identifier - Type: {t}, Value: {v}")
        
        if t == "ISBN_10":
            result["isbn_10"] = v
            print(f"[FETCH_ISBN] Set ISBN-10: {v}")
        elif t == "ISBN_13":
            result["isbn_13"] = v
            print(f"[FETCH_ISBN] Set ISBN-13: {v}")

    print(f"[FETCH_ISBN] Final result: {result}")
    return result
