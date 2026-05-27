"""
pipeline.py — Orchestrates the full BookShelf agent workflow.

Steps:
  1. Scan books directory  (scanner.py)
  2. Clean filename → readable title  (title_cleaner.py)
  3. Validate title via Google Books  (books_api.py)
  4. AI-validate result matches original filename (title_cleaner.py)
  5. Fetch ISBN-10 and ISBN-13  (books_api.py)
  6. Write results to Excel  (excel_writer.py)

Features:
  - Skip files already processed (resume support)
  - Incremental saves after each book (crash-proof)
"""

import time
from typing import List, Dict

from src.scanner import scan_books_dir
from src.title_cleaner import build_cleaner, build_validator
from src.books_api import search_candidates, fetch_isbn, get_api_call_count
from src.excel_writer import load_processed_files, append_record_to_excel, write_excel


def _process_record(rec: dict, clean_fn, validate_fn) -> dict:
    """
    Enrich a single file record with resolved name and ISBN data.
    Returns a flat dict matching Excel columns.
    """
    stem = rec["stem"]
    raw_filename = rec["raw_filename"]
    file_type = rec["file_type"]

    # Step 1: clean filename -> candidate title
    candidate_title, fail_reason = clean_fn(stem)

    if fail_reason:
        return {
            "name": raw_filename,
            "file_type": file_type,
            "isbn_10": "",
            "isbn_13": "",
            "reason_for_failure": fail_reason,
        }

    # Step 2: get multiple candidates from Google Books
    candidates = search_candidates(candidate_title, max_results=5)
    time.sleep(1.0)  # rate-limit between search calls

    if not candidates:
        return {
            "real_name": raw_filename,
            "status": "Failed",
            "name": candidate_title or raw_filename,
            "author": "",
            "description": "",
            "file_type": file_type,
            "isbn_10": "",
            "isbn_13": "",
            "reason_for_failure": f"Google Books: no results for '{candidate_title}'",
        }

    # Step 3: ask validator to score each candidate and pick the best
    best = None
    best_conf = -1
    for idx, cand in enumerate(candidates):
        # Build a compact text representation for validation
        google_text = f"Title: {cand.get('title','')}\nAuthors: {cand.get('authors','')}\nDescription: {cand.get('description','')[:300]}"
        is_match, confidence = validate_fn(raw_filename, google_text)
        # Print a concise per-candidate summary
        print(f"         Candidate {idx+1}/{len(candidates)}: {cand.get('title','')[:60]} → {confidence}%")
        if confidence > best_conf:
            best_conf = confidence
            best = (cand, is_match, confidence)

    # If the best candidate is not confident enough, mark as failed
    if best is None or best_conf < 70:
        confidence_str = f"{best_conf}%" if best_conf >= 0 else "unknown"
        chosen_title = best[0].get('title') if best else (candidate_title or raw_filename)
        return {
            "real_name": raw_filename,
            "status": "Failed",
            "name": chosen_title,
            "author": best[0].get('authors','') if best else "",
            "description": best[0].get('description','') if best else "",
            "file_type": file_type,
            "isbn_10": "",
            "isbn_13": "",
            "reason_for_failure": f"Result validation failed (confidence: {confidence_str}) - likely different book",
        }

    # Use the selected candidate
    selected, _, conf = best
    # Step 4: fetch ISBNs (extract directly from the selected item)
    time.sleep(1.0)  # rate-limit before ISBN extraction
    isbns = fetch_isbn(selected)
    time.sleep(0.5)

    return {
        "real_name": raw_filename,
        "status": "Found",
        "name": selected.get("title") or candidate_title,
        "author": selected.get("authors", ""),
        "description": selected.get("description", ""),
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
    validation_model: str = "mistral:7b",
) -> bool:
    print(f"\n{'='*60}")
    print("  📚 BookShelf Cataloger")
    print(f"{'='*60}")
    print(f"  Directory  : {books_dir}")
    print(f"  Output     : {output_path}")
    print(f"  Mode       : {model if use_llm else 'Heuristic Only'}")
    print(f"  Validator  : {validation_model}")
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

    # Load already processed files to skip them
    processed = load_processed_files(output_path)
    unprocessed = [f for f in files if f['raw_filename'] not in processed]
    
    print(f"  ✓ Found {len(files)} book(s)")
    if processed:
        print(f"  ⏭️  {len(processed)} already processed, {len(unprocessed)} remaining")
    print(f"\n{'─'*60}\n")

    if not unprocessed:
        print("  ✓ All books already processed!\n")
        return True

    # Build cleaner and validator
    clean_fn = build_cleaner(model=model, use_llm=use_llm)
    validate_fn = build_validator(model=validation_model)

    # Process each file and save incrementally
    processed_count = 0
    for i, rec in enumerate(unprocessed, 1):
        print(f"  [{i:02d}/{len(unprocessed):02d}] {rec['raw_filename']:<40} ", end="", flush=True)
        enriched = _process_record(rec, clean_fn, validate_fn)
        status = "✓" if not enriched["reason_for_failure"] else "✗"
        print(f"{status}")
        if enriched["reason_for_failure"]:
            print(f"         → {enriched['reason_for_failure']}")
        
        # Save immediately after each record
        append_record_to_excel(enriched, output_path)
        processed_count += 1

    # Print summary
    print(f"\n{'─'*60}\n")
    api_calls = get_api_call_count()
    total_in_catalog = len(processed) + processed_count
    print(f"  ✓ Session: Processed {processed_count} new books")
    print(f"  ✓ Total in catalog: {total_in_catalog} books")
    print(f"  ✓ API Calls: {api_calls} fetches to Google Books")
    print(f"  ✓ Saved to: {output_path}\n")
    return True
