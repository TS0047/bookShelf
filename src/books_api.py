"""
books_api.py — Wraps the Google Books API.

Two operations:
  1. search_title(query) -> best matching volume title
  2. fetch_isbn(title)   -> {"isbn_10": ..., "isbn_13": ...}

Optional API key for higher rate limits (set GOOGLE_BOOKS_API_KEY env var).
"""

import time
import requests
import os
from typing import Dict, Optional, Tuple

_BASE = "https://www.googleapis.com/books/v1/volumes"
_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")
_TIMEOUT = 8

# Tracking API calls
_api_call_count = 0


def _get(params: dict, retries: int = 5) -> Optional[dict]:
    """
    Make a request to Google Books API with exponential backoff on rate limiting.
    """
    global _api_call_count
    _api_call_count += 1
    
    if _API_KEY:
        params["key"] = _API_KEY
    
    for attempt in range(retries):
        try:
            r = requests.get(_BASE, params=params, timeout=_TIMEOUT)
            
            if r.status_code == 429:
                # Rate limited - use exponential backoff
                delay = (2 ** attempt) * 5  # 5s, 10s, 20s, 40s, 80s
                print(f"      ⚠️  Rate limited (429). Retry in {delay}s...")
                time.sleep(delay)
                continue
            
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt == retries - 1:
                print(f"      ✗ API Error: {e}")
    
    return None


def get_api_call_count() -> int:
    """Returns total number of API calls made."""
    return _api_call_count


def search_title(query: str) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Search Google Books for `query`.
    Returns (canonical_title, google_volume_id, found) or (None, None, False).
    """
    data = _get({"q": query, "maxResults": 1, "langRestrict": "en"})
    
    if not data or data.get("totalItems", 0) == 0:
        return None, None, False

    items = data.get("items", [])
    if not items:
        return None, None, False

    item = items[0]
    info = item.get("volumeInfo", {})
    title = info.get("title")
    vid = item.get("id")
    
    # Show info about the fetch
    print(f"      📖 Found: '{title}'")
    
    return title, vid, True


def fetch_isbn(title: str) -> Dict[str, str]:
    """
    Given a title, fetch ISBN-10 and ISBN-13 from Google Books.
    Returns {"isbn_10": "...", "isbn_13": "..."} with empty strings on miss.
    """
    data = _get({"q": f'intitle:"{title}"', "maxResults": 1})
    
    result = {"isbn_10": "", "isbn_13": ""}
    
    if not data or data.get("totalItems", 0) == 0:
        return result

    items = data.get("items", [])
    if not items:
        return result

    info = items[0].get("volumeInfo", {})
    identifiers = info.get("industryIdentifiers", [])
    
    for id_entry in identifiers:
        t = id_entry.get("type", "")
        v = id_entry.get("identifier", "")
        
        if t == "ISBN_10":
            result["isbn_10"] = v
        elif t == "ISBN_13":
            result["isbn_13"] = v

    # Show info about the fetch
    isbn10_str = f"ISBN-10: {result['isbn_10']}" if result['isbn_10'] else "—"
    isbn13_str = f"ISBN-13: {result['isbn_13']}" if result['isbn_13'] else "—"
    print(f"      📚 ISBNs: {isbn10_str} | {isbn13_str}")

    return result
