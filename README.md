# 🔍 Site Reverse Image Search

A powerful, clean tool to find similar images **on any website** using both traditional visual matching and AI (CLIP) semantic search.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- ✅ Upload image or paste image URL
- ✅ Search within **any website**
- ✅ **Pagination support** (scrape multiple pages)
- ✅ Two matching modes:
  - **pHash** — Fast visual similarity
  - **CLIP** — AI-powered semantic understanding (recommended)
- ✅ Clean, modern two-tab interface
- ✅ Auto-scraping when searching

- Upload image or paste image URL
- Search within any website (with pagination support)
- Two matching modes:
  - Fast pHash (visual similarity)
  - Powerful CLIP (semantic / AI understanding) — recommended
- Clean two-tab interface
- Auto-scraping when searching

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

```
thumbnail_matcher_v2/
├── app.py              # Main Streamlit app
├── requirements.txt
├── README.md
├── core/
│   ├── scraper.py      # Web scraping + pagination
│   └── matcher.py      # pHash + CLIP matching
└── ui/                 # (Reserved for future UI components)
```

## Notes

- First time using CLIP mode will download ~600MB model.
- For very large sites, start with pHash mode or limit the number of images.
- Works best on sites with static HTML image tags.

Built as a clean rewrite of the original tool.
