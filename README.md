# BookShelf Agent

An AI-powered local agent that scans your book folder, resolves file names into real book titles using a local LLM (Ollama), fetches ISBN numbers via the Google Books API, and outputs a clean Excel catalog.

---

## Features

| Step | What happens |
|------|-------------|
| **Scan** | Reads all `.pdf`, `.epub`, `.mobi`, `.txt`, `.djvu` files from your books folder |
| **Title Clean** | Converts `waroftheworlds.epub` → `The War of the Worlds` using heuristics + Ollama LLM |
| **Google Books** | Validates the title and gets the canonical name |
| **ISBN Fetch** | Retrieves ISBN-10 and ISBN-13 from the same API |
| **Excel Output** | Writes a formatted `bookshelf.xlsx` with failure reasons for unresolvable files |

---

## Project Structure

```
bookshelf/
├── main.py               # Entry point / CLI
├── requirements.txt
├── books/                # Drop your book files here
└── src/
    ├── scanner.py        # Directory walker
    ├── title_cleaner.py  # Heuristic + LLM title resolver
    ├── books_api.py      # Google Books API client
    ├── excel_writer.py   # openpyxl Excel builder
    └── pipeline.py       # Orchestrates all steps
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Install & run Ollama

```bash
# Install Ollama: https://ollama.com
ollama pull llama3.2:3b        # lightweight, fast
# or
ollama pull qwen2.5-coder:7b   # better reasoning
```

> **No API key needed.** Google Books basic search is free (1 000 req/day).  
> For higher limits, add `&key=YOUR_KEY` in `src/books_api.py`.

### 3. Add your books

Drop any `.pdf`, `.epub`, `.mobi`, `.txt`, or `.djvu` files into the `books/` folder.

---

## Usage

```bash
# Default run (books/ folder, llama3.2:3b, output: bookshelf.xlsx)
python main.py

# Custom folder and model
python main.py --books-dir /path/to/library --model qwen2.5-coder:7b

# Skip LLM, use heuristic title parsing only
python main.py --no-llm

# Custom output path
python main.py --output my_catalog.xlsx
```

### CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--books-dir` | `books` | Path to folder with book files |
| `--output` | `bookshelf.xlsx` | Output Excel file name |
| `--model` | `llama3.2:3b` | Ollama model for title cleaning |
| `--no-llm` | off | Use heuristic only (no Ollama needed) |

---

## Excel Output

| Column | Description |
|--------|-------------|
| **Name** | Resolved canonical book title |
| **File Type** | `pdf`, `epub`, etc. |
| **ISBN 10** | 10-digit ISBN (if found) |
| **ISBN 13** | 13-digit ISBN (if found) |
| **Reason For Failure** | Why the book couldn't be resolved (blank = success) |

Rows with failures are highlighted in red. Every other row alternates for readability.

---

## Failure Cases

The agent flags and explains these cases instead of crashing:

- **Non-English filename** — contains non-ASCII characters (e.g., `द्रोण.pdf`)
- **Generic filename** — `file1.epub`, `book.pdf`, `untitled.pdf`
- **Not found in Google Books** — title was cleaned but API returned no match

---

## Models Tested

Works with any Ollama model. Recommended for this task:

| Model | Speed | Quality |
|-------|-------|---------|
| `llama3.2:3b` | Fast | Good |
| `mistral:7b` | Medium | Better |
| `qwen2.5-coder:7b` | Medium | Best for edge cases |

---

## Notes

- Google Books API has a **1 000 free requests/day** limit without a key.
- The agent adds a 300 ms delay between requests to avoid rate-limiting.
- If Ollama is not running, the agent automatically falls back to heuristic title cleaning.
