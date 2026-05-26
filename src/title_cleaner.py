"""
title_cleaner.py — Converts raw filename stems into readable English titles.

Two strategies:
  1. Heuristic: split camelCase / underscores / hyphens, title-case, strip numbers.
  2. LLM (Ollama via LangChain): sends the raw stem to a local model for a clean title.
  
Also includes validation to verify Google Books results match the original filename.
"""

import re
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

_PROMPT = PromptTemplate(
    input_variables=["stem"],
    template=(
        "You are a librarian. Given a raw filename stem (spaces removed, possibly "
        "camelCase or lowercase run-together words), return ONLY the proper English "
        "book title — nothing else, no punctuation, no explanations.\n\n"
        "Filename stem: {stem}\n"
        "Book title:"
    ),
)

_VALIDATION_PROMPT = PromptTemplate(
    input_variables=["filename", "google_result"],
    template=(
        "You are a librarian verifying if a Google Books search result matches a filename.\n\n"
        "Original filename: {filename}\n"
        "Google Books result: {google_result}\n\n"
        "Do these refer to the SAME book? Consider:\n"
        "- Same title (ignoring editions like '2nd Ed', '4th Ed')\n"
        "- Same authors\n"
        "- Same general subject\n\n"
        "Reply with ONLY 'YES' or 'NO' and a confidence score 0-100.\n"
        "Example: 'YES 95' or 'NO 30'\n\n"
        "Answer:"
    ),
)


def _heuristic_clean(stem: str) -> str:
    """Best-effort heuristic title extraction."""
    # Replace separators
    s = re.sub(r"[_\-]+", " ", stem)
    # Split camelCase
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    # Remove leading/trailing digits and noise
    s = re.sub(r"^\d+\s*|\s*\d+$", "", s)
    s = s.strip()
    # If already has spaces, just title-case
    if " " in s:
        return s.title()
    # Run-together lowercase — insert spaces before common word boundaries
    # Use a known common-word split via regex lookahead (greedy left-to-right)
    # Fallback: just title-case the whole thing so Google Books gets a shot
    return s.title()


def _is_likely_non_english(text: str) -> bool:
    """Return True if the stem contains non-ASCII characters (heuristic)."""
    return not all(ord(c) < 128 for c in text)


def _is_meaningless(stem: str) -> bool:
    """Return True if the stem looks like a generic/unnamed file."""
    cleaned = re.sub(r"[^a-zA-Z]", "", stem).lower()
    meaningless = {"file", "book", "document", "untitled", "unknown", "ebook", "copy"}
    return cleaned in meaningless or len(cleaned) <= 3


def build_cleaner(model: str = "llama3.2:3b", use_llm: bool = True):
    """
    Returns a callable `clean(stem) -> (title, failure_reason)`.
    `failure_reason` is an empty string on success.
    """
    chain = None
    if use_llm:
        try:
            llm = OllamaLLM(model=model, temperature=0)
            chain = _PROMPT | llm
        except Exception as e:
            print(f"[WARN] Could not connect to Ollama ({e}). Falling back to heuristic.")

    def clean(stem: str):
        # Non-English check
        if _is_likely_non_english(stem):
            return "", "Non-English filename — cannot resolve title"

        # Meaningless name check
        if _is_meaningless(stem):
            return "", f"Filename '{stem}' is too generic to identify"

        # LLM path
        if chain is not None:
            try:
                result = chain.invoke({"stem": stem}).strip()
                # Sanity check: LLM returned something reasonable
                if result and len(result) > 2 and result.lower() not in {"unknown", "n/a", "none"}:
                    return result, ""
            except Exception as e:
                print(f"[WARN] LLM call failed for '{stem}': {e}")

        # Heuristic fallback
        title = _heuristic_clean(stem)
        return title, ""

    return clean


def build_validator(model: str = "mistral:7b"):
    """
    Returns a validator function that compares filename with Google Books result.
    Uses a larger, more capable model (default: mistral:7b) for better accuracy.
    
    Returns: (is_match: bool, confidence: int)
    """
    try:
        llm = OllamaLLM(model=model, temperature=0)
        chain = _VALIDATION_PROMPT | llm
    except Exception as e:
        print(f"[WARN] Validation model '{model}' not available: {e}")
        chain = None

    def validate(filename: str, google_result: str) -> tuple[bool, int]:
        """
        Validates if google_result matches the book in filename.
        Returns (is_match, confidence_0_to_100)
        """
        if chain is None:
            # Fallback: simple substring matching
            filename_lower = filename.lower()
            result_lower = google_result.lower()
            # Check if key words overlap
            words = set(filename_lower.split())
            result_words = set(result_lower.split())
            overlap = len(words & result_words) / max(len(words), 1)
            is_match = overlap > 0.5
            confidence = int(overlap * 100)
            return is_match, confidence

        try:
            response = chain.invoke({
                "filename": filename,
                "google_result": google_result
            }).strip()
            
            # Parse response: "YES 95" or "NO 30"
            parts = response.split()
            if len(parts) >= 2:
                is_match = parts[0].upper() == "YES"
                try:
                    confidence = int(parts[1])
                except ValueError:
                    confidence = 50
            else:
                # Fallback parsing
                is_match = "yes" in response.lower()
                confidence = 50
            
            return is_match, confidence
        except Exception as e:
            print(f"[WARN] Validation failed: {e}")
            return True, 50  # Default to accepting on error

    return validate
