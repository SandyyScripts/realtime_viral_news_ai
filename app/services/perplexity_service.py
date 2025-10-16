import requests
import time
import json
import logging
from typing import Any, Dict, List, Union,Optional
from app.config import PERPLEXITY_MODEL, PPLX_API_KEY
from app.get_rss_feed_data import extract_articles_from_links,collect_latest_from_rss
import os
from openai import OpenAI

def redact(api_key):
    if api_key:
        return f"{api_key[:4]}...{api_key[-4:]}"
    return "Not set"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Replace your old DEFAULT_FEEDS_MAP with this
DEFAULT_FEEDS_MAP = {
    # ========== TOP (pick 6) ==========
    # Broader coverage + mix of national dailies, digital-first outlets & wire feeds
    "top_stories": [
        # national dailies / broad coverage
        "https://timesofindia.indiatimes.com/rss.cms",                    # Times of India (Top feeds index)
        "https://www.thehindu.com/news/national/feeder/default.rss",     # The Hindu - National
        "https://indianexpress.com/feed/",                               # Indian Express - Top
        "https://www.hindustantimes.com/rss/topnews/rssfeed.xml",        # Hindustan Times - Top
        # digital-first / analysis
        "https://www.livemint.com/rss/homepage",                         # Mint - homepage
        "https://www.ndtv.com/rss/news",                                 # NDTV - Top news
        # agency / aggregator (helps reduce duplication caused by syndication)
        "https://www.aninews.in/feed/",                                  # ANI - agency
    ],

    # ========== WORLD (pick 1) ==========
    "world": [
        "https://www.thehindu.com/news/international/feeder/default.rss", # The Hindu - International
        "https://www.bbc.co.uk/feeds/rss/world.xml",                      # BBC World (India-relevant international lens)
        "https://www.aljazeera.com/xml/rss/all.xml",                      # Al Jazeera - world
    ],

    # ========== STOCKS / MARKETS (pick 1) ==========
    "stocks": [
        "https://www.livemint.com/rss/markets",                            # Mint - Markets
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", # Economic Times - Markets
        "https://www.business-standard.com/rss/markets-economy.rss",       # Business Standard - Markets
        "https://www.moneycontrol.com/rss/MCtopnews.xml",                  # Moneycontrol top news (markets)
    ],

    # ========== BOLLYWOOD / ENTERTAINMENT (pick 1) ==========
    "bollywood": [
        "https://www.bollywoodhungama.com/rss-feed/",                      # Bollywood Hungama
        "https://www.filmfare.com/feeds/latest.xml",                       # Filmfare - latest
        "https://www.pinkvilla.com/rss",                                   # Pinkvilla (entertainment)
        "https://indianexpress.com/section/entertainment/feed/",           # Indian Express - Entertainment section
    ],

    # ========== CRICKET / SPORTS (pick 1) ==========
    "cricket": [
        "https://www.espncricinfo.com/ci/content/rss/feeds/0.xml",          # ESPNcricinfo - Global news / cricket
        "https://www.cricbuzz.com/cricket/rss",                            # Cricbuzz - Cricket news
        "https://www.thehindu.com/sport/cricket/feeder/default.rss",       # The Hindu - Cricket
        "https://timesofindia.indiatimes.com/rss.cms?sectionId=4719148",   # TOI - Sports (fallback)
    ],
}

