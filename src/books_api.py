"""
books_api.py — Wraps the Google Books API.

Two operations:
  1. search_title(query) -> best matching volume title
  2. fetch_isbn(title)   -> {"isbn10": ..., "isbn13": ...}

No API key required for basic volume searches (free tier, 1000 req/day).
"""

import time
import requests
from typing import Dict, Optional, Tuple

_BASE = "https://www.googleapis.com/books/v1/volumes"
_RETRY_DELAY = 1.0  # seconds between retries
_TIMEOUT = 8


def _get(params: dict, retries: int = 3) -> Optional[dict]:
    for attempt in range(retries):
        try:
            r = requests.get(_BASE, params=params, timeout=_TIMEOUT)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt == retries - 1:
                print(f"[ERROR] Google Books API: {e}")
    return None


def search_title(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Search Google Books for `query`.
    Returns (canonical_title, google_volume_id) or (None, None).
    """
    data = _get({"q": query, "maxResults": 1, "langRestrict": "en"})
    if not data or data.get("totalItems", 0) == 0:
        return None, None

    item = data["items"][0]
    info = item.get("volumeInfo", {})
    title = info.get("title")
    vid = item.get("id")
    return title, vid


def fetch_isbn(title: str) -> Dict[str, str]:
    """
    Given a title, fetch ISBN-10 and ISBN-13 from Google Books.
    Returns {"isbn10": "...", "isbn13": "..."} with empty strings on miss.
    """
    data = _get({"q": f'intitle:"{title}"', "maxResults": 1})
    result = {"isbn10": "", "isbn13": ""}
    if not data or data.get("totalItems", 0) == 0:
        return result

    info = data["items"][0].get("volumeInfo", {})
    for id_entry in info.get("industryIdentifiers", []):
        t = id_entry.get("type", "")
        v = id_entry.get("identifier", "")
        if t == "ISBN_10":
            result["isbn10"] = v
        elif t == "ISBN_13":
            result["isbn13"] = v

    return result
