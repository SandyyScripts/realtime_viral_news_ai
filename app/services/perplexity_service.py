import requests
import time
import json
import logging
from typing import Any, Dict, List, Union
from app.config import PERPLEXITY_MODEL, PPLX_API_KEY
from app.get_rss_feed_data import extract_articles_from_links,collect_latest_from_rss

def redact(api_key):
    if api_key:
        return f"{api_key[:4]}...{api_key[-4:]}"
    return "Not set"


DEFAULT_FEEDS_MAP = {
  "tech": [
    "https://indianexpress.com/section/technology/feed/",
    "https://feeds.feedburner.com/gadgets360-latest",
    "https://timesofindia.indiatimes.com/rssfeeds/5880659.cms",
    "https://www.thehindu.com/sci-tech/feeder/default.rss"
  ],
  "stock_market": [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "https://feeds.feedburner.com/ndtvprofit-latest",
    "https://indianexpress.com/section/business/feed/"
  ],
  "travel": [
    "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
    "https://indianexpress.com/section/travel/feed/",
    "https://www.news18.com/rss/travel.xml"
  ],
  "fashion": [
    "https://timesofindia.indiatimes.com/rssfeeds/2886704.cms",
    "https://indianexpress.com/section/lifestyle/feed/",
    "https://www.hindustantimes.com/feeds/rss/lifestyle/rssfeed.xml"
  ]
}

def transform_rss_with_perplexity() -> List[Dict[str, Any]]:
    """
    For each RSS news item, call Perplexity and build final array.

    Changed behavior:
      - Fetch 5 stories from Times of India Top Stories RSS
      - Fetch 1 story each from 4 other categories (first 4 keys present in DEFAULT_FEEDS_MAP)
      - Dedupe URLs, limit to MAX_EXTRACT_URLS when extracting article content
      - Rest of pipeline unchanged (extract_articles_from_links -> call_perplexity_on_news)
    """
    # configurable constants
    TOPSTORIES_URL = "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"
    NUM_TOPSTORIES = 5
    NUM_OTHER_CATEGORIES = 4   # one each from 4 other categories
    ONE_PER_CATEGORY = 1
    MAX_EXTRACT_URLS = 8  # keep from your original flow

    # Determine which other categories to use (preserve insertion order of DEFAULT_FEEDS_MAP)
    available_categories = [k for k in DEFAULT_FEEDS_MAP.keys() if k]
    # exclude any accidental 'topstories' key if present
    other_categories = available_categories[:NUM_OTHER_CATEGORIES]

    # 1) Fetch top stories (5) using the collect function
    top_feed_map = {"topstories": [TOPSTORIES_URL]}
    top_items = collect_latest_from_rss(
        feeds_map=top_feed_map,
        max_per_feed=NUM_TOPSTORIES,
        hours_window=8,
        try_fetch_missing_ts=True,
        debug=False
    )

    # 2) Fetch 1 item each from the chosen other categories (if they exist in DEFAULT_FEEDS_MAP)
    other_feed_map = {}
    for cat in other_categories:
        feeds = DEFAULT_FEEDS_MAP.get(cat)
        if feeds:
            other_feed_map[cat] = feeds

    other_items = []
    if other_feed_map:
        other_items = collect_latest_from_rss(
            feeds_map=other_feed_map,
            max_per_feed=ONE_PER_CATEGORY,
            hours_window=8,
            try_fetch_missing_ts=True,
            debug=False
        )

    # 3) Combine top + other, dedupe by URL, and build a URL list to extract articles from.
    combined = []
    combined.extend(top_items)
    combined.extend(other_items)

    urls = []
    seen_urls = set()
    for it in combined:
        u = it.get("url")
        if not u:
            continue
        # simple normalization of URL to avoid tiny variants (strip trailing slash)
        u_norm = u.rstrip("/")
        if u_norm in seen_urls:
            continue
        seen_urls.add(u_norm)
        urls.append(u_norm)
        if len(urls) >= MAX_EXTRACT_URLS:
            break

    # 4) Extract article contents from urls (reuses your existing extractor)
    rss_items = extract_articles_from_links(urls, debug=False)

    # 5) Call Perplexity/transform step for each extracted article and keep valid news
    out = []
    for item in rss_items:
        try:
            transformed = call_perplexity_on_news(item)
            is_valid = transformed.get("is_valid_news", False)
            if is_valid:
                out.append(transformed)
        except Exception as e:
            # keep the original behavior of printing errors
            print(f"❌ Error on item: {item.get('title')} -> {e}")
        time.sleep(1)  # polite pause

    return out


def call_perplexity_on_news(news_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Perplexity for one news item and return the transformed object.
    """
    prompt = f"""
    You are the Chief Editor for "theaipoint" – India's premier AI-powered news platform. 
    Your job: write engaging, fact-based social media posts that hook readers while staying responsible.

    NEWS INPUT:
    {json.dumps(news_item, ensure_ascii=False)}

    GUIDELINES:
    - Headline:
    * Serious/sensitive (deaths, disasters, violence, policy): calm, professional, NO emojis otherwise Use power words: "SHOCKING", "EXCLUSIVE", "BREAKING", "MASSIVE" Breaking/tech/positive/sports: punchy, scroll-stopping, GenZ flavor allowed ✅ (⚡🔥🚀).
    * Keep it factual, max 15-18 words.
    - Hashtags: 4-5 max that are trending on twitter/X for this news or topic
    - Never sensationalize tragedies. Never invent facts.

    📰 HEADLINE FORMULA:
    - Hook + Key Detail + Impact (≤20 words)
    - Avoid mentioning TV channels/media outlets
    - Focus on human impact, not corporate jargon
    
    🤖 AI ANALYSIS FRAMEWORK:
    Create a sharp, data-driven perspective that answers:
    - WHY should Indians care RIGHT NOW?
    - WHAT are the hidden implications?
    - WHO benefits/loses from this?
    - Connect to broader trends affecting common people
    - Use specific numbers, percentages, comparisons
    - Limit: 45-50 words maximum
    - Cite only verifiable sources in [brackets]
    
    #️⃣ HASHTAG STRATEGY:
    - Mix trending + niche tags for maximum reach
    - Include 1 branded tag (#TheAIPoint or #AIAnalysis)
    - 4-5 total hashtags
    - Research current trending topics
    
    📌 SOURCE CREDIBILITY:
    - Verify through 2+ independent Indian sources
    - Prefer: PTI, ANI, major newspapers, official statements
    - Avoid: Unverified social media, opinion blogs
    - Note LLM model used for transparency
    
    VIRAL CONTENT CHECKLIST:
    ✅ Emotional trigger (anger, surprise, hope, fear)
    ✅ Relatable to middle-class Indians
    ✅ Shareable without controversy
    ✅ Clear call-to-action or discussion starter
    ✅ Factually accurate and balanced


    OUTPUT FORMAT (JSON):
    {{
    "title": "Catchy headline (emoji only if appropriate)",
    "pov": "Balanced, GenZ-friendly analysis with verified context [Source1][Source2]",
    "hashtags": ["#IndiaNews", "#TopicTag", "#ResponsibleJournalism"],
    "source": "Verified sources + AI analysis",
    "is_valid_news": true/false,
    "category": "breaking/politics/economy/technology/health/sports/positive",
    "news_sensitivity": "high/medium/low",
    "editorial_tone": "serious/professional/engaging",
    "public_interest_score": 1-10,
    "verification_confidence": "high/medium/low"
    }}
    """

    headers = {
        "Authorization": f"Bearer {PPLX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    body = {
        "model": PERPLEXITY_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": "You are an expert social media news editor. Create viral, factual content for Indian audiences. Be concise, engaging, and maintain journalistic integrity."
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,  # Add creativity while maintaining accuracy
        "max_tokens": 1000
    }

    try:
        resp = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=body, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        # Extract and clean content
        content = data["choices"][0]["message"]["content"]
        content = content.strip()
        
        # Remove markdown formatting if present
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        parsed_data = json.loads(content)
        
        # Ensure required fields exist
        required_fields = ["title", "pov", "hashtags", "source", "is_valid_news", "category"]
        for field in required_fields:
            if field not in parsed_data:
                parsed_data[field] = "" if field != "is_valid_news" else False
                
        return parsed_data
        
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return {"title": news_item.get("title", ""), "is_valid_news": False, "error": str(e)}
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        return {"title": news_item.get("title", ""), "is_valid_news": False, "error": "Invalid JSON response"}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"title": news_item.get("title", ""), "is_valid_news": False, "error": str(e)}

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