def transform_rss_with_perplexity() -> List[Dict[str, Any]]:
    """
    SIMPLE news curation: Always return exactly 10 posts

    Strategy:
      - 6 from top stories (main news)
      - 1 from world news
      - 1 from stock market
      - 1 from Bollywood
      - 1 from cricket
      = 10 posts guaranteed
    """
    # SIMPLE STRATEGY - Fixed allocation for predictable output
    STORIES_PER_CATEGORY = {
        "top_stories": 6,   # Main top stories (politics, economy, breaking, etc.)
        "world": 1,         # International news
        "stocks": 1,        # Stock market/finance
        "bollywood": 1,     # Entertainment
        "cricket": 1,       # Sports/cricket
    }

    MAX_EXTRACT_URLS = 10  # Exactly 10 articles
    TARGET_POSTS = 10      # Always return 10 posts
    HOURS_WINDOW = 12      # Wider window to ensure we get content

    print(f"\n🔍 Starting news curation (fetching from {len(STORIES_PER_CATEGORY)} categories)...")

    # 1) Fetch stories from each category based on priority
    all_items = []
    for category, count in STORIES_PER_CATEGORY.items():
        feeds = DEFAULT_FEEDS_MAP.get(category)
        if not feeds:
            continue

        category_items = collect_latest_from_rss(
            feeds_map={category: feeds},
            max_per_feed=count,
            hours_window=HOURS_WINDOW,
            try_fetch_missing_ts=True,
            debug=False
        )
        all_items.extend(category_items)
        print(f"  ✓ {category}: {len(category_items)} stories")

    print(f"\n📰 Collected {len(all_items)} total stories")

    # 2) Dedupe by URL and limit to MAX_EXTRACT_URLS
    # Also build a map for fallback when 403 blocked
    urls = []
    rss_items_map = {}
    seen_urls = set()
    for it in all_items:
        u = it.get("url")
        if not u:
            continue
        u_norm = u.rstrip("/")
        if u_norm in seen_urls:
            continue
        seen_urls.add(u_norm)
        urls.append(u_norm)
        rss_items_map[u_norm] = it  # Store for fallback
        if len(urls) >= MAX_EXTRACT_URLS:
            break

    print(f"🔗 Extracting {len(urls)} unique articles...")

    # 3) Extract article contents with RSS fallback for 403 errors
    rss_items = extract_articles_from_links(urls, debug=False)

    print(f"📝 Extracted {len(rss_items)} articles, now scoring with AI...")

    # 4) Transform ALL articles with AI (NO rejection, always get 10 posts)
    transformed_news = []
    for idx, item in enumerate(rss_items, 1):
        try:
            transformed = call_chatgpt_on_news(item)

            # Preserve article metadata
            transformed["article_image_url"] = item.get("top_image_url", "")
            transformed["article_url"] = item.get("url", "")

            transformed_news.append(transformed)
            print(f"  ✅ [{idx}/{len(rss_items)}] Transformed: {transformed.get('title', '')[:70]}...")

        except Exception as e:
            print(f"  ⚠️ [{idx}/{len(rss_items)}] ERROR: {e}")
            # Still try to include the raw article if AI fails
            transformed_news.append({
                "title": item.get("title", "")[:100],
                "pov": item.get("description_5line", "")[:200],
                "hashtags": "#TheAIPoint #News #India",
                "image_generation_prompt": "news background abstract, professional journalism, modern editorial",
                "source": item.get("source", ""),
                "category": "general",
                "article_image_url": item.get("top_image_url", ""),
                "article_url": item.get("url", ""),
            })

        time.sleep(0.8)  # Polite pause

    print(f"\n🎯 FINAL SELECTION: {len(transformed_news)} posts ready")
    return transformed_news



