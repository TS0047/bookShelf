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
from src.books_api import search_title, fetch_isbn
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
    canonical_title, _ = search_title(candidate_title)
    if not canonical_title:
        return {
            "name": candidate_title or rec["raw_filename"],
            "file_type": file_type,
            "isbn_10": "",
            "isbn_13": "",
            "reason_for_failure": f"Google Books: no results for '{candidate_title}'",
        }

    # Step 3: fetch ISBNs
    isbns = fetch_isbn(canonical_title)
    time.sleep(0.3)  # gentle rate-limit

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
    print(f"\n{'='*55}")
    print("  BookShelf Agent")
    print(f"{'='*55}")
    print(f"  Books dir : {books_dir}")
    print(f"  Output    : {output_path}")
    print(f"  LLM model : {model if use_llm else 'heuristic only'}")
    print(f"{'='*55}\n")

    # Scan
    try:
        files = scan_books_dir(books_dir)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return False

    if not files:
        print("[WARN] No supported book files found.")
        return False

    print(f"[SCAN] Found {len(files)} file(s).\n")

    # Build cleaner once
    clean_fn = build_cleaner(model=model, use_llm=use_llm)

    # Process each file
    results: List[Dict] = []
    for i, rec in enumerate(files, 1):
        print(f"[{i:02d}/{len(files):02d}] {rec['raw_filename']} ...", end=" ", flush=True)
        enriched = _process_record(rec, clean_fn)
        status = "✓" if not enriched["reason_for_failure"] else "✗"
        name_display = enriched["name"][:45]
        print(f"{status}  →  {name_display}")
        if enriched["reason_for_failure"]:
            print(f"         Reason: {enriched['reason_for_failure']}")
        results.append(enriched)

    # Write Excel
    print()
    write_excel(results, output_path)

    ok = sum(1 for r in results if not r["reason_for_failure"])
    print(f"\nDone. {ok}/{len(results)} books resolved successfully.\n")
    return True
