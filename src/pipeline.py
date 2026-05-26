"""
pipeline.py — Orchestrates the full BookShelf agent workflow.

Steps:
  1. Scan books directory  (scanner.py)
  2. Clean filename → readable title  (title_cleaner.py)
  3. Validate title via Google Books  (books_api.py)
  4. Fetch ISBN-10 and ISBN-13  (books_api.py)
  5. Write results to Excel  (excel_writer.py)
"""

import time
from typing import List, Dict

from src.scanner import scan_books_dir
from src.title_cleaner import build_cleaner
from src.books_api import search_title, fetch_isbn, get_api_call_count
from src.excel_writer import write_excel


def _process_record(rec: dict, clean_fn) -> dict:
    """
    Enrich a single file record with resolved name and ISBN data.
    Returns a flat dict matching Excel columns.
    """
    stem = rec["stem"]
    file_type = rec["file_type"]

    # Step 1: clean filename -> candidate title
    candidate_title, fail_reason = clean_fn(stem)

    if fail_reason:
        return {
            "name": rec["raw_filename"],
            "file_type": file_type,
            "isbn_10": "",
            "isbn_13": "",
            "reason_for_failure": fail_reason,
        }

    # Step 2: verify + get canonical title from Google Books
    canonical_title, _, found = search_title(candidate_title)
    time.sleep(1.0)  # rate-limit between search_title calls
    
    if not canonical_title:
        return {
            "name": candidate_title or rec["raw_filename"],
            "file_type": file_type,
            "isbn_10": "",
            "isbn_13": "",
            "reason_for_failure": f"Google Books: no results for '{candidate_title}'",
        }

    # Step 3: fetch ISBNs
    time.sleep(1.0)  # rate-limit before ISBN search
    isbns = fetch_isbn(canonical_title)
    time.sleep(1.0)  # gentle rate-limit after ISBN search

    return {
        "name": canonical_title,
        "file_type": file_type,
        "isbn_10": isbns.get("isbn_10", ""),
        "isbn_13": isbns.get("isbn_13", ""),
        "reason_for_failure": "",
    }


def run_pipeline(
    books_dir: str = "books",
    output_path: str = "bookshelf.xlsx",
    model: str = "llama3.2:3b",
    use_llm: bool = True,
) -> bool:
    print(f"\n{'='*60}")
    print("  📚 BookShelf Cataloger")
    print(f"{'='*60}")
    print(f"  Directory  : {books_dir}")
    print(f"  Output     : {output_path}")
    print(f"  Mode       : {model if use_llm else 'Heuristic Only'}")
    print(f"{'='*60}\n")

    # Scan
    try:
        files = scan_books_dir(books_dir)
    except FileNotFoundError as e:
        print(f"  ✗ Error: {e}\n")
        return False

    if not files:
        print("  ⚠️  No supported book files found.\n")
        return False

    print(f"  ✓ Found {len(files)} book(s)\n")
    print(f"{'─'*60}\n")

    # Build cleaner once
    clean_fn = build_cleaner(model=model, use_llm=use_llm)

    # Process each file
    results: List[Dict] = []
    for i, rec in enumerate(files, 1):
        print(f"  [{i:02d}/{len(files):02d}] {rec['raw_filename']:<40} ", end="", flush=True)
        enriched = _process_record(rec, clean_fn)
        status = "✓" if not enriched["reason_for_failure"] else "✗"
        name_display = enriched["name"][:40] if enriched["name"] else "Unknown"
        print(f"{status}")
        if enriched["reason_for_failure"]:
            print(f"         → {enriched['reason_for_failure']}")
        results.append(enriched)

    # Write Excel
    print(f"\n{'─'*60}\n")
    write_excel(results, output_path)

    ok = sum(1 for r in results if not r["reason_for_failure"])
    api_calls = get_api_call_count()
    print(f"\n  ✓ Complete: {ok}/{len(results)} books cataloged")
    print(f"  ✓ API Calls: {api_calls} fetches to Google Books")
    print(f"  ✓ Saved to: {output_path}\n")
    return True
