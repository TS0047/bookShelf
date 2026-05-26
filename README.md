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

## Sample Output

```
============================================================
  📚 BookShelf Cataloger
============================================================
  Directory  : books
  Output     : bookshelf.xlsx
  Mode       : llama3.2:3b
============================================================

  ✓ Found 4 book(s)

──────────────────────────────────────────────────────────

  [01/04] harrypotter.txt                          ✓
      📖 Found: 'Harry Potter and the Philosopher\'s Stone'
      📚 ISBNs: ISBN-10: 0747532699 | ISBN-13: 978-0747532690

  [02/04] little-red-riding-hood.txt               ✓
      📖 Found: 'Little Red Riding Hood'
      📚 ISBNs: ISBN-10: — | ISBN-13: 978-0486401195

  [03/04] mobyDick.txt                             ✓
      📖 Found: 'Moby-Dick; or, The Whale'
      📚 ISBNs: ISBN-10: 0486432513 | ISBN-13: 978-0486432519

  [04/04] war-of-the-worlds.txt                    ✓
      📖 Found: 'The War of the Worlds'
      📚 ISBNs: ISBN-10: 0486402753 | ISBN-13: 978-0486402758

──────────────────────────────────────────────────────────

  ✓ Complete: 4/4 books cataloged
  ✓ API Calls: 8 fetches to Google Books
  ✓ Saved to: bookshelf.xlsx

```

The output shows:
- **File scanning progress** - Which file is being processed
- **Google Books result** - The canonical title found (📖)
- **ISBN details** - Both ISBN-10 and ISBN-13 (📚), or dashes if not available
- **API statistics** - Total number of Google Books API calls made
- **Completion summary** - Success count and output file location

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

### 3. (Optional) Google Books API Key

**No API key is required**, but it's recommended for production use:
- **Without API key**: ~1,000 requests/day (free tier, may hit rate limits)
- **With API key**: 1,000,000 requests/day (requires Google Cloud account)

To enable API key authentication:

1. Get an API key from [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable Google Books API
   - Create an API Key credential
2. Set the environment variable:

```powershell
# Windows PowerShell
$env:GOOGLE_BOOKS_API_KEY = "your_api_key_here"
python main.py
```

```bash
# Linux/Mac
export GOOGLE_BOOKS_API_KEY="your_api_key_here"
python main.py
```

### 4. Add your books

Drop any `.pdf`, `.epub`, `.mobi`, `.txt`, or `.djvu` files into the `books/` folder.

---

## Usage

```bash
# Default run (books/ folder, llama3.2:3b cleaner, mistral:7b validator)
python main.py

# Custom models
python main.py --model qwen2.5:7b --validation-model deepseek-r1:7b

# Skip LLM, use heuristic title parsing only (no validation)
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
| `--validation-model` | `mistral:7b` | Ollama model for result validation (see table below) |
| `--no-llm` | off | Use heuristic only (no LLM, no validation) |

### Available Models for Validation

Use `--validation-model` with any of these larger, more accurate models:

| Model | Size | Best For | Speed |
|-------|------|----------|-------|
| `mistral:7b` | 4.4 GB | **Recommended** - Best balance | Medium |
| `qwen2.5:7b` | 4.7 GB | Good accuracy, slightly slower | Medium-Slow |
| `deepseek-r1:7b` | 4.7 GB | Best accuracy, slowest | Slow |
| `llava:latest` | 4.7 GB | Uses vision (not recommended for text) | Medium |

Example with different validator:
```bash
python main.py --validation-model qwen2.5:7b
```

---

## How It Works: AI-Powered Validation

### The Problem
Google Books doesn't always return the exact book you need:
- "Operating System Concepts" → finds "Operating System Concepts, 10e **Abridged** Print Companion" (wrong edition)
- "Data Structures in C++" → finds related but different book (no ISBN data)

### The Solution
After Google Books returns a result, a **larger AI model** validates if it actually matches your original filename:

```
File: Abraham-Silberschatz-Operating-System-Concepts-10th-2018.pdf
  ↓
Cleaned title: "Operating System Concepts"
  ↓
Google Books: "Operating System Concepts, 10e Abridged Print Companion"
  ↓
AI Validator: "NO 30" → Only 30% confidence match
  ↓
Result: ✗ REJECTED (too low confidence)
```

The validator uses one of the larger, more capable models to understand context and similarity, unlike simple string matching.

### Available Validators
Choose based on your accuracy needs vs. speed:

- `mistral:7b` (default) - Fast, very accurate, **recommended**
- `qwen2.5:7b` - Slightly slower, excellent accuracy
- `deepseek-r1:7b` - Slowest, best reasoning and accuracy

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

## Troubleshooting

### HTTP 429 "Too Many Requests" from Google Books API

**Symptoms**: Books fail to resolve with "no results" messages

**Causes**:
- Using free tier without API key (limited to ~1,000 requests/day)
- Too many requests in a short time

**Solutions**:
1. **Add an API key** (recommended)
   - Follow the steps in "Google Books API Key" section above
   - This increases limit to 1,000,000 requests/day

2. **Use `--no-llm` flag** to reduce API calls
   ```bash
   python main.py --no-llm
   ```

3. **Wait and retry** - The app automatically retries with exponential backoff

### ISBN numbers not appearing in Excel

**Check**: Look at the Excel output
- If ISBN columns are empty, the books weren't found in Google Books
- Some older or obscure books may not have ISBN data available

---

## Recent Fixes & Improvements

- **v1.4**: Added AI-powered result validation to catch incorrect book matches
  - Uses larger models (mistral:7b, qwen2.5:7b, deepseek-r1:7b) for verification
  - Confidence threshold: 70% - rejects low-confidence matches
  - Solves issues with wrong editions being returned
- **v1.3**: Added detailed API fetch information (book names, ISBN numbers, fetch count)
- **v1.2**: Removed verbose debug output, cleaner terminal display
- **v1.1**: Fixed ISBN key names (`isbn_10`, `isbn_13`) not being saved to Excel
- **v1.1**: Improved Google Books API retry logic with exponential backoff
- **v1.1**: Added optional API key support via `GOOGLE_BOOKS_API_KEY` env variable

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
