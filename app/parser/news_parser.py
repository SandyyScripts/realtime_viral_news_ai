import re, html, logging
from typing import List

URL_RE = re.compile(r'https?://\S+')

def _clean_urls(urls):
    """Keep only usable Unsplash/Pexels photo page URLs, strip trailing punctuation."""
    cleaned = []
    for u in urls:
        u = u.rstrip(').,]>\'"')
        if ('unsplash.com/photos/' in u) or ('pexels.com/photo/' in u):
            cleaned.append(u)
    # De-dupe preserving order
    seen, deduped = set(), []
    for u in cleaned:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped

def parse_news_content(raw_content: str) -> List[dict]:
    """
    Parses LLM output that uses '---' separators and sections:
    📰 Title, 🤖 pov, 🖼️ Stock Images:, #️⃣ Hashtags:, 📌 Source:
    """
    logging.info("Parsing news content...")
    news_items = []
    articles = [a for a in raw_content.strip().split('---') if a.strip()]

    for article_text in articles:
        item = {"images": []}
        article_text = article_text.replace('\\n', '\n').strip()

        # Title
        m = re.search(r'📰(.*?)(?:\n🤖|\n🖼️|#️⃣|📌|$)', article_text, re.DOTALL)
        if m:
            item['title'] = html.escape(m.group(1).strip())

        # pov
        m = re.search(r'🤖(.*?)(?:\n🖼️|#️⃣|📌|$)', article_text, re.DOTALL)
        if m:
            item['pov'] = html.escape(m.group(1).strip())

        # Images
        m = re.search(r'🖼️\s*Stock Images:(.*?)(?:#️⃣|📌|$)', article_text, re.DOTALL | re.IGNORECASE)
        if m:
            item['images'] = _clean_urls(URL_RE.findall(m.group(1)))

        # Hashtags
        m = re.search(r'#️⃣\s*Hashtags:(.*?)(?:📌|$)', article_text, re.DOTALL | re.IGNORECASE)
        if m:
            item['hashtags'] = html.escape(m.group(1).strip())

        # Source
        m = re.search(r'📌\s*Source:(.*)$', article_text, re.DOTALL | re.IGNORECASE)
        if m:
            item['source'] = html.escape(m.group(1).strip())

        news_items.append(item)

    return news_items