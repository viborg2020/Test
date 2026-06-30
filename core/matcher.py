"""
Matching module for Site Reverse Image Search.
Supports both traditional pHash and CLIP semantic similarity.
"""

import numpy as np
import streamlit as st
from io import BytesIO
import requests

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def hamming_to_similarity(distance: int) -> float:
    """Convert pHash Hamming distance to similarity percentage."""
    if distance <= 0:
        return 100.0
    return round(max(0.0, 100 - (distance / 64.0 * 100)), 1)


# ====================== pHash Matching ======================

def compute_phash_similarity(query_img, image_urls: list, max_images: int = 500):
    """Compute pHash similarity between query image and list of URLs."""
    import imagehash
    from PIL import Image

    query_hash = imagehash.phash(query_img)
    results = []

    for url in image_urls[:max_images]:
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": DEFAULT_USER_AGENT})
            if resp.status_code != 200:
                continue
            img = Image.open(BytesIO(resp.content))
            if img.mode != "RGB":
                img = img.convert("RGB")
            target_hash = imagehash.phash(img)
            distance = query_hash - target_hash
            similarity = hamming_to_similarity(distance)
            results.append({
                "url": url,
                "distance": distance,
                "similarity": similarity,
                "size": img.size,
                "method": "pHash"
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["distance"])
    return results


# ====================== CLIP Matching ======================

@st.cache_resource(show_spinner="Loading CLIP model (first time only)...")
def load_clip_model():
    try:
        import torch
        import open_clip
        model, _, preprocess = open_clip.create_model_and_transforms(
            'ViT-B-32', pretrained='openai', device='cpu'
        )
        model.eval()
        tokenizer = open_clip.get_tokenizer('ViT-B-32')
        return model, preprocess, tokenizer
    except Exception as e:
        st.error(f"Failed to load CLIP: {e}")
        return None, None, None


def get_clip_embedding(image_input, model, preprocess):
    """Get normalized CLIP embedding for PIL Image or URL."""
    from PIL import Image

    if model is None:
        return None
    try:
        if isinstance(image_input, str):
            resp = requests.get(image_input, timeout=8, headers={"User-Agent": DEFAULT_USER_AGENT})
            img = Image.open(BytesIO(resp.content)).convert("RGB")
        else:
            img = image_input.convert("RGB")

        image_tensor = preprocess(img).unsqueeze(0)
        with torch.no_grad():
            embedding = model.encode_image(image_tensor)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)
        return embedding.squeeze().cpu().numpy()
    except Exception:
        return None


def compute_clip_similarity(query_img, image_urls: list, max_images: int = 300):
    """Compute CLIP semantic similarity."""
    model, preprocess, _ = load_clip_model()
    if model is None:
        return []

    query_emb = get_clip_embedding(query_img, model, preprocess)
    if query_emb is None:
        return []

    results = []
    for url in image_urls[:max_images]:
        img_emb = get_clip_embedding(url, model, preprocess)
        if img_emb is not None:
            sim = float(np.dot(query_emb, img_emb))
            results.append({
                "url": url,
                "similarity": sim,
                "distance": 1 - sim,
                "size": (0, 0),
                "method": "CLIP"
            })

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results
