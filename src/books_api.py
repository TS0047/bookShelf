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
from typing import Dict, Optional, Tuple, List, Union

_BASE = "https://www.googleapis.com/books/v1/volumes"
_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")
_TIMEOUT = 8

# Debug: Show API key status
if _API_KEY:
    print(f"✓ Google Books API key loaded (first 10 chars: {_API_KEY[:10]}...)")
else:
    print("⚠️  No Google Books API key found. Rate limits will be lower.")

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


def search_candidates(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search Google Books for `query` and return up to `max_results` candidate items.
    Each candidate is a dict with keys: title, id, authors (string), description (string), raw (original item).
    """
    data = _get({"q": query, "maxResults": max_results, "langRestrict": "en"})

    if not data or data.get("totalItems", 0) == 0:
        return []

    items = data.get("items", [])
    candidates: List[Dict] = []
    for item in items[:max_results]:
        info = item.get("volumeInfo", {})
        title = info.get("title")
        authors = info.get("authors") or []
        authors_str = ", ".join(authors) if isinstance(authors, (list, tuple)) else (authors or "")
        description = info.get("description") or ""
        candidates.append({
            "title": title,
            "id": item.get("id"),
            "authors": authors_str,
            "description": description,
            "raw": item,
        })

    return candidates


def search_title(query: str) -> Tuple[Optional[str], Optional[str], bool]:
    """Backward-compatible helper: returns the first candidate (title,id,found)."""
    candidates = search_candidates(query, max_results=1)
    if not candidates:
        return None, None, False
    c = candidates[0]
    if c["title"]:
        print(f"      📖 Found: '{c['title']}'")
        return c["title"], c["id"], True
    return None, None, False


def fetch_isbn(item_or_title: Union[str, Dict]) -> Dict[str, str]:
    """
    Given either a Google Books item (dict) or a title string, return ISBN-10 and ISBN-13.
    Returns {"isbn_10": "...", "isbn_13": "..."}.
    If an item dict is provided, extracts identifiers directly (no extra API call).
    """
    result = {"isbn_10": "", "isbn_13": ""}

    # If we received a dict (candidate item), extract identifiers from it
    if isinstance(item_or_title, dict):
        info = item_or_title.get("raw", item_or_title).get("volumeInfo", {})
        identifiers = info.get("industryIdentifiers", [])
        for id_entry in identifiers:
            t = id_entry.get("type", "")
            v = id_entry.get("identifier", "")
            if t == "ISBN_10":
                result["isbn_10"] = v
            elif t == "ISBN_13":
                result["isbn_13"] = v
        isbn10_str = f"ISBN-10: {result['isbn_10']}" if result['isbn_10'] else "—"
        isbn13_str = f"ISBN-13: {result['isbn_13']}" if result['isbn_13'] else "—"
        print(f"      📚 ISBNs: {isbn10_str} | {isbn13_str}")
        return result

    # Otherwise fall back to searching by title (legacy behavior)
    title = str(item_or_title)
    data = _get({"q": f'intitle:"{title}"', "maxResults": 1})

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

    isbn10_str = f"ISBN-10: {result['isbn_10']}" if result['isbn_10'] else "—"
    isbn13_str = f"ISBN-13: {result['isbn_13']}" if result['isbn_13'] else "—"
    print(f"      📚 ISBNs: {isbn10_str} | {isbn13_str}")
    return result
