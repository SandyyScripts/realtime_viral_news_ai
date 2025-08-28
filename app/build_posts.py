# app/build_posts.py
import re, logging
from typing import List, Dict, Optional
from pathlib import Path
from app.generate_image import make_post_image

logging.basicConfig(level=logging.INFO)

URL_RE = re.compile(r"https?://\S+")

def _clean_url(u: str) -> Optional[str]:
    """Keep only Unsplash/Pexels photo page URLs; strip trailing punctuation & parenthetical notes."""
    # remove inline comments like: https://... (voting)
    u = u.strip()
    # take only the first URL on the line
    m = URL_RE.search(u)
    if not m:
        return None
    u = m.group(0)
    # trim trailing punctuation
    u = u.rstrip(").,]>’”'\"")
    # accept only photo pages
    if "unsplash.com/photos/" in u or "pexels.com/photo/" in u:
        return u
    return None

def parse_llm_news(raw: str) -> List[Dict]:
    """
    Parse LLM output into structured items.
    Supports blocks separated by *** or --- and flexible whitespace.
    """
    # unify separators
    chunks = re.split(r"(?:^\*{3,}\s*$|^-{3,}\s*$)", raw, flags=re.MULTILINE)
    items: List[Dict] = []

    for ch in (c for c in chunks if c and c.strip()):
        text = ch.strip()

        # title
        m = re.search(r"^📰\s*(.+)", text, flags=re.MULTILINE)
        title = m.group(1).strip() if m else None

        # pov/comment
        m = re.search(r"^🤖\s*theaipoint:\s*(.+)", text, flags=re.MULTILINE | re.IGNORECASE)
        pov = m.group(1).strip() if m else None

        # image block: collect subsequent lines after "🖼️"
        imgs: List[str] = []
        img_block = re.search(r"^🖼️.*?(?:\n+(.+?))(?:\n\s*#️⃣|\n\s*📌|$)", text, flags=re.DOTALL | re.MULTILINE)
        if img_block:
            for line in img_block.group(1).splitlines():
                u = _clean_url(line)
                if u:
                    imgs.append(u)

        # hashtags: capture all lines after "#️⃣ Hashtags:" until next section/end
        hashtags = ""
        h = re.search(r"#️⃣\s*Hashtags:\s*(.+?)(?:\n\s*📌|$)", text, flags=re.DOTALL | re.IGNORECASE)
        if h:
            hashtags = re.sub(r"\n\s*-\s*", "\n- ", h.group(1).strip())

        # source (optional)
        src = ""
        s = re.search(r"📌\s*Source:\s*(.+)$", text, flags=re.DOTALL | re.IGNORECASE)
        if s:
            src = s.group(1).strip()

        if title or pov or imgs:
            items.append({
                "title": title or "",
                "pov": pov or "",
                "images": imgs,
                "hashtags": hashtags,
                "source": src,
            })

    return items

def build_images_from_llm(raw: str, model_name: str = "sonar-online") -> List[Path]:
    """
    Parse LLM text and generate one social image per item.
    Returns list of output image paths.
    """
    posts = parse_llm_news(raw)
    outputs: List[Path] = []
    for i, p in enumerate(posts, 1):
        title = p["title"] or f"theaipoint post #{i}"
        pov   = p["pov"] or "Why it matters for you."
        imgs  = p["images"] or []  # generate_image has a dark fallback
        tags  = p["hashtags"] or ""
        out = make_post_image(
            title=title,
            pov=pov,
            image_urls=imgs,
            hashtags=tags,
            model_name=model_name,
            category="trending"
        )
        logging.info(f"[{i}/{len(posts)}] Saved {out}")
        outputs.append(Path(out))
    return outputs