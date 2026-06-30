# Video Thumbnail Matcher

A lightweight, self-contained web tool that scrapes video thumbnails (or any images) from a website and finds **exact** or **visually similar** matches to an image you upload.

Built with **Streamlit** + perceptual hashing (pHash via `imagehash`).

## Features

- Scrape any public webpage for thumbnails using `<img>`, video `poster`, and social meta tags
- Smart filtering to prefer real content thumbnails over logos/icons
- **Exact match detection** (perceptual hash distance = 0)
- **Similarity search** with adjustable Hamming distance threshold
- Clean grid + table results with direct links
- Works entirely locally (your images never leave your computer)

## 🚀 Easy Start for macOS (Mac Mini / MacBook)

**Recommended method – just double-click:**

1. Download and unzip this folder.
2. Double-click the **`run.sh`** file (or right-click → Open).
3. It will automatically:
   - Create a Python virtual environment
   - Install all dependencies
   - Launch the app in your browser

> First run may take 1–2 minutes while it installs packages.

If double-click doesn't work:
- Right-click `run.sh` → **Open** (you may need to do this twice the first time for security).
- Or open Terminal, `cd` into this folder, and run: `./run.sh`

---

## Standard Installation (any OS)

```bash
# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## How to Run

```bash
streamlit run app.py
```

The tool will open in your browser at `http://localhost:8501`

## How to Use

1. **Scrape Website** tab
   - Paste any URL that contains video thumbnails (e.g. a Vimeo channel, news article with embedded videos, stock footage page, etc.)
   - Adjust max images and minimum size in the sidebar if needed
   - Click **Scrape & Analyze Thumbnails**
   - Preview the extracted thumbnails in the expander

2. **Find Matches** tab
   - Upload a reference image (PNG/JPG/WEBP)
   - Click **Find Exact & Similar Thumbnails**
   - View exact matches first, then similar ones ranked by visual similarity
   - Expand "Top 20 Ranked" for a full table view

## Tips for Best Results

- Use pages where thumbnails are present in the **initial HTML** (many modern sites load images via JavaScript — those won't be scraped).
- Good test URLs:
  - Vimeo staff picks or category pages
  - News sites with video embeds (CNN, BBC, etc.)
  - Stock video sites (Pexels, Pixabay video sections)
  - Wikipedia pages with video thumbnails
- Increase the similarity threshold (sidebar) if you want looser matches.
- Distance 0 = perceptually identical (or extremely close).
- Distance 2–8 = usually very similar (minor crops, color shifts, compression, etc.).

## Limitations

- JavaScript-rendered sites (YouTube search/results, Instagram, TikTok, etc.) often return few or no thumbnails because the tool uses simple HTTP requests (no browser rendering).
- For advanced scraping of dynamic sites you would need Playwright or Selenium (not included to keep the tool simple and dependency-light).
- This is **visual similarity**, not AI semantic search (e.g. "find other videos of the same person" works only if they look visually alike in the thumbnails).

## Technical Details

- Uses **pHash** (perceptual hash) — robust to minor edits, compression, and slight crops.
- Hamming distance on 64-bit hashes.
- All processing is local and private.

## License & Use

For personal, educational, and research purposes.  
Please respect the `robots.txt` and Terms of Service of any website you scrape.

---

Created as a practical tool for content discovery, duplicate detection, and media analysis workflows.