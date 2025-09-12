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
  "politics": [
    "https://indianexpress.com/feed/",
    "https://indianexpress.com/section/politics/feed/",
    "https://feeds.feedburner.com/ndtvnews-latest",
    "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "https://www.thehindu.com/news/national/feeder/default.rss",
    "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    "https://www.news18.com/rss/india.xml"
  ],
  "cricket": [
    "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms",
    "https://indianexpress.com/section/sports/feed/",
    "https://www.cricbuzz.com/rss/news"
  ],
  "bollywood": [
    "https://timesofindia.indiatimes.com/rssfeedstopstories.cms?cat=entertainment",
    "https://indianexpress.com/section/entertainment/feed/",
    "https://feeds.feedburner.com/ndtventertainment-latest",
    "https://www.hindustantimes.com/feeds/rss/entertainment/rssfeed.xml"
  ],
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
    """
    interests = ["politics", "cricket", "bollywood", "tech", "stock_market", "travel", "fashion"]
    MAX_PER_INTEREST = 3
    MAX_EXTRACT_URLS = 8

    feeds_map_for_collection = {i: DEFAULT_FEEDS_MAP[i] for i in interests if i in DEFAULT_FEEDS_MAP}

    collected = collect_latest_from_rss(
        feeds_map=feeds_map_for_collection,
        max_per_feed=MAX_PER_INTEREST,
        hours_window=8,
        try_fetch_missing_ts=True,
        debug=False
    )

    urls = []
    seen_urls = set()
    for it in collected:
        u = it.get("url")
        if not u or u in seen_urls:
            continue
        seen_urls.add(u)
        urls.append(u)
        if len(urls) >= MAX_EXTRACT_URLS:
            break

    rss_items = extract_articles_from_links(urls, debug=False)

    out = []
    for item in rss_items:
        try:
            transformed = call_perplexity_on_news(item)
            is_valid = transformed.get("is_valid_news", False)
            if is_valid:
                out.append(transformed)
        except Exception as e:
            print(f"❌ Error on item: {item.get('title')} -> {e}")
        time.sleep(1)  # polite pause

    return out


def call_perplexity_on_news(news_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Perplexity for one news item and return the transformed object.
    """
    prompt = f"""
        You are the lead content strategist for "theaipoint" - India's fastest-growing AI-powered news platform that creates viral, fact-based content.

        News Input:
        {json.dumps(news_item, ensure_ascii=False)}

        CONTENT CREATION GUIDELINES:
        
        📰 HEADLINE FORMULA:
        - Hook + Key Detail + Impact (≤20 words)
        - Use power words: "SHOCKING", "EXCLUSIVE", "BREAKING", "MASSIVE"
        - Include 1-2 strategic emojis (🚨⚡🔥💥📢🎯)
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
        
        OUTPUT FORMAT - Respond ONLY with JSON:
        {{
            "title": "Viral headline with emojis",
            "pov": "AI analysis with cited sources [1][2]",
            "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4", "#TheAIPoint"],
            "source": "Primary source + LLM model",
            "is_valid_news": true/false,
            "category": "breaking/politics/tech/economy/sports/trending",
            "virality_score": 1-10,
            "engagement_hook": "Discussion starter question"
        }}
        
        CONTENT QUALITY STANDARDS:
        - Unbiased reporting with AI-powered insights
        - No sensationalism without facts
        - Represent multiple perspectives when relevant
        - Focus on solutions, not just problems
        - Indian context and local relevance priority
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
