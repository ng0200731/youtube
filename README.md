# YouTube Top Videos

Find the most viewed YouTube videos in any time period. Export to CSV for analysis in NotebookLM.

## Setup

```bash
py -m pip install -r requirements.txt
```

Add your YouTube Data API v3 key to `.env`:

```
YOUTUBE_API_KEY=your_key_here
```

## Run

```bash
py tools/server.py
```

Open http://localhost:5000
