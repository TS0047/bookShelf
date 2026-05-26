# Google Books API Debug Report

## Problem Found: 429 Rate Limiting

**Status Code 429 (Too Many Requests)** is being returned on every single API call.

### Root Causes:

1. **No API Key / Unauthenticated Requests**
   - Free tier limit: ~1000 requests per day
   - Your code doesn't use an API key, hitting the lowest rate limit
   - Without authentication, Google aggressively rate-limits to prevent abuse

2. **Insufficient Retry Delays**
   - Original delays: 1s, 2s, 4s (not enough to recover from rate limiting)
   - New delays: 5s, 10s, 20s, 40s, 80s (exponential backoff × 5)

3. **Rapid API Calls**
   - Pipeline was calling API with only 0.3s between requests
   - Now spacing out requests by 1.0s between each call

## Solutions Implemented:

### 1. Enhanced Retry Logic (books_api.py)
- Increased retries from 3 to 5 attempts
- Exponential backoff now: `(2^attempt) × 5 seconds`
  - Attempt 1: 5 seconds
  - Attempt 2: 10 seconds
  - Attempt 3: 20 seconds
  - Attempt 4: 40 seconds
  - Attempt 5: 80 seconds

### 2. API Key Support
- Code now checks for `GOOGLE_BOOKS_API_KEY` environment variable
- If set: Authenticated requests (1,000,000 requests/day limit)
- If not set: Unauthenticated requests (~1000 requests/day)

### 3. Increased Rate Limiting (pipeline.py)
- Added 1.0s delays between each API call
- Changed from 0.3s to 1.0s spacing
- Better distribution of requests over time

### 4. Improved Debugging Output
- Shows whether API key is being used
- Clearer rate limit messages with backoff timing
- Tips for users to set API key environment variable

## How to Use with API Key:

### Option A: Set Environment Variable (Recommended)

```powershell
# Windows PowerShell
$env:GOOGLE_BOOKS_API_KEY = "your_api_key_here"
python main.py
```

### Option B: Get an API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google Books API
4. Create an API Key credential
5. Set it as `GOOGLE_BOOKS_API_KEY` environment variable

## Next Steps:

1. **Test with increased delays first** - Run without API key to see if longer waits help
2. **Get an API key** - For production use, get authenticated access (1M req/day)
3. **Monitor rate limiting** - Watch debug output for 429 responses

## Test Command:

```bash
# With default settings (unauthenticated, longer retries and delays)
python main.py --books-dir books --output bookshelf.xlsx --no-llm

# With API key set
$env:GOOGLE_BOOKS_API_KEY = "YOUR_KEY"
python main.py --books-dir books --output bookshelf.xlsx --no-llm
```
