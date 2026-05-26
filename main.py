"""
BookShelf Agent - Main Entry Point
Scans a book folder, resolves real titles via Google Books API,
fetches ISBN numbers, and writes results to an Excel file.
"""

import argparse
import sys
from src.pipeline import run_pipeline


def parse_args():
    parser = argparse.ArgumentParser(description="BookShelf AI Agent")
    parser.add_argument(
        "--books-dir",
        default="books",
        help="Path to folder containing book files (default: books/)",
    )
    parser.add_argument(
        "--output",
        default="bookshelf.xlsx",
        help="Output Excel file path (default: bookshelf.xlsx)",
    )
    parser.add_argument(
        "--model",
        default="llama3.2:3b",
        help="Ollama model to use for title cleaning (default: llama3.2:3b)",
    )
    parser.add_argument(
        "--validation-model",
        default="mistral:7b",
        help="Ollama model to use for result validation (default: mistral:7b). Options: mistral:7b, qwen2.5:7b, deepseek-r1:7b",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM title cleaning; use heuristic only",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = run_pipeline(
        books_dir=args.books_dir,
        output_path=args.output,
        model=args.model,
        use_llm=not args.no_llm,
        validation_model=args.validation_model,
    )
    sys.exit(0 if success else 1)
