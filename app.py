#!/usr/bin/env python3
"""
Video Thumbnail Matcher - A Streamlit web tool
Scrapes video thumbnails (or images) from any website URL and finds exact or similar matches
to an uploaded reference image using perceptual hashing.

Run with: streamlit run app.py
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from PIL import Image, UnidentifiedImageError
import imagehash
from io import BytesIO
import time
import numpy as np

# Optional CLIP imports (loaded only when needed)
try:
    import torch
    import open_clip
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False

# ---------------------------
# Configuration & Helpers
# ---------------------------

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

def get_image_hash(image_url: str, timeout: int = 12):
    """
    Download image and compute perceptual hash (pHash).
    Returns (hash_object, (width, height)) or (None, None) on failure.
    """
    try:
        headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept": "image/*,*/*;q=0.8"}
        resp = requests.get(image_url, headers=headers, timeout=timeout, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type.lower():
            return None, None

        # Read content
        content = resp.content
        img = Image.open(BytesIO(content))

        # Convert to RGB if necessary (handles RGBA, P, etc.)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Optional: downsize very large images for faster hashing (doesn't hurt perceptual quality much)
        if max(img.size) > 1024:
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

        phash = imagehash.phash(img)
        return phash, img.size

    except (requests.RequestException, UnidentifiedImageError, OSError, ValueError):
        return None, None
    except Exception:
        # Catch-all for unexpected issues (e.g. corrupt image)
        return None, None


def is_likely_thumbnail(img_tag, abs_url: str, min_dimension: int = 100) -> bool:
    """
    Heuristic filter to prefer actual content thumbnails over icons/logos.
    """
    url_lower = abs_url.lower()

    # Skip obvious non-content images
    skip_patterns = [
        "logo", "icon", "avatar", "pixel", "spacer", "blank", "1x1",
        "favicon", ".svg", "tracking", "analytics", "beacon", "sprite"
    ]
    if any(p in url_lower for p in skip_patterns):
        return False

    # Check explicit width/height attributes on the tag
    try:
        w = int(img_tag.get("width", 0))
        h = int(img_tag.get("height", 0))
        if w > 0 and h > 0:
            if w < min_dimension or h < min_dimension:
                return False
    except (ValueError, TypeError):
        pass

    # Prefer images that look like thumbnails (in URL or nearby context)
    thumb_hints = ["thumb", "thumbnail", "poster", "video", "cover", "preview", "still"]
    parent_classes = ""
    if img_tag.parent:
        parent_classes = " ".join(img_tag.parent.get("class", [])) if img_tag.parent.get("class") else ""
    tag_classes = " ".join(img_tag.get("class", [])) if img_tag.get("class") else ""

    if any(hint in (url_lower + " " + tag_classes + " " + parent_classes).lower() for hint in thumb_hints):
        return True

    # If no strong negative signals and reasonable size hints, accept
    return True


def scrape_thumbnails(base_url: str, max_images: int = 100, min_dimension: int = 100):
    """
    Fetch page, extract candidate image URLs that are likely video thumbnails.
    Set max_images to a very high number (e.g. 5000) for unlimited scraping.
    Returns list of absolute image URLs (capped by max_images).
    """
    candidates = []
    seen = set()

    try:
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        resp = requests.get(base_url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # 1. Standard <img> tags + common lazy-load attributes
        for img in soup.find_all("img"):
            for attr in ("src", "data-src", "data-lazy-src", "data-original", "data-srcset"):
                src = img.get(attr)
                if not src:
                    continue
                # Handle srcset (take first URL)
                if attr == "data-srcset" or "srcset" in attr:
                    src = src.split(",")[0].strip().split(" ")[0]

                abs_url = urljoin(base_url, src)
                if abs_url in seen:
                    continue

                if is_likely_thumbnail(img, abs_url, min_dimension):
                    seen.add(abs_url)
                    candidates.append(abs_url)
                    if len(candidates) >= max_images:
                        break
            if len(candidates) >= max_images:
                break

        # 2. <video> poster attributes (often high-quality thumbnails)
        for video in soup.find_all("video"):
            poster = video.get("poster")
            if poster:
                abs_url = urljoin(base_url, poster)
                if abs_url not in seen:
                    seen.add(abs_url)
                    candidates.append(abs_url)
                    if len(candidates) >= max_images:
                        break

        # 3. Open Graph / Twitter card images (often the main video thumb)
        for meta_name in ("og:image", "og:image:secure_url", "twitter:image"):
            meta = soup.find("meta", property=meta_name) or soup.find("meta", attrs={"name": meta_name})
            if meta:
                content = meta.get("content")
                if content:
                    abs_url = urljoin(base_url, content)
                    if abs_url not in seen and is_likely_thumbnail(meta, abs_url, min_dimension):
                        seen.add(abs_url)
                        candidates.append(abs_url)

        return candidates[:max_images]

    except requests.RequestException as e:
        st.error(f"Network error while fetching page: {e}")
        return []
    except Exception as e:
        st.error(f"Unexpected error during scraping: {e}")
        return []


def scrape_paginated_thumbnails(base_url: str, page_template: str, num_pages: int, max_images: int, min_dimension: int):
    """
    Scrape thumbnails across multiple paginated pages.
    Replaces {page} in page_template with 1, 2, 3, ...
    Optimized for high page counts (thousands+).
    """
    all_candidates = []
    seen = set()

    # For very high page counts, update progress less frequently to avoid UI lag
    update_frequency = max(1, num_pages // 100)  # Update roughly every 1% of pages

    progress = st.progress(0, text=f"Scraping page 1 of {num_pages}...")

    for i in range(1, num_pages + 1):
        page_url = page_template.replace("{page}", str(i))

        # Only update progress periodically for performance
        if i % update_frequency == 0 or i == 1 or i == num_pages:
            progress.progress(i / num_pages, text=f"Scraping page {i} of {num_pages}...")

        try:
            # Reuse the single-page logic but without its own max limit first
            page_candidates = scrape_thumbnails(page_url, max_images=5000, min_dimension=min_dimension)
            for url in page_candidates:
                if url not in seen:
                    seen.add(url)
                    all_candidates.append(url)
                    if len(all_candidates) >= max_images:
                        progress.empty()
                        return all_candidates
        except Exception as e:
            st.warning(f"Could not scrape page {i} ({page_url}): {e}")
            continue

    progress.empty()
    return all_candidates[:max_images]


def compute_similarity(query_hash, target_hash) -> int:
    """Return Hamming distance (0 = identical / extremely similar)."""
    return query_hash - target_hash


def hamming_to_similarity(distance: int) -> float:
    """Convert pHash Hamming distance to a similarity percentage (0-100%)."""
    if distance <= 0:
        return 100.0
    similarity = max(0.0, 100 - (distance / 64.0 * 100))
    return round(similarity, 1)


@st.cache_resource(show_spinner="Loading AI model (CLIP)... This may take a minute on first use.")
def load_clip_model():
    """Load CLIP model for semantic image search. Uses a good balance of speed/quality."""
    if not CLIP_AVAILABLE:
        return None, None, None
    try:
        model, _, preprocess = open_clip.create_model_and_transforms(
            'ViT-B-32', 
            pretrained='openai',
            device='cpu'  # Use CPU for broad compatibility
        )
        model.eval()
        return model, preprocess, open_clip.get_tokenizer('ViT-B-32')
    except Exception as e:
        st.error(f"Failed to load CLIP model: {e}")
        return None, None, None


def get_clip_embedding(image_input, model, preprocess):
    """Get CLIP image embedding for a PIL Image or image URL."""
    if model is None or preprocess is None:
        return None
    try:
        if isinstance(image_input, str):  # URL
            resp = requests.get(image_input, timeout=8, headers={"User-Agent": DEFAULT_USER_AGENT})
            img = Image.open(BytesIO(resp.content)).convert("RGB")
        else:  # PIL Image
            img = image_input.convert("RGB")

        image_tensor = preprocess(img).unsqueeze(0)
        with torch.no_grad():
            embedding = model.encode_image(image_tensor)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)  # Normalize
        return embedding.squeeze().cpu().numpy()
    except Exception as e:
        return None


# ---------------------------
# Streamlit UI
# ---------------------------

st.set_page_config(
    page_title="Site Reverse Image Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔍 Site Reverse Image Search")
st.markdown(
    "Upload an image and find **visually similar or exact matching images** on any website — "
    "like Google Reverse Image Search, but limited to one specific site or domain."
)

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Settings")
    max_images = st.slider(
        "Maximum thumbnails to scrape",
        min_value=5,
        max_value=1000,
        value=100,
        step=10,
        help="Higher values scrape more images but can be slower. 100–300 is usually plenty. Use 500+ only if needed."
    )

    unlimited_scrape = st.checkbox(
        "Scrape unlimited thumbnails (no limit)",
        value=False,
        help="⚠️ Warning: This can be very slow on pages with hundreds of images and may hit website rate limits."
    )
    if unlimited_scrape:
        max_images = 5000  # Effectively unlimited for practical purposes
        st.warning("Unlimited mode enabled — scraping may take longer and use more bandwidth.")

    use_clip = False
    if CLIP_AVAILABLE:
        use_clip = st.checkbox(
            "Use AI Semantic Search (CLIP) — Recommended",
            value=True,
            help="Much smarter matching using AI (understands content & context). Recommended for most use cases."
        )
        if use_clip:
            st.success("AI Semantic Search enabled")
            if len(st.session_state.get("thumb_hashes", {})) > 400:
                st.warning("Large number of images detected. CLIP mode may be slow. Consider reducing 'Maximum thumbnails' or using Visual Hash mode for very large scrapes.")
    else:
        st.caption("💡 Install `torch` + `open-clip-torch` for powerful AI Semantic Search (CLIP)")

    min_dimension = st.slider("Minimum thumbnail size (px)", min_value=60, max_value=250, value=110, step=10,
                              help="Filters out small icons/logos")
    max_distance = st.slider("Similarity threshold (Hamming distance)", min_value=0, max_value=25, value=8, step=1,
                             help="Lower = stricter match. 0 = exact perceptual match. Typical good similar range: 2–10")
    st.divider()
    st.caption("**Note:** Works best on pages with static HTML thumbnails. "
               "Heavy JS sites (YouTube, Instagram, etc.) may return fewer results.")

# Session state init
if "thumb_hashes" not in st.session_state:
    st.session_state.thumb_hashes = {}
if "scraped_url" not in st.session_state:
    st.session_state.scraped_url = ""

# Layout
tab_scrape, tab_match = st.tabs(["🔍 Scrape Website", "🖼️ Find Matches"])

with tab_scrape:
    st.subheader("Step 1: Scrape Video Thumbnails")
    target_url = st.text_input(
        "Website URL containing video thumbnails",
        placeholder="https://example.com/videos-page or https://vimeo.com/channels/staffpicks",
        help="Enter any public page that displays video thumbnails in its HTML source."
    )

    with st.expander("📄 Pagination (for sites with page 1, page 2, page 3...)", expanded=False):
        use_pagination = st.checkbox("Scrape multiple pages (pagination)", value=False)
        num_pages = 1
        page_template = target_url
        if use_pagination:
            num_pages = st.number_input(
                "Number of pages to scrape",
                min_value=1,
                max_value=100000,
                value=5,
                step=1,
                help="You can go up to 100,000 pages. Be careful — very high numbers will take hours and may get your connection blocked by the website."
            )
            page_template = st.text_input(
                "Page URL template — replace page number with {page}",
                value=target_url,
                help="Examples:\n• https://site.com/videos?page={page}\n• https://site.com/page{page}.html\n• https://site.com/videos/{page}"
            )
            if num_pages > 100:
                st.warning("⚠️ You selected more than 100 pages. This can take a very long time and may trigger rate limits or IP blocks on the target site.")
            if num_pages > 1000:
                st.error("🚨 Extremely high page count selected. Only proceed if you are sure the site can handle it and you have permission.")
            st.info("The tool will scrape page 1, page 2, ... up to the number you choose and combine all unique thumbnails.")

    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        scrape_btn = st.button("🚀 Scrape & Analyze Thumbnails", type="primary", use_container_width=True)
    with col_btn2:
        if st.button("🗑️ Clear Previous Data", use_container_width=True):
            st.session_state.thumb_hashes = {}
            st.session_state.scraped_url = ""
            st.rerun()

    if scrape_btn:
        if not target_url or not target_url.startswith(("http://", "https://")):
            st.error("Please enter a valid URL starting with http:// or https://")
        else:
            spinner_text = "Scraping thumbnails..."
            if use_pagination:
                if num_pages > 50:
                    spinner_text = f"Scraping {num_pages} pages (this may take a long time)..."
                else:
                    spinner_text = f"Scraping {num_pages} pages..."
            with st.spinner(spinner_text):
                start = time.time()

                if use_pagination and 'page_template' in locals() and page_template:
                    candidate_urls = scrape_paginated_thumbnails(
                        target_url, page_template, num_pages, max_images, min_dimension
                    )
                    display_url = f"{page_template} (pages 1–{num_pages})"
                else:
                    candidate_urls = scrape_thumbnails(target_url, max_images, min_dimension)
                    display_url = target_url

                if not candidate_urls:
                    st.warning("No candidate images found. The page might be heavily JavaScript-rendered or protected.")
                else:
                    progress_bar = st.progress(0.0, text="Downloading & hashing images...")
                    hashes_dict = {}
                    success_count = 0

                    for idx, img_url in enumerate(candidate_urls):
                        phash, size = get_image_hash(img_url)
                        if phash is not None:
                            hashes_dict[img_url] = {"hash": phash, "size": size}
                            success_count += 1
                        progress_bar.progress((idx + 1) / len(candidate_urls), text=f"Processed {idx+1}/{len(candidate_urls)}")

                    progress_bar.empty()

                    if hashes_dict:
                        st.session_state.thumb_hashes = hashes_dict
                        st.session_state.scraped_url = display_url
                        elapsed = time.time() - start
                        st.success(f"✅ Successfully processed **{success_count}** thumbnails across pages in {elapsed:.1f}s")
                    else:
                        st.error("Could not download/analyze any images. Check URL or try another page.")

    # Preview section (always visible if data exists)
    if st.session_state.thumb_hashes:
        st.divider()
        with st.expander(f"🖼️ Preview Scraped Thumbnails ({len(st.session_state.thumb_hashes)} total)", expanded=False):
            preview_urls = list(st.session_state.thumb_hashes.keys())[:16]
            cols = st.columns(4)
            for i, url in enumerate(preview_urls):
                with cols[i % 4]:
                    try:
                        st.image(url, use_column_width=True, caption=urlparse(url).netloc)
                    except Exception:
                        st.caption(f"⚠️ Could not display: {url[:60]}...")

with tab_match:
    st.subheader("Step 2: Upload Reference Image & Find Matches")

    if not st.session_state.thumb_hashes:
        st.info("👆 Please scrape a website first in the **Scrape Website** tab.")
    else:
        st.caption(f"Comparing against **{len(st.session_state.thumb_hashes)}** thumbnails from: {st.session_state.scraped_url}")

        st.markdown("**Your Reference Image**")
        col_upload, col_url = st.columns(2)

        with col_upload:
            uploaded_file = st.file_uploader(
                "Upload image file",
                type=["png", "jpg", "jpeg", "webp"],
                help="Upload the image you want to search for"
            )

        with col_url:
            image_url_input = st.text_input(
                "Or paste image URL",
                placeholder="https://example.com/image.jpg",
                help="Direct link to an image on the web"
            )

        query_img = None
        query_source = None

        if uploaded_file:
            try:
                query_img = Image.open(uploaded_file)
                query_source = "file"
            except Exception as e:
                st.error(f"Could not open uploaded file: {e}")

        elif image_url_input:
            try:
                resp = requests.get(image_url_input, timeout=10, headers={"User-Agent": DEFAULT_USER_AGENT})
                if resp.status_code == 200:
                    query_img = Image.open(BytesIO(resp.content))
                    query_source = "url"
                else:
                    st.error("Could not download image from the URL provided.")
            except Exception as e:
                st.error(f"Error loading image from URL: {e}")

        if query_img:
            if query_img.mode != "RGB":
                query_img = query_img.convert("RGB")

            # Show query
            qcol1, qcol2 = st.columns([1, 2])
            with qcol1:
                st.image(query_img, caption="Your Reference Image", width=280)
            with qcol2:
                st.write("**Image info:**")
                st.write(f"- Source: {query_source}")
                st.write(f"- Size: {query_img.size[0]} × {query_img.size[1]} px")
                st.write(f"- Mode: {query_img.mode}")

            if st.button("🔎 Search this site for similar images", type="primary"):
                if not st.session_state.thumb_hashes:
                    st.error("Please scrape a website first in the Scrape tab!")
                else:
                    with st.spinner("Analyzing images with AI..." if use_clip else "Computing similarity..."):
                        ranked = []

                        if use_clip and CLIP_AVAILABLE:
                            # === CLIP Semantic Search Mode ===
                            model, preprocess, _ = load_clip_model()
                            if model is None:
                                st.error("CLIP model failed to load. Falling back to visual hash.")
                                use_clip = False
                            else:
                                query_emb = get_clip_embedding(query_img, model, preprocess)
                                if query_emb is None:
                                    st.error("Could not create embedding for your image.")
                                else:
                                    for turl, data in st.session_state.thumb_hashes.items():
                                        img_emb = get_clip_embedding(turl, model, preprocess)
                                        if img_emb is not None:
                                            # Cosine similarity
                                            sim = float(np.dot(query_emb, img_emb))
                                            ranked.append({
                                                "url": turl,
                                                "similarity": sim,
                                                "distance": 1 - sim,  # For compatibility
                                                "size": data["size"],
                                                "is_clip": True
                                            })
                        else:
                            # === Traditional pHash Mode ===
                            query_hash = imagehash.phash(query_img)
                            for turl, data in st.session_state.thumb_hashes.items():
                                dist = compute_similarity(query_hash, data["hash"])
                                ranked.append({
                                    "url": turl,
                                    "distance": dist,
                                    "size": data["size"],
                                    "is_clip": False
                                })

                        if not ranked:
                            st.error("No images could be compared.")
                        else:
                            if use_clip:
                                ranked.sort(key=lambda x: x["similarity"], reverse=True)  # Higher similarity first
                                exact_matches = [r for r in ranked if r["similarity"] > 0.95]
                                similar_matches = [r for r in ranked if 0.7 < r["similarity"] <= 0.95]
                            else:
                                ranked.sort(key=lambda x: x["distance"])
                                exact_matches = [r for r in ranked if r["distance"] == 0]
                                similar_matches = [r for r in ranked if 0 < r["distance"] <= max_distance]

                        # Results header
                        st.divider()
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Exact Matches", len(exact_matches))
                        m2.metric("Similar Matches", len(similar_matches))
                        m3.metric("Images Analyzed", len(ranked))

                        # Exact matches
                        if exact_matches:
                            st.success("🎯 **Exact / Perceptually Identical Matches**")
                            ex_cols = st.columns(min(5, len(exact_matches)))
                            for i, match in enumerate(exact_matches[:5]):
                                with ex_cols[i]:
                                    st.image(match["url"], use_column_width=True)
                                    st.caption("**100%** match (exact)")
                                    st.markdown(f"[🔗 Open full image]({match['url']})")

                        # Results display - supports both pHash and CLIP modes
                        is_clip_mode = use_clip and CLIP_AVAILABLE and any(r.get("is_clip") for r in ranked[:1])

                        if similar_matches:
                            st.subheader(f"🔍 Similar Images ({len(similar_matches)} found)")
                            sim_cols = st.columns(4)
                            for i, match in enumerate(similar_matches[:12]):
                                with sim_cols[i % 4]:
                                    if is_clip_mode:
                                        sim_pct = round(match.get("similarity", 0) * 100, 1)
                                        caption = f"**{sim_pct}%** semantic match"
                                    else:
                                        sim_pct = hamming_to_similarity(match["distance"])
                                        caption = f"**{sim_pct}%** similar"

                                    st.image(match["url"], use_column_width=True)
                                    st.caption(f"{caption} • {match['size'][0]}×{match['size'][1]}")
                                    with st.popover("Details"):
                                        if is_clip_mode:
                                            st.write(f"**Semantic Similarity (AI):** {sim_pct}%")
                                            visual_pct = hamming_to_similarity(match.get("distance", 64))
                                            st.write(f"**Visual Similarity:** {visual_pct}%")
                                            st.caption("Hybrid view: AI understands meaning + traditional visual match")
                                        else:
                                            st.write(f"**Visual Similarity:** {sim_pct}%")
                                            st.write(f"**Hamming Distance:** {match['distance']} (lower = better)")
                                        st.write(f"**Dimensions:** {match['size'][0]} × {match['size'][1]} px")
                                        st.code(match["url"], language=None)
                                        st.markdown(f"[🔗 Open full image]({match['url']})")
                        elif not exact_matches:
                            st.warning(f"No matches found within distance ≤ {max_distance}. "
                                       "Try increasing the threshold in the sidebar or using a different reference image.")

                        # Show top 20 ranked (even beyond threshold) in a compact table
                        with st.expander("📋 Show Top 20 Ranked Matches (all distances)", expanded=False):
                            import pandas as pd
                            top20 = ranked[:20]
                            df = pd.DataFrame([
                                {
                                    "Rank": i+1,
                                    "Distance": r["distance"],
                                    "Width": r["size"][0],
                                    "Height": r["size"][1],
                                    "URL": r["url"][:80] + "..." if len(r["url"]) > 80 else r["url"]
                                } for i, r in enumerate(top20)
                            ])
                            st.dataframe(df, use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"Error processing uploaded image: {e}")

# Footer / Limitations
st.divider()
with st.expander("ℹ️ How it works & Limitations"):
    st.markdown("""
    **How it works**
    1. Scrapes a webpage for `<img>` tags, video `poster` attributes, and social meta images.
    2. Filters out obvious icons/logos using heuristics.
    3. Downloads each candidate and computes a **perceptual hash (pHash)** — a 64-bit fingerprint of visual content.
    4. Your uploaded image gets the same hash treatment.
    5. Matches are ranked by **Hamming distance** between hashes (0 = identical or near-identical visually).

    **Good for**
    - Finding duplicate or slightly edited thumbnails
    - Locating the same scene/person across different videos
    - Reverse image search style matching within one site

    **Limitations**
    - **JavaScript-heavy sites** (YouTube, TikTok, Instagram, many modern SPAs): Only static HTML is parsed. Thumbnails loaded dynamically are often missed. Use pages that render thumbnails in the initial HTML source.
    - Not semantic/AI understanding — it sees visual similarity, not "this is a cat".
    - Some sites block hotlinking or return 403/429 — those images are skipped.
    - Large pages with 100+ images can be slow (each image is downloaded).

    **Dependencies** (install once):
    ```bash
    pip install streamlit requests beautifulsoup4 Pillow imagehash lxml pandas
    ```
    Then run: `streamlit run app.py`

    **Privacy**: All processing happens locally on your machine. No images or URLs are sent to any third party.
    """)

st.caption("Built with ❤️ using perceptual hashing • For personal, educational, and research use • Respect website Terms of Service and robots.txt")
