"""
Site Reverse Image Search - Clean v2
A powerful tool to find similar images on any website using pHash + CLIP.
"""

import streamlit as st
from PIL import Image
from io import BytesIO
import requests

from core.scraper import scrape_thumbnails, scrape_paginated_thumbnails
from core.matcher import (
    compute_phash_similarity,
    compute_clip_similarity,
    hamming_to_similarity,
    load_clip_model
)

st.set_page_config(page_title="Site Reverse Image Search", page_icon="🔍", layout="wide")

st.title("🔍 Site Reverse Image Search")
st.markdown("Upload an image and find visually or semantically similar images on any website.")

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("Settings")

    use_clip = st.checkbox(
        "Use AI Semantic Search (CLIP) — Recommended",
        value=True,
        help="Uses AI to understand image content. More powerful but slower."
    )

    max_images = st.slider("Max images to analyze", 10, 500, 150, 10)

    min_dimension = st.slider("Min thumbnail size (px)", 60, 200, 100, 10,
                              help="Filters out small icons/logos")

    st.divider()
    st.caption("Tip: For best results on paginated sites, use the pagination options in the Search tab.")

# ====================== TABS ======================
tab1, tab2 = st.tabs(["📷 Upload Reference Image", "🔎 Search on Website"])

# ====================== TAB 1: UPLOAD ======================
with tab1:
    st.subheader("Step 1: Upload Your Reference Image")

    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("Upload image", type=["png", "jpg", "jpeg", "webp"])

    with col2:
        image_url = st.text_input("Or paste image URL", placeholder="https://...")

    query_img = None
    if uploaded_file:
        query_img = Image.open(uploaded_file)
    elif image_url:
        try:
            resp = requests.get(image_url, timeout=10)
            query_img = Image.open(BytesIO(resp.content))
        except Exception as e:
            st.error(f"Could not load image from URL: {e}")

    if query_img:
        if query_img.mode != "RGB":
            query_img = query_img.convert("RGB")

        st.session_state.reference_image = query_img
        st.image(query_img, caption="Your Reference Image", width=280)
        st.success("Image ready! Go to the **Search on Website** tab.")
    else:
        st.info("Upload an image or paste a URL to continue.")

# ====================== TAB 2: SEARCH ======================
with tab2:
    st.subheader("Step 2: Search on a Website")

    if "reference_image" not in st.session_state:
        st.warning("Please upload your reference image in the first tab first.")
        st.stop()

    query_img = st.session_state.reference_image

    with st.expander("Your Reference Image", expanded=False):
        st.image(query_img, width=150)

    target_url = st.text_input(
        "Website URL to search within",
        placeholder="https://example.com or https://vimeo.com/..."
    )

    # Pagination
    with st.expander("📄 Pagination (optional)", expanded=False):
        enable_pagination = st.checkbox("Scrape multiple pages")
        num_pages = 1
        page_template = target_url
        if enable_pagination:
            num_pages = st.number_input("Number of pages", 1, 500, 5)
            page_template = st.text_input("Page template (use {page})", value=target_url)

    if st.button("🔎 Search for Similar Images", type="primary"):
        if not target_url:
            st.error("Please enter a website URL.")
            st.stop()

        with st.spinner("Scraping website..."):
            if enable_pagination and num_pages > 1:
                image_urls = scrape_paginated_thumbnails(
                    target_url, page_template, num_pages, max_images, min_dimension
                )
            else:
                image_urls = scrape_thumbnails(target_url, max_images, min_dimension)

        if not image_urls:
            st.error("No suitable images found on that site.")
            st.stop()

        st.success(f"Found {len(image_urls)} images. Analyzing...")

        with st.spinner("Running similarity search..."):
            if use_clip:
                results = compute_clip_similarity(query_img, image_urls, max_images)
            else:
                results = compute_phash_similarity(query_img, image_urls, max_images)

        if not results:
            st.warning("No matches could be computed.")
            st.stop()

        # Display results
        st.subheader(f"Results ({len(results)} images analyzed)")

        cols = st.columns(4)
        for idx, res in enumerate(results[:12]):
            with cols[idx % 4]:
                try:
                    st.image(res["url"], use_column_width=True)
                    if use_clip:
                        st.caption(f"**{res['similarity']*100:.1f}%** semantic match")
                    else:
                        st.caption(f"**{res['similarity']}%** similar")
                except Exception:
                    pass

        # Show more in expander
        with st.expander("Show all results (table)"):
            import pandas as pd
            df = pd.DataFrame(results)
            st.dataframe(df[["url", "similarity", "distance"]].head(50), use_container_width=True)
