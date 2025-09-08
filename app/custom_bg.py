import os
import time
import uuid
import random
from google import genai
from PIL import Image
from io import BytesIO

# Configure client once
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def generate_custom_bg(headline: str, pov: str, out_dir: str = "app/output") -> str:
    """
    Generate a custom social-media news post image using Nano Banana (Gemini).
    Adds randomness via style adjectives + seed so each call is unique.
    
    Args:
        headline: News headline text
        pov: AI point of view / context
        out_dir: Directory to save the generated image
    
    Returns:
        Path to saved image file
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

    # Add randomness via seed
    seed = random.randint(1, 1_000_000)

    # Call the API
    response = client.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents=prompt,
        config={"seed": seed}
    )

    # Find image in response
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            img = Image.open(BytesIO(part.inline_data.data))
            filename = f"news_{int(time.time())}_{uuid.uuid4().hex[:6]}.png"
            out_path = os.path.join(out_dir, filename)
            img.save(out_path)
            return out_path

    raise RuntimeError("❌ No image returned from Gemini model.")