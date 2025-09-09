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

    # Randomized style adjectives for variation
    style_word = random.choice(["cinematic", "photorealistic", "hyperreal", "dramatic"])
    energy_word = random.choice(["energetic", "dynamic", "intense", "celebratory"])

    prompt = f"""
    You are a professional social media designer creating a viral news post background image.

    Task:
    Create one bold, editorial, ultra-detailed {style_word} image that represents this news:
    "{headline}"

    Context:
    {pov}

    Rendering instructions:
    - Format: 1080x1350 portrait (Instagram feed).
    - Style: {style_word}, ultra-detailed, editorial, thumb-stopping social-card.
    - Tone: {energy_word}, high energy — suitable to stop scrolling.
    - Virality cues: high contrast, dramatic perspective, clean negative space for overlays.
    - Prohibited: no logos, no watermarks, no political hate symbols, no real faces, no text burned in.

    Output:
    One high-resolution image (PNG). Do not draw text, just provide a clean visual background.
    """

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
    
