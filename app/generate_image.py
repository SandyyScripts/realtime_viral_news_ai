import os, io, re, asyncio, logging, base64, textwrap, pathlib, requests
from datetime import datetime
from dateutil import tz
from typing import Optional, List, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import json
from .custom_bg import generate_custom_bg

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATES_DIR = HERE / "templates"
OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Enhanced themes with better color schemes and gradients
THEMES: Dict[str, Dict[str, Any]] = {
    "breaking": {
        "brand": "#ff3b30", "accent": "#ff8a80", "brandDark": "#d32f2f", "accentDark": "#ff5722",
        "ai_bg": "rgba(255,59,48,0.15)", "ai_fg": "#ffffff", "cta_bg": "rgba(255,59,48,0.25)",
        "scrim_top": "rgba(0,0,0,.65)", "scrim_bottom": "rgba(0,0,0,.95)",
        "icon": "🚨", "title": "Breaking", "gradient": ["#ff3b30", "#ff8a80", "#d32f2f"]
    },
    "economy": {
        "brand": "#22c55e", "accent": "#16a34a", "brandDark": "#059669", "accentDark": "#047857",
        "ai_bg": "rgba(34,197,94,0.18)", "ai_fg": "#effff2", "cta_bg": "rgba(34,197,94,0.28)",
        "scrim_top": "rgba(0,0,0,.58)", "scrim_bottom": "rgba(0,0,0,.92)",
        "icon": "💹", "title": "Economy", "gradient": ["#22c55e", "#16a34a", "#059669"]
    },
    "cricket": {
        "brand": "#2563eb", "accent": "#1d4ed8", "brandDark": "#1e40af", "accentDark": "#1e3a8a",
        "ai_bg": "rgba(37,99,235,0.20)", "ai_fg": "#eef3ff", "cta_bg": "rgba(37,99,235,0.28)",
        "scrim_top": "rgba(0,0,0,.58)", "scrim_bottom": "rgba(0,0,0,.92)",
        "icon": "🏏", "title": "Cricket", "gradient": ["#2563eb", "#1d4ed8", "#1e40af"]
    },
    "tech": {
        "brand": "#a855f7", "accent": "#7e22ce", "brandDark": "#7c3aed", "accentDark": "#6b21a8",
        "ai_bg": "rgba(168,85,247,0.20)", "ai_fg": "#fff0ff", "cta_bg": "rgba(168,85,247,0.28)",
        "scrim_top": "rgba(0,0,0,.56)", "scrim_bottom": "rgba(0,0,0,.92)",
        "icon": "🤖", "title": "Tech", "gradient": ["#a855f7", "#7e22ce", "#7c3aed"]
    },
    "politics": {
        "brand": "#f59e0b", "accent": "#d97706", "brandDark": "#f97316", "accentDark": "#ea580c",
        "ai_bg": "rgba(245,158,11,0.20)", "ai_fg": "#fff7e8", "cta_bg": "rgba(245,158,11,0.28)",
        "scrim_top": "rgba(0,0,0,.58)", "scrim_bottom": "rgba(0,0,0,.92)",
        "icon": "🗳️", "title": "Politics", "gradient": ["#f59e0b", "#d97706", "#f97316"]
    },
    "disaster": {
        "brand": "#ef4444", "accent": "#b91c1c", "brandDark": "#dc2626", "accentDark": "#991b1b",
        "ai_bg": "rgba(239,68,68,0.20)", "ai_fg": "#ffecec", "cta_bg": "rgba(239,68,68,0.28)",
        "scrim_top": "rgba(0,0,0,.70)", "scrim_bottom": "rgba(0,0,0,.96)",
        "icon": "⚠️", "title": "Alert", "gradient": ["#ef4444", "#b91c1c", "#dc2626"]
    },
    "default": {
        "brand": "#00d4ff", "accent": "#22c1c3", "brandDark": "#0066cc", "accentDark": "#1a9a9e",
        "ai_bg": "rgba(0,212,255,0.18)", "ai_fg": "#e9fbff", "cta_bg": "rgba(0,212,255,0.25)",
        "scrim_top": "rgba(0,0,0,.58)", "scrim_bottom": "rgba(0,0,0,.92)",
        "icon": "✨", "title": "Trending", "gradient": ["#00d4ff", "#22c1c3", "#0066cc"]
    }
}

def detect_category(title: str, hashtags: str = "", content: str = "") -> str:
    """Enhanced category detection with content analysis"""
    text = f"{title} {hashtags} {content}".lower()
    
    # Priority order matters - more specific first
    if any(k in text for k in ["flood", "landslide", "earthquake", "cyclone", "disaster", "crash", "blast", "emergency", "alert", "warning"]): 
        return "disaster"
    if any(k in text for k in ["breaking", "urgent", "just in", "developing", "live"]): 
        return "breaking"
    if any(k in text for k in ["rupee", "inflation", "tariff", "budget", "economy", "jobs", "gdp", "stock market", "sensex", "nifty", "investment"]): 
        return "economy"
    if any(k in text for k in ["virat", "ipl", "cricket", "team india", "bcci", "world cup", "t20", "odi", "test match"]): 
        return "cricket"
    if any(k in text for k in ["ai ", "artificial intelligence", "iphone", "semiconductor", "chip", "tech", "startup", "android", "google", "apple", "meta", "openai"]): 
        return "tech"
    if any(k in text for k in ["election", "minister", "bjp", "congress", "parliament", "vote", "policy", "government", "political"]): 
        return "politics"
    
    return "default"

def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def _create_enhanced_gradient(colors: List[str], size: tuple = (1080, 1350)) -> bytes:
    """Create a sophisticated gradient with noise and effects"""
    w, h = size
    
    # Create base gradient
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    
    # Multi-stop gradient
    color_stops = [_hex_to_rgb(c) for c in colors]
    
    for y in range(h):
        # Calculate position in gradient (0 to 1)
        pos = y / h
        
        # Determine which colors to interpolate between
        if pos <= 0.5:
            # First half: color[0] to color[1]
            t = pos * 2
            start_color = color_stops[0]
            end_color = color_stops[1] if len(color_stops) > 1 else color_stops[0]
        else:
            # Second half: color[1] to color[2]
            t = (pos - 0.5) * 2
            start_color = color_stops[1] if len(color_stops) > 1 else color_stops[0]
            end_color = color_stops[2] if len(color_stops) > 2 else color_stops[-1]
        
        # Interpolate colors
        r = int(start_color[0] + (end_color[0] - start_color[0]) * t)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * t)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * t)
        
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    
    # Add subtle noise texture
    noise_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    noise_draw = ImageDraw.Draw(noise_overlay)
    
    import random
    random.seed(42)  # Consistent noise pattern
    for _ in range(w * h // 100):  # Sparse noise
        x = random.randint(0, w-1)
        y = random.randint(0, h-1)
        alpha = random.randint(5, 15)
        noise_draw.point((x, y), fill=(255, 255, 255, alpha))
    
    # Combine base gradient with noise
    img = Image.alpha_composite(img.convert("RGBA"), noise_overlay)
    
    # Add radial vignette
    vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vignette_draw = ImageDraw.Draw(vignette)
    
    # Create radial vignette effect
    center_x, center_y = w // 2, h // 2
    max_distance = ((w/2)**2 + (h/2)**2)**0.5
    
    for y in range(0, h, 4):  # Skip pixels for performance
        for x in range(0, w, 4):
            distance = ((x - center_x)**2 + (y - center_y)**2)**0.5
            vignette_strength = min(1.0, (distance / max_distance) * 0.8)
            alpha = int(vignette_strength * 60)  # Max 60 alpha
            vignette_draw.rectangle([x, y, x+3, y+3], fill=(0, 0, 0, alpha))
    
    # Apply vignette
    img = Image.alpha_composite(img, vignette)
    
    # Convert back to RGB and save
    img = img.convert("RGB")
    
    # Enhance contrast slightly
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.1)
    
    # Save to bytes
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=92)
    return output.getvalue()

def _image_to_data_uri(img_bytes: bytes) -> str:
    """Convert image bytes to data URI"""
    return "data:image/jpeg;base64," + base64.b64encode(img_bytes).decode("ascii")

def _cover_resize(img: Image.Image, size: tuple = (1080, 1350)) -> Image.Image:
    """Resize image to cover the given size maintaining aspect ratio"""
    target_width, target_height = size
    source_width, source_height = img.size
    
    # Calculate scaling factor to cover the target area
    scale_x = target_width / source_width
    scale_y = target_height / source_height
    scale = max(scale_x, scale_y)  # Use max to cover (crop excess)
    
    # Calculate new dimensions
    new_width = int(source_width * scale)
    new_height = int(source_height * scale)
    
    # Resize image
    img = img.resize((new_width, new_height), Image.LANCZOS)
    
    # Calculate crop coordinates (center crop)
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height
    
    return img.crop((left, top, right, bottom))

def _download_photo_bytes(url: str) -> Optional[bytes]:
    """Download image from URL with better error handling"""
    if not url or not url.startswith(('http://', 'https://')):
        return None
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 theaipoint/2.0",
        "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache"
    }
    
    try:
        # Handle Unsplash URLs
        if "unsplash.com/photos/" in url:
            download_url = url.rstrip("/") + "/download?force=true&w=1080"
            logging.info(f"Downloading Unsplash image: {download_url}")
            response = requests.get(download_url, headers=headers, timeout=15, stream=True)
            if response.ok and response.headers.get("content-type", "").startswith("image/"):
                return response.content
        
        # Handle Pexels URLs
        elif "pexels.com/photo/" in url:
            logging.info(f"Processing Pexels URL: {url}")
            page_response = requests.get(url, headers=headers, timeout=15)
            if page_response.ok:
                # Extract high-res image URL from page
                import re
                og_image_match = re.search(r'<meta property="og:image" content="([^"]+)"', page_response.text)
                if og_image_match:
                    img_url = og_image_match.group(1)
                    img_response = requests.get(img_url, headers=headers, timeout=15)
                    if img_response.ok and img_response.headers.get("content-type", "").startswith("image/"):
                        return img_response.content
        
        # Handle direct image URLs
        else:
            logging.info(f"Downloading direct image: {url}")
            response = requests.get(url, headers=headers, timeout=15, stream=True)
            if response.ok and response.headers.get("content-type", "").startswith("image/"):
                return response.content
                
    except Exception as e:
        logging.warning(f"Failed to download image from {url}: {e}")
    
    return None

def _process_background_image(title: str, pov: str, image_urls: List[str], theme: Dict[str, Any], is_nano_banana: bool = False, category: str = "general", article_image_url: Optional[str] = None, flux_prompt: Optional[str] = None) -> str:
    """Generate background image using AI-generated Flux prompt. Returns data URI."""

    # 1) Generate using ChatGPT-optimized Flux Schnell prompt
    ai_path = generate_custom_bg(
        title,
        pov,
        is_nano_banana=is_nano_banana,
        category=category,
        article_image_url=article_image_url,
        flux_prompt=flux_prompt
    )
    if ai_path and os.path.exists(ai_path):
        with open(ai_path, "rb") as f:
            logging.info(f"✅ Generated post image ({'Nano Banana' if is_nano_banana else 'Flux Schnell'}) with AI-optimized prompt")
            return _image_to_data_uri(f.read())

    # 2) Fallback: static fallback.jpeg
    fallback_path = os.path.join(os.path.dirname(__file__), "assets", "fallback.jpeg")
    try:
        with open(fallback_path, "rb") as f:
            logging.info("🖼️ Using static fallback.jpeg")
            return _image_to_data_uri(f.read())
    except Exception as e:
        logging.error(f"❌ Could not load fallback.jpeg: {e}")
        return ""

