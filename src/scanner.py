"""
scanner.py — Scans a directory and returns file metadata.
Supported types: .pdf, .epub, .mobi, .txt, .djvu
"""

import os
from pathlib import Path
from typing import List, Dict

SUPPORTED_TYPES = {".pdf", ".epub", ".mobi", ".txt", ".djvu", ".azw", ".azw3"}


def scan_books_dir(directory: str) -> List[Dict]:
    """
    Walk `directory` and collect metadata for each supported book file.

    Returns a list of dicts:
        {
            "raw_filename": "waroftheworlds.epub",
            "stem": "waroftheworlds",
            "file_type": "epub",
        }
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Books directory not found: {directory}")

    records = []
    for entry in sorted(dir_path.iterdir()):
        if not entry.is_file():
            continue
        suffix = entry.suffix.lower()
        if suffix not in SUPPORTED_TYPES:
            continue
        records.append(
            {
                "raw_filename": entry.name,
                "stem": entry.stem,
                "file_type": suffix.lstrip("."),
            }
        )

    return records
