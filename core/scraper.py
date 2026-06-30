"""
Core scraping module for Site Reverse Image Search tool.
Handles single-page and paginated scraping with smart filtering.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import streamlit as st

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def is_likely_thumbnail(img_tag, abs_url: str, min_dimension: int = 100) -> bool:
    """Heuristic to filter out logos, icons, and small images."""
    url_lower = abs_url.lower()
    skip_patterns = ["logo", "icon", "avatar", "pixel", "spacer", "blank", "favicon", ".svg"]
    if any(p in url_lower for p in skip_patterns):
        return False

    try:
        w = int(img_tag.get("width", 0))
        h = int(img_tag.get("height", 0))
        if w > 0 and h > 0 and (w < min_dimension or h < min_dimension):
            return False
    except (ValueError, TypeError):
        pass

    return True


def get_image_hash(image_url: str, timeout: int = 10):
    """Download image and return perceptual hash + size."""
    try:
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        resp = requests.get(image_url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return None, None

        img = Image.open(BytesIO(resp.content))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        import imagehash
        phash = imagehash.phash(img)
        return phash, img.size
    except Exception:
        return None, None


def scrape_thumbnails(base_url: str, max_images: int = 100, min_dimension: int = 100):
    """Scrape thumbnails from a single page."""
    candidates = []
    seen = set()

    try:
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        resp = requests.get(base_url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if not src:
                continue

            abs_url = urljoin(base_url, src)
            if abs_url in seen:
                continue
            if not is_likely_thumbnail(img, abs_url, min_dimension):
                continue

            seen.add(abs_url)
            candidates.append(abs_url)
            if len(candidates) >= max_images:
                break

        # Also check video posters
        for video in soup.find_all("video"):
            poster = video.get("poster")
            if poster:
                abs_url = urljoin(base_url, poster)
                if abs_url not in seen:
                    seen.add(abs_url)
                    candidates.append(abs_url)

        return candidates[:max_images]

    except Exception as e:
        st.warning(f"Scraping error on {base_url}: {e}")
        return []


def scrape_paginated_thumbnails(base_url: str, page_template: str, num_pages: int,
                                max_images: int, min_dimension: int):
    """Scrape across multiple pages using a template."""
    all_candidates = []
    seen = set()

    progress = st.progress(0, text="Scraping pages...")

    for i in range(1, num_pages + 1):
        page_url = page_template.replace("{page}", str(i))
        progress.progress(i / num_pages, text=f"Scraping page {i}/{num_pages}...")

        page_candidates = scrape_thumbnails(page_url, max_images=5000, min_dimension=min_dimension)
        for url in page_candidates:
            if url not in seen:
                seen.add(url)
                all_candidates.append(url)
                if len(all_candidates) >= max_images:
                    progress.empty()
                    return all_candidates

    progress.empty()
    return all_candidates[:max_images]
