import base64
import os
import time
import uuid
import random
from io import BytesIO
from pathlib import Path
from PIL import Image
from typing import Optional

# Google Gemini
try:
    from google import genai
except ImportError:
    genai = None

# Nebius Studio (OpenAI-compatible)
from openai import OpenAI

# Configure clients once
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")

genai_client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY and genai else None
nebius_client = OpenAI(base_url="https://api.studio.nebius.com/v1/", api_key=NEBIUS_API_KEY)


def generate_custom_bg(
    headline: str,
    pov: str,
    out_dir: str = "app/output",
    is_nano_banana: bool = False,
    category: str = "general",
    article_image_url: Optional[str] = None,
    flux_prompt: Optional[str] = None
) -> str:
    """
    Generate professional news agency-quality background images.

    SIMPLIFIED APPROACH:
    - Uses AI-generated Flux Schnell prompt from ChatGPT (passed as flux_prompt)
    - Adds simple quality rules and restrictions
    - Generates with Flux Schnell or Gemini

    Args:
        headline: News headline
        pov: AI point of view / analysis
        out_dir: Output directory
        is_nano_banana: Use Gemini (True) or Nebius Flux Schnell (False)
        category: News category (for fallback only)
        article_image_url: Optional URL to article's featured image (for future use)
        flux_prompt: AI-generated Flux Schnell optimized prompt from ChatGPT

    Returns:
        Path to generated PNG image
    """
    os.makedirs(out_dir, exist_ok=True)

    # Build final Flux Schnell prompt
    if flux_prompt:
        # Use AI-generated prompt + add quality rules
        final_prompt = f"""{flux_prompt}

Quality: 4K UHD, ultra-detailed, photorealistic, sharp focus, professional depth of field, cinematic lighting, HDR color grading, editorial magazine quality, dark vignette edges, clean negative space for text overlay

Restrictions: NO faces, NO text, NO logos, NO brands, NO watermarks

Aspect Ratio: 9:16 portrait (1080x1350px)
Output: Award-winning photojournalism, Reuters/AFP/BBC quality"""
    else:
        # Fallback: Simple category-based prompt
        category_styles = {
            "politics": "parliament building silhouette, democratic symbols, authoritative blue and gold",
            "cricket": "cricket stadium lights, sports energy, vibrant blue and green",
            "bollywood": "cinema spotlight, glamorous purple and gold, entertainment flair",
            "economy": "financial charts abstract, rupee symbol glow, green and red",
            "tech": "futuristic circuit patterns, neon cyan and purple, digital innovation",
            "breaking": "urgent red glow, dramatic speed lines, breaking news energy",
            "education": "graduation cap, books, hopeful yellow and blue",
            "disaster": "somber clouds with hope light, soft amber, respectful tone",
            "positive": "sunrise celebration, uplifting orange and yellow, victory",
            "general": "professional modern abstract, teal and gold, balanced"
        }

        style = category_styles.get(category, category_styles["general"])

        final_prompt = f"""News background visual: {style}

Subject inspired by: {headline[:100]}

Quality: 4K UHD, photorealistic, cinematic, editorial magazine quality, 9:16 portrait
Restrictions: NO faces, NO text, NO logos
Output: Professional news agency photography"""

    # Ensure prompt is under Flux Schnell's 2000 char limit
    final_prompt = final_prompt.strip()[:1950]

    seed = random.randint(1, 1_000_000)
    filename = f"news_{int(time.time())}_{uuid.uuid4().hex[:6]}.png"
    out_path = os.path.join(out_dir, filename)

    if is_nano_banana:
        # Use Google Gemini (Nano Banana)
        if not genai_client:
            raise RuntimeError("Google GenAI not configured. Set GOOGLE_API_KEY.")
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=final_prompt,
            config={"seed": seed},
        )
        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                img = Image.open(BytesIO(part.inline_data.data))
                img.save(out_path, format="PNG")
                return out_path
        raise RuntimeError("❌ No image returned from Gemini.")
    else:
        # Use Nebius Flux Schnell (default, per user preference)
        if not NEBIUS_API_KEY:
            raise RuntimeError("Nebius Studio not configured. Set NEBIUS_API_KEY.")

        response = nebius_client.images.generate(
            model="black-forest-labs/flux-schnell",
            prompt=final_prompt,
            response_format="b64_json",
            size="1080x1350"
        )

        b64_image = response.data[0].b64_json
        img = Image.open(BytesIO(base64.b64decode(b64_image)))
        img.save(out_path, format="PNG")
        return out_path
