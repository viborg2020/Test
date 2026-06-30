# Video Thumbnail Matcher

A lightweight, self-contained web tool that scrapes video thumbnails (or any images) from a website and finds **exact** or **visually similar** matches to an image you upload.

Built with **Streamlit** + perceptual hashing (pHash via `imagehash`).

> **This is already a web application.** It runs in your browser.  
> Below you can deploy it for **free** so you can open it from any device with just a link (no installation needed).

## 🚀 Deploy as a Public Web App (Recommended – Works in Any Browser)

You can host this tool **for free** on Streamlit Community Cloud. Once deployed, you get a public URL like `https://yourname-video-thumbnail-matcher.streamlit.app` that you can open in any browser on any device (Mac, Windows, phone, etc.).

### One-Time Setup (takes ~5–10 minutes)

1. **Create a free GitHub account** (if you don't have one).
2. Create a **new public repository** on GitHub and upload these files (or drag the whole folder).
3. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
4. Click **New app** → select your repository and `app.py` as the main file.
5. Click **Deploy**.

That's it! Streamlit will automatically install everything and give you a public link.

Your app will be live and accessible from any browser. You can even share the link with others.

**Free tier limits**: Apps sleep after inactivity but wake up quickly when you visit. Perfect for personal use.

---

## Features

- Scrape any public webpage for thumbnails using `<img>`, video `poster`, and social meta tags
- Smart filtering to prefer real content thumbnails over logos/icons
- **Exact match detection** (perceptual hash distance = 0)
- **Similarity search** with adjustable Hamming distance threshold
- Clean grid + table results with direct links
- Works entirely locally (your images never leave your computer)

## 🚀 Easy Start for macOS (Mac Mini M1 / Apple Silicon)

**Best method for M1/M2/M3/M4 Macs (including macOS Tahoe):**

1. Download and unzip the folder.
2. Find the file named **`Video_Thumbnail_Matcher.command`**
3. **Double-click** it in Finder.
4. If macOS shows a security warning:
   - Right-click the file → choose **Open** (you may need to do this twice).
5. A Terminal window will open, set everything up automatically, and launch the tool in your browser.

> The first run can take 1–3 minutes while it installs Python packages. Subsequent launches are fast.

**If it still doesn't work:**

**Option A – Quick fix in Terminal (copy & paste these lines one by one):**

```bash
cd ~/Downloads/thumbnail_matcher_app          # Adjust path if you unzipped elsewhere
xattr -d com.apple.quarantine Video_Thumbnail_Matcher.command
chmod +x Video_Thumbnail_Matcher.command
./Video_Thumbnail_Matcher.command
```

**Option B – Install Python properly (recommended for Apple Silicon):**

```bash
# 1. Install Homebrew (if you don't have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Python (native arm64 version)
/opt/homebrew/bin/brew install python

# 3. Then double-click Video_Thumbnail_Matcher.command again
```

This ensures you have the correct native Python for M1 chips instead of Rosetta/Intel version.

---

## 🍎 Create a Real Native macOS .app (Recommended for Best Experience)

If you want a proper **Video Thumbnail Matcher.app** you can put in your Applications folder and launch like any other Mac program (supports Apple Silicon natively), use **Briefcase**:

### On your Mac Mini, open Terminal and run:

```bash
cd ~/Downloads/thumbnail_matcher_app     # Change if you unzipped it elsewhere

pip3 install briefcase

briefcase create macOS
briefcase build macOS
briefcase run macOS          # Test it

# To get a distributable .app:
briefcase package macOS
```

You will end up with a real `Video Thumbnail Matcher.app` bundle.

> The app opens the tool in a browser window (normal for Streamlit-based tools).  
> This is currently the easiest way to get a native-feeling Mac application without rewriting the whole tool in Swift.

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