def _generate_smart_cta(category: str, title: str) -> str:
    """Generate contextually relevant CTA text"""
    title_lower = title.lower()
    
    cta_options = {
        "economy": [
            "💬 Impact on your wallet?",
            "📊 What's your take?",
            "💰 Share your thoughts",
            "📈 Good or bad news?"
        ],
        "cricket": [
            "🏏 Who's your MOTM?",
            "🔥 Rate this performance",
            "🎯 Your prediction?",
            "⭐ Share your views"
        ],
        "tech": [
            "🤖 Game changer or hype?",
            "💡 Your thoughts?",
            "🚀 Excited or worried?",
            "⚡ What's your take?"
        ],
        "politics": [
            "🗳️ Agree or disagree?",
            "🎯 Your take on this?",
            "💭 What do you think?",
            "📊 Good move or not?"
        ],
        "disaster": [
            "🙏 Stay safe everyone",
            "❤️ Thoughts and prayers",
            "🆘 Share safety tips",
            "💪 How can we help?"
        ],
        "breaking": [
            "⚡ Your instant reaction?",
            "🔥 What's your view?",
            "💥 Thoughts on this?",
            "⭐ Share your POV"
        ],
        "default": [
            "💭 What's your POV?",
            "🎯 Share your thoughts",
            "💬 Your take on this?",
            "⭐ What do you think?"
        ]
    }
    
    # Get category-specific options
    options = cta_options.get(category, cta_options["default"])
    
    # Simple selection logic (could be made smarter)
    import hashlib
    seed = int(hashlib.md5(title.encode()).hexdigest()[:8], 16)
    return options[seed % len(options)]

def _get_ist_timestamp() -> str:
    """Get current timestamp in IST"""
    now_utc = datetime.utcnow().replace(tzinfo=tz.UTC)
    ist_timezone = tz.gettz("Asia/Kolkata")
    ist_time = now_utc.astimezone(ist_timezone)
    return ist_time.strftime("%d %b %Y, %I:%M %p IST")

def _determine_headline_size(title: str) -> str:
    """Determine appropriate headline size based on title length"""
    length = len(title)
    if length < 50:
        return "h-xl"
    elif length < 70:
        return "h-lg"
    elif length < 90:
        return "h-md"
    else:
        return "h-sm"

