# Run Web App — YouTube Top Videos

## Objective

Start the YouTube Top Videos web app and use it to find, browse, and export the most-viewed YouTube videos in any time period.

## Prerequisites

1. **Python** installed (invoked via `py`)
2. **YouTube Data API v3 key** — get one free at [console.cloud.google.com](https://console.cloud.google.com):
   - Create a project (or use an existing one)
   - Go to **APIs & Services > Library** → search "YouTube Data API v3" → Enable
   - Go to **APIs & Services > Credentials** → Create Credentials → API Key
   - Copy the key
3. **Set the key** in `.env`:
   ```
   YOUTUBE_API_KEY=your_actual_key_here
   ```

## Setup (first time only)

```bash
py -m pip install -r requirements.txt
py tools/db.py
```

## Start the app

```bash
py tools/server.py
```

Open http://localhost:5000 in your browser.

## Usage

1. **Pick a date range** using the date pickers or quick-select buttons (This Month, Last Year, etc.)
2. **Choose pages** — each page fetches 50 videos, costs ~101 API quota units
3. Click **Find Top Videos** — results appear in a table sorted by view count
4. **Click any row** to expand and see description, tags, and category
5. Click **Download CSV** to export all results for NotebookLM analysis

## Quota

- Free tier: **10,000 units/day** (resets at midnight Pacific Time)
- 1 page of 50 videos = ~101 units
- Results are cached in SQLite — repeating the same search costs nothing
- Quota remaining is shown on the page

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "API key not configured" | Check `.env` has `YOUTUBE_API_KEY=<key>` (no quotes) |
| "Quota exceeded" | Wait until midnight PT, or use a different API key |
| No results | Try a broader date range or check that the API key has YouTube Data API v3 enabled |
| Port 5000 in use | Set `PORT=5001` in `.env` |
