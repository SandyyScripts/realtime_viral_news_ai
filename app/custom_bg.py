import base64
import os
import time
import uuid
import random
from io import BytesIO
from pathlib import Path
from PIL import Image

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


def generate_custom_bg(headline: str, pov: str, out_dir: str = "app/output", is_nano_banana: bool = False) -> str:
    """
    Generate a custom social-media news post image using either:
      - Nano Banana (Gemini) if is_nano_banana=True
      - Nebius Flux Schnell if is_nano_banana=False

    Returns path to saved PNG image.
    """
    os.makedirs(out_dir, exist_ok=True)

    # Cinematic overlays & effects
    cinematic_effects = [
        "volumetric light rays cutting through mist",
        "glowing particle swirls orbiting the focal object",
        "dramatic spotlight beams with deep shadows",
        "glass-shatter explosion in background with glowing shards",
        "energy motion streaks wrapping around the scene",
        "ethereal fog with glowing edges and cinematic depth"
    ]

    # Mood-based color palettes
    color_palettes = [
        "neon teal with golden sparks",
        "bright coral with glowing violet light",
        "electric blue with radiant white highlights",
        "deep charcoal with molten gold accents",
        "emerald green with luminous silver tones",
        "luxurious burgundy with glowing champagne highlights"
    ]

    def build_cinematic_prompt(headline: str) -> str:
        colors = random.choice(color_palettes)
        effect = random.choice(cinematic_effects)
        
        prompt = f"""
        Design a cinematic poster-style social media card for: "{headline}"

        Visual concept:
        - Symbolically dramatize the news with an epic central scene
        - {effect}
        - Palette: {colors}

        Artistic direction:
        - Bold editorial poster look (1080x1350 portrait)
        - Scroll-stopping, Instagram-viral, ultra-premium cinematic design
        - Central composition with glowing highlights, dramatic depth, and layered energy
        - Negative space zones for headline overlay
        - STRICTLY AVOID: human faces, gore, disturbing imagery, weapons
        - Focus on: breathtaking symbolic poster art that makes people stop scrolling
        - Output: ultra-high definition, no text, no watermarks, no logos
        """
        return prompt.strip()
    


    prompt = build_cinematic_prompt(headline)

    seed = random.randint(1, 1_000_000)
    filename = f"news_{int(time.time())}_{uuid.uuid4().hex[:6]}.png"
    out_path = os.path.join(out_dir, filename)

    if is_nano_banana:
        if not genai_client:
            raise RuntimeError("Google GenAI not configured. Set GOOGLE_API_KEY.")
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=prompt,
            config={"seed": seed},
        )
        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                img = Image.open(BytesIO(part.inline_data.data))
                img.save(out_path, format="PNG")
                return out_path
        raise RuntimeError("❌ No image returned from Gemini.")
    else:
        if not NEBIUS_API_KEY:
            raise RuntimeError("Nebius Studio not configured. Set NEBIUS_API_KEY.")
        response = nebius_client.images.generate(
            model="black-forest-labs/flux-schnell",
            prompt=prompt,
            response_format="b64_json",   # ensure inline base64
            size="1080x1350"  
        )
        # Nebius returns base64 JSON
        b64_image = response.data[0].b64_json
        img = Image.open(BytesIO(base64.b64decode(b64_image)))
        img.save(out_path, format="PNG")
        return out_path
    