async def _render_html_to_image(html_content: str, output_path: pathlib.Path) -> None:
    """Render HTML to 4K image using Playwright with optimized settings"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--font-render-hinting=none',  # Better font rendering
                '--force-color-profile=srgb',  # Better color accuracy
            ]
        )

        try:
            # 4K rendering: deviceScaleFactor=3 for ultra-sharp text
            page = await browser.new_page(
                viewport={"width": 1080, "height": 1350, "deviceScaleFactor": 3}
            )

            # Set content and wait for everything to load
            await page.set_content(html_content, wait_until="networkidle")

            # Wait for fonts and images to fully load
            await page.wait_for_timeout(800)

            # Take 4K screenshot with highest quality
            await page.screenshot(
                path=str(output_path),
                type="jpeg",
                quality=95,  # Higher quality for 4K
                full_page=False,
                omit_background=False
            )
            
            logging.info(f"Successfully rendered image: {output_path}")
            
        finally:
            await browser.close()

def make_post_image(
    title: str,
    pov: str,
    image_urls: List[str] = None,
    hashtags: str = "",
    model_name: str = "claude",
    category: Optional[str] = None,
    cta_text: Optional[str] = None,
    output_filename: Optional[str] = None,
    is_nano_banana: bool = False,
    article_image_url: Optional[str] = None,
    flux_prompt: Optional[str] = None
) -> str:
    """
    Generate a professional social media post image
    
    Args:
        title: Main headline text
        pov: AI Point of View (the key insight)
        image_urls: List of image URLs to try as background
        hashtags: Hashtags for category detection
        model_name: Name of the AI model used
        category: Override category detection
        cta_text: Custom CTA text
        output_filename: Custom output filename
    
    Returns:
        Path to the generated image file
    """
    
    try:
        # Detect category
        detected_category = category or detect_category(title, hashtags, pov)
        theme = THEMES.get(detected_category, THEMES["default"])
        
        logging.info(f"Generating post for category: {detected_category}")
        
        # Process content
        title_clean = title.strip()
        pov_clean = pov.strip()
        pov_clean = re.sub(r"\[\w+\]", "", pov_clean)

        # Get background using AI-generated Flux Schnell prompt
        background_data_uri = _process_background_image(
            title, pov, image_urls or [], theme,
            is_nano_banana=is_nano_banana,
            category=detected_category,
            article_image_url=article_image_url,
            flux_prompt=flux_prompt
        )
        
        # Generate smart CTA
        if not cta_text:
            cta_text = _generate_smart_cta(detected_category, title_clean)
        
        # Get timestamp
        timestamp_ist = _get_ist_timestamp()
        
        # Determine headline size
        headline_size = _determine_headline_size(title_clean)
        
        # Create filename
        if not output_filename:
            slug = re.sub(r"[^a-z0-9]+", "-", title_clean.lower())
            slug = slug.strip("-")[:50] or "post"
            output_filename = f"{slug}-{detected_category}.jpg"
        
        output_path = OUTPUT_DIR / output_filename
        
        # Generate HTML
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>theaipoint - Social Post</title>
  <!-- VIRAL TYPOGRAPHY: Bold, Thick, High-Contrast for Social Media -->
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800;900&family=Inter:wght@500;600;700;800;900&family=Bebas+Neue&display=swap" rel="stylesheet">
  <style>
    :root {
      --w: 1080px; --h: 1350px; --pad: 48px;
      --brand: {{ theme.brand }}; --accent: {{ theme.accent }};
      --brandDark: {{ theme.brandDark }}; --accentDark: {{ theme.accentDark }};
      --fg: #ffffff; --fgMuted: #d1d5db; --fgSecondary: #9ca3af;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    html, body {
      width: var(--w); height: var(--h);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      color: var(--fg); background: #000; overflow: hidden;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      text-rendering: optimizeLegibility;
      image-rendering: -webkit-optimize-contrast;
    }

    .bg-container { position: absolute; inset: 0; overflow: hidden; }
    .bg-image {
      position: absolute; inset: 0;
      background: url("{{ background_data_uri }}") center/cover no-repeat;
      filter: brightness(0.75) contrast(1.1);
    }
    .overlay {
      position: absolute; inset: 0;
      background: linear-gradient(180deg,
        rgba(0,0,0,0.5) 0%,
        rgba(0,0,0,0.25) 30%,
        rgba(0,0,0,0.4) 70%,
        rgba(0,0,0,0.85) 100%);
    }

    .container {
      position: relative; width: 100%; height: 100%; padding: var(--pad);
      display: flex; flex-direction: column; z-index: 10;
    }

    /* Branding - Enhanced */
    .header {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;
    }
    .brand {
      display: flex; flex-direction: column; gap: 4px;
    }
    .brand-text {
      font-family: 'Montserrat', sans-serif;
      font-weight: 900;
      font-size: 42px;
      color: #ffffff;
      letter-spacing: -1px;
      text-shadow: 0 4px 12px rgba(0,0,0,0.95), 0 2px 4px rgba(0,0,0,0.8);
    }
    .tagline {
      font-family: 'Inter', sans-serif;
      font-size: 11px;
      color: var(--brand);
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 3px;
    }

    /* Breaking Badge - NEW */
    .breaking-badge {
      background: linear-gradient(135deg, #ff0000, #ff4444);
      color: #fff; padding: 10px 18px; border-radius: 8px;
      font-weight: 800; font-family: 'DM Sans', sans-serif; font-size: 14px;
      text-transform: uppercase; letter-spacing: 1.5px;
      box-shadow: 0 0 20px rgba(255,0,0,0.5), 0 4px 12px rgba(0,0,0,0.6);
      animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.05); }
    }

    /* Category Pill - Enhanced */
    .category-pill {
      display: inline-flex; align-items: center; gap: 8px;
      background: linear-gradient(135deg, var(--brand), var(--accent));
      padding: 10px 18px; border-radius: 20px;
      font-weight: 700; font-size: 14px; font-family: 'DM Sans', sans-serif;
      text-transform: uppercase; letter-spacing: 0.5px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .category-icon { font-size: 18px; }

    /* Headline - VIRAL OPTIMIZED: Bold, Thick, Punchy */
    .headline {
      font-family: 'Montserrat', sans-serif;
      font-weight: 900;
      line-height: 1.05;
      color: #ffffff;
      letter-spacing: -1.5px;
      margin-bottom: 32px;
      text-shadow: 0 4px 8px rgba(0,0,0,1),
                   0 8px 24px rgba(0,0,0,0.8),
                   0 2px 4px rgba(0,0,0,0.9);
      word-wrap: break-word;
      text-transform: none;
    }
    .h-xl { font-size: 82px; line-height: 1.0; }
    .h-lg { font-size: 72px; line-height: 1.05; }
    .h-md { font-size: 62px; line-height: 1.08; }
    .h-sm { font-size: 52px; line-height: 1.1; }

    /* AI POV Card - VIRAL OPTIMIZED: Bolder, More Prominent */
    .ai-point {
      background: linear-gradient(145deg,
        rgba(0,0,0,0.85) 0%,
        rgba(0,0,0,0.75) 100%);
      backdrop-filter: blur(28px);
      border: 3px solid rgba(255,255,255,0.25);
      border-left: 8px solid var(--brand);
      border-radius: 24px;
      padding: 32px 36px;
      margin-bottom: 32px;
      box-shadow: 0 16px 48px rgba(0,0,0,0.9),
                  inset 0 2px 0 rgba(255,255,255,0.2),
                  0 0 60px rgba(0,0,0,0.6);
      position: relative;
    }
    .ai-point::before {
      content: '';
      position: absolute; top: 0; left: 0; right: 0; height: 3px;
      background: linear-gradient(90deg, var(--brand), transparent);
      opacity: 0.7;
    }
    .ai-label {
      font-family: 'Montserrat', sans-serif;
      font-size: 15px;
      font-weight: 900;
      color: var(--brand);
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 10px;
      text-transform: uppercase;
      letter-spacing: 3px;
      text-shadow: 0 2px 4px rgba(0,0,0,0.8);
    }
    .ai-label::before {
      content: '●';
      font-size: 12px;
      color: var(--brand);
      animation: glow 2s ease-in-out infinite;
    }
    @keyframes glow {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.6; transform: scale(1.15); }
    }
    .ai-content {
      font-family: 'Inter', sans-serif;
      font-size: 28px;
      font-weight: 700;
      line-height: 1.4;
      color: #ffffff;
      letter-spacing: -0.3px;
      text-shadow: 0 2px 4px rgba(0,0,0,0.8);
    }

    /* Metadata - Enhanced */
    .metadata {
      display: flex; align-items: center; gap: 20px;
      margin-top: auto;
    }

    /* Footer - Enhanced with Verification */
    .footer {
      display: flex; justify-content: space-between; align-items: center; margin-top: 28px;
      font-family: 'DM Sans', sans-serif; font-size: 14px; color: var(--fgSecondary);
    }
    .verified-badge {
      display: inline-flex; align-items: center; gap: 6px;
      background: rgba(29, 155, 240, 0.15);
      padding: 6px 12px; border-radius: 20px;
      border: 1px solid rgba(29, 155, 240, 0.3);
      font-size: 13px; font-weight: 600;
    }
    .verified-icon {
      color: #1d9bf0; font-size: 14px; font-weight: 900;
    }

    /* CTA Button - Enhanced with Animation */
    .cta {
      position: absolute; bottom: var(--pad); left: 0; right: 0;
      display: flex; justify-content: center;
    }
    .cta-button {
      background: linear-gradient(135deg, var(--brand), var(--accent));
      color: #fff; padding: 18px 36px;
      font-family: 'DM Sans', sans-serif; font-weight: 700; font-size: 19px;
      border-radius: 50px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.5), 0 0 40px rgba(0,0,0,0.2);
      display: inline-flex; align-items: center; gap: 10px;
      position: relative; overflow: hidden;
    }
    .cta-button::before {
      content: '';
      position: absolute; top: 0; left: -100%;
      width: 100%; height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
      animation: shimmer 3s infinite;
    }
    @keyframes shimmer {
      to { left: 100%; }
    }
    .cta-arrow {
      font-size: 20px;
      animation: bounce 2s ease-in-out infinite;
    }
    @keyframes bounce {
      0%, 100% { transform: translateX(0); }
      50% { transform: translateX(5px); }
    }
  </style>
</head>
<body>
  <div class="bg-container">
    <div class="bg-image"></div>
    <div class="overlay"></div>
  </div>

  <div class="container">
    <header class="header">
      <div class="brand">
        <div class="brand-text">theaipoint</div>
        <div class="tagline">news + ai perspective</div>
      </div>
      {% if category == 'breaking' %}
      <div class="breaking-badge">🚨 BREAKING</div>
      {% endif %}
    </header>

    <main>
      <h1 class="headline {{ headline_size }}">{{ title }}</h1>

      <div class="ai-point">
        <div class="ai-label">AI POINT</div>
        <div class="ai-content">{{ pov }}</div>
      </div>

      <div class="metadata">
        <div class="category-pill">
          <span class="category-icon">{{ icon }}</span>
          <span>{{ category_title }}</span>
        </div>
      </div>
    </main>

    <footer class="footer">
      <span><strong>@theaipoint</strong> — AI news in 30 sec</span>
      <div class="verified-badge">
        <span class="verified-icon">✓</span>
        <span>AI Verified</span>
      </div>
    </footer>

    <div class="cta">
      <div class="cta-button">
        <span>{{ cta_text }}</span>
        <span class="cta-arrow">→</span>
      </div>
    </div>
  </div>
</body>
</html>
"""
        
        # Use Jinja2 to render template
        from jinja2 import Template
        template = Template(html_template)
        
        html_content = template.render(
            title=title_clean,
            pov=pov_clean,
            background_data_uri=background_data_uri,
            model_name=model_name,
            timestamp_ist=timestamp_ist,
            category=detected_category,
            category_title=theme["title"],
            cta_text=cta_text,
            headline_size=headline_size,
            icon=theme["icon"],
            theme=theme
        )
        
        # Render to image
        asyncio.run(_render_html_to_image(html_content, output_path))
        
        logging.info(f"Successfully generated social media post: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logging.error(f"Error generating post image: {e}")
        raise

# Example usage
if __name__ == "__main__":
    # Test with sample data
    test_data = {
        "title": "Breaking: AI chatbot solves climate change with revolutionary carbon capture method 🌍⚡",
        "pov": "This breakthrough could transform how we tackle environmental challenges, showing AI's potential beyond just conversation.",
        "image_urls": [
            "https://images.unsplash.com/photo-1611273426858-450d8e3c9fce?q=80&w=2070",
            # Fallback will be used if this fails
        ],
        "hashtags": "#AI #ClimateChange #TechNews #Innovation",
        "model_name": "claude-sonnet-4",
        "category": "tech"
    }
    
    result = make_post_image(**test_data)
    print(f"Generated image: {result}")