def call_chatgpt_on_news(news_item, model="gpt-4o-mini"):
    # Compress news item to essential fields only (save tokens)
    compact_news = {
        "title": news_item.get("title", "")[:200],
        "description": news_item.get("description_5line", news_item.get("full_text", ""))[:600],
        "source": news_item.get("source", ""),
        "published": news_item.get("published_at", "")
    }

    prompt = f"""NEWS: {json.dumps(compact_news, ensure_ascii=False)}

Create social media post for Indian audience. Output JSON only.

=== 1. HEADLINE (≤18 words) ===
REWRITE with power hooks to grab attention like it is written by a Senior Journalist who knows the audience and knows how to convey a news story in a way that will grab attention.
Use: ₹/crore/lakh, Indian cities/people
✅ "Shock: EMI jumps ₹2,400/month—RBI move hits 4cr borrowers"
❌ "Government Announces Policy" (boring)

=== 2. AI POINT (50-70 words) ===
WRITE LIKE A FAMOUS INDIAN JOURNALIST explaining news to common people over chai.

CRITICAL: For statement/controversy news, QUOTE THE EXACT STATEMENT from the article.

FLOW NATURALLY (don't use labels like [CONTEXT] or [TAKE]):
- What happened (1-2 lines, simple)
- Who's affected + real impact with numbers/facts
- What mainstream media isn't highlighting
- Your unbiased analysis as senior journalist

RAW NEWS TOUCH: Include exact quotes, actual numbers, real statements when available.

✅ "RBI raised rates 0.25%—your ₹50L home loan EMI jumps ₹2,400/month. 4cr borrowers feeling the pinch to control inflation. Here's what they won't tell you: banks will earn ₹18,000cr extra annually while common man pays. My take: Necessary for long-term stability, yes, but why do citizens always bear the burden while bank profits soar?"

✅ "Amit Shah said 'surgical strikes sent a clear message to Pakistan'—this statement sparked massive debate in Parliament. Opposition claims credit for policy continuity since 2008, government says execution matters. Real story: 200 surgical strikes happened pre-2014, but branding changed the narrative. Unbiased take: Both sides politicizing military operations isn't healthy for national security discourse."

✅ "Virat dropped from T20 after poor form. Captain with most wins now sidelined. BCCI facing ₹15cr salary dilemma vs investing in youth like Gill and Jaiswal. My view: Tough but right call—every legend's era ends, but selection transparency needed for fans who've supported him 15 years."

❌ "Many people will be affected. This is an important decision. We'll have to wait and see." (lazy, no insight, no quotes)

=== 3. HASHTAGS (5 total) ===
ALWAYS start with: #TheAIPoint
Then add 4 RELEVANT hashtags from news content
Rules:
- Use specific keywords from headline (not generic #News #India #Breaking)
- Include topic-specific tags (e.g., #RBI #Rupee #Economy OR #Virat #Cricket #BCCI)
- Mix popular + niche tags
- Avoid Generic Hastags and think of hastags that can go viral and improve my reach

EXAMPLES:
✅ RBI news: "#TheAIPoint #RBI #InterestRates #HomeLoan"
✅ Cricket: "#TheAIPoint #Virat #BCCI #IndianCricket"
✅ Bollywood: "#TheAIPoint #Bollywood #BoxOffice #ShahRukh"
✅ Stocks: "#TheAIPoint #Sensex #StockMarket #Investing"
❌ "#TheAIPoint #News #India #Trending" (too generic)

=== 4. IMAGE PROMPT (60-90 words) ===
Flux Schnell prompt for THIS news:
[Subject]: Specific visual | [Mood]: tone | [Colors]: palette | [Lighting]: dramatic | [Quality]: 4K photorealistic | NO faces/text/logos

EXAMPLES:
✅ "Dark money briefcase, broken handcuffs, courthouse pillars, side lighting, red/black, crisis mood, 4K photorealistic, NO faces/text"
✅ "Cricket stadium floodlights, empty armband on blue jersey, melancholic, blue/saffron, spotlight, 4K, NO faces/text"
✅ "₹ symbol falling through red charts, financial skyline blurred, red/black, dramatic lighting, 4K, NO faces/text"

JSON: {{"title":"...","pov":"...","hashtags":"#TheAIPoint #Specific #Relevant #Tags","image_generation_prompt":"...","source":"...","category":"politics|cricket|bollywood|economy|tech|world|disaster|positive","news_sensitivity":"low|medium|high"}}

Return ONLY valid JSON. NO rejection - transform every news."""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are TheAIPoint's AI editor. Transform ALL news into engaging social posts with unique insights and RELEVANT hashtags. Always output valid JSON. Never reject."},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=450,
        temperature=0.7
    )

    content = resp.choices[0].message.content.strip()
    if content.startswith("```"):
        # strip code fences
        content = "\n".join(line for line in content.splitlines() if not line.strip().startswith("```"))
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"is_valid_news": False, "error": "Invalid JSON", "raw": content}

# Using Union for type hinting for compatibility with Python < 3.10
def call_perplexity(prompt: str, model: str = PERPLEXITY_MODEL, retries: int = 3, timeout: int = 60) -> Union[dict, None]:
    if not PPLX_API_KEY or PPLX_API_KEY == "REPLACE_ME":
        logging.error("Missing PERPLEXITY_API_KEY (set as env var).")
        return None

    url = "https://api.perplexity.ai/chat/completions"
    headers = { "Authorization": f"Bearer {PPLX_API_KEY}", "Content-Type": "application/json" }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Be precise, concise. India audience."},
            {"role": "user", "content": prompt},
        ],
    }

    logging.info("👉 Calling Perplexity…")
    logging.info(f"   URL: {url}")
    logging.info(f"   Model: {model}")
    logging.info(f"   Auth: {redact(PPLX_API_KEY)}")
    logging.info(f"   Prompt: {(prompt[:180] + '…') if len(prompt) > 180 else prompt}")

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=timeout)
            logging.info(f"   HTTP {resp.status_code}")
            if resp.status_code >= 400:
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                    sleep_s = 2 ** (attempt - 1)
                    logging.warning(f"   Transient error; retrying in {sleep_s}s…")
                    time.sleep(sleep_s)
                    continue
                resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logging.error(f"   Attempt {attempt}/{retries} failed: {e}")
            if attempt == retries:
                raise
    return None

def extract_text(data: dict) -> str:
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as e:
        logging.error(f"Error extracting text from Perplexity response: {e}")
        # fallback: return readable JSON
        return json.dumps(data, indent=2)
