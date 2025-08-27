import os, io, re, asyncio, hashlib, logging, base64, textwrap, pathlib, requests
from datetime import datetime
from dateutil import tz
from typing import Optional, List
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright
from PIL import Image

logging.basicConfig(level=logging.INFO)

# --- paths relative to this file (works no matter where you run it) ---
HERE = pathlib.Path(__file__).resolve().parent
TEMPLATES_DIR = HERE / "templates"          # expects post.html inside this folder
OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

def _slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60] or "post"

def _image_to_data_uri(img_bytes: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(img_bytes).decode("ascii")

def _cover_resize(img: Image.Image, size=(1080, 1350)) -> Image.Image:
    tw, th = size
    sw, sh = img.size
    tr = tw / th
    sr = sw / sh
    if sr > tr:
        nh = th
        nw = int(sr * nh)
    else:
        nw = tw
        nh = int(nw / sr)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))

def _download_photo_bytes(url: str) -> Optional[bytes]:
    """Resolve Unsplash/Pexels photo page to actual image bytes."""
    headers = {"User-Agent": "Mozilla/5.0 theaipoint/1.0"}
    try:
        if "unsplash.com/photos/" in url:
            dl = url.rstrip("/") + "/download?force=true"
            r = requests.get(dl, headers=headers, timeout=20)
            if r.ok and r.headers.get("content-type", "").startswith("image/"):
                return r.content
        elif "pexels.com/photo/" in url:
            html = requests.get(url, headers=headers, timeout=20).text
            m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
            if m:
                img_url = m.group(1)
                r = requests.get(img_url, headers=headers, timeout=20)
                if r.ok and r.headers.get("content-type", "").startswith("image/"):
                    return r.content
    except Exception as e:
        logging.warning(f"Could not fetch {url}: {e}")
    return None

def _pick_background_data_uri(photo_urls: List[str]) -> str:
    for u in photo_urls:
        b = _download_photo_bytes(u)
        if not b:
            continue
        try:
            im = Image.open(io.BytesIO(b)).convert("RGB")
            im = _cover_resize(im, (1080, 1350))
            out = io.BytesIO()
            im.save(out, format="JPEG", quality=90)
            return _image_to_data_uri(out.getvalue())
        except Exception as e:
            logging.warning(f"Image processing failed for {u}: {e}")
    # dark fallback
    fallback = Image.new("RGB", (1080, 1350), (18, 18, 22))
    out = io.BytesIO()
    fallback.save(out, format="JPEG", quality=85)
    return _image_to_data_uri(out.getvalue())

async def _render_html_to_image(html_str: str, out_path: pathlib.Path):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 1080, "height": 1350, "deviceScaleFactor": 2}
        )
        await page.set_content(html_str, wait_until="load")
        await page.wait_for_timeout(300)
        await page.screenshot(path=str(out_path), type="jpeg", quality=90)
        await browser.close()

def make_post_image(
    title: str,
    pov: str,
    image_urls: List[str],
    hashtags: str,
    model_name: str,
    category: str = "trending",
) -> str:
    bg_data_uri = _pick_background_data_uri(image_urls)

    now_utc = datetime.utcnow().replace(tzinfo=tz.UTC)
    ist = tz.gettz("Asia/Kolkata")
    ts_ist = now_utc.astimezone(ist).strftime("%d %b %Y, %I:%M %p IST")

    template = env.get_template("post.html")
    html_rendered = template.render(
        title=title.strip(),
        pov=textwrap.shorten(pov.strip(), width=180, placeholder="…"),
        background_data_uri=bg_data_uri,
        hashtags=hashtags.strip(),
        model_name=model_name,
        timestamp_ist=ts_ist,
        category=category,
    )

    slug = _slugify(title)
    out_img = OUTPUT_DIR / f"{slug}.jpg"
    asyncio.run(_render_html_to_image(html_rendered, out_img))
    logging.info(f"Saved: {out_img}")
    return str(out_img)

# --- quick manual test ---
if __name__ == "__main__":
    item = {
        "title": "Rupee slides to ₹84.6/$ — travel & iPhones get pricier 💸",
        "pov": "Dollar up, wallet down. Expect pricier imports and OTT subscriptions.",
        "images": [
            "https://unsplash.com/photos/8manzosRGPE",
            "https://www.pexels.com/photo/close-up-photography-of-indian-rupee-banknotes-164686/",
        ],
        "hashtags": "#rupee #economy #financeindia #dollar #inflation #moneymatters #trendingindia",
        "model_name": "sonar-online",
    }
    make_post_image(
        title=item["title"],
        pov=item["pov"],
        image_urls=item["images"],
        hashtags=item["hashtags"],
        model_name=item["model_name"],
        category="finance",
    )