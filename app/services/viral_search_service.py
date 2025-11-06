"""
Viral News Discovery Service - OpenAI Only
Uses OpenAI to score and select viral-worthy news from diverse RSS feeds
No additional API costs - uses your existing OpenAI key!
"""

import logging
import time
import json
from typing import List, Dict, Any
from openai import OpenAI
import os
import re

logger = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Expanded RSS feeds for viral content discovery
VIRAL_RSS_FEEDS = {
    # Social/Trending News
    "trending": [
        "https://timesofindia.indiatimes.com/rss.cms",
        "https://www.hindustantimes.com/rss/trending/rssfeed.xml",
        "https://www.indiatoday.in/rss/home",
    ],

    # Politics & Controversy (high viral potential)
    "politics": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://indianexpress.com/section/india/feed/",
        "https://www.ndtv.com/india/rss",
    ],

    # Cricket (huge engagement in India)
    "cricket": [
        "https://www.espncricinfo.com/ci/content/rss/feeds/0.xml",
        "https://www.cricbuzz.com/cricket/rss",
        "https://timesofindia.indiatimes.com/rss.cms?sectionId=4719148",
    ],

    # Bollywood/Entertainment (high shareability)
    "entertainment": [
        "https://www.bollywoodhungama.com/rss-feed/",
        "https://www.pinkvilla.com/rss",
        "https://indianexpress.com/section/entertainment/feed/",
    ],

    # Markets/Money (₹ triggers engagement)
    "markets": [
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://www.livemint.com/rss/markets",
        "https://www.moneycontrol.com/rss/MCtopnews.xml",
    ],
}


def discover_viral_news(max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Discover viral-worthy news using OpenAI to analyze diverse RSS feeds

    Strategy:
    1. Fetch from diverse RSS categories (politics, cricket, entertainment, etc.)
    2. Extract 15-20 recent articles
    3. Use OpenAI to score each for viral potential
    4. Select top N with highest viral scores

    Args:
        max_results: Number of viral posts to return

    Returns:
        List of viral news items with scores
    """
    from app.get_rss_feed_data import collect_latest_from_rss, extract_articles_from_links

    logger.info(f"🔥 Discovering viral news using OpenAI (target: {max_results} posts)...")

    # Step 1: Collect diverse RSS articles
    print(f"   📰 Fetching from {len(VIRAL_RSS_FEEDS)} diverse RSS categories...")

    all_rss_items = []
    for category, feeds in VIRAL_RSS_FEEDS.items():
        try:
            items = collect_latest_from_rss(
                feeds_map={category: feeds},
                max_per_feed=2,  # 2 items per category
                hours_window=12,
                try_fetch_missing_ts=True,
                debug=False
            )
            all_rss_items.extend(items)
            print(f"      ✓ {category}: {len(items)} articles")
        except Exception as e:
            logger.warning(f"      ⚠️ {category} failed: {e}")
            continue

    print(f"   📊 Collected {len(all_rss_items)} total articles from RSS")

    if len(all_rss_items) < 5:
        logger.warning(f"   ⚠️ Only {len(all_rss_items)} articles found, may not be enough")
        return []

    # Step 2: Extract article content (limit to 15 for speed/cost)
    urls = []
    seen = set()
    for item in all_rss_items:
        url = item.get("url", "").rstrip("/")
        if url and url not in seen:
            urls.append(url)
            seen.add(url)
            if len(urls) >= 15:  # Limit to 15 articles max
                break

    print(f"   🔗 Extracting full content from {len(urls)} articles...")

    try:
        extracted_articles = extract_articles_from_links(urls, debug=False)
        print(f"   ✅ Extracted {len(extracted_articles)} articles")
    except Exception as e:
        logger.error(f"   ❌ Extraction failed: {e}")
        return []

    if len(extracted_articles) < 3:
        logger.warning(f"   ⚠️ Only {len(extracted_articles)} articles extracted")
        return []

    # Step 3: Use OpenAI to score each article for viral potential
    print(f"   🤖 Analyzing viral potential with OpenAI...")

    viral_candidates = []
    for idx, article in enumerate(extracted_articles, 1):
        try:
            # Score article using OpenAI
            viral_analysis = _score_viral_potential_with_openai(article)

            if viral_analysis and viral_analysis.get("viral_score", 0) >= 60:
                viral_candidates.append({
                    "title": article.get("title", "")[:200],
                    "description": article.get("description_5line", "")[:500],
                    "viral_score": viral_analysis.get("viral_score", 0),
                    "viral_reason": viral_analysis.get("viral_reason", ""),
                    "category": viral_analysis.get("category", "general"),
                    "source": article.get("source", "RSS Feeds"),
                    "article_url": article.get("url", ""),
                    "article_image_url": article.get("top_image_url", "")
                })

                print(f"      ✅ [{idx}/{len(extracted_articles)}] Score {viral_analysis['viral_score']}/100: {article.get('title', '')[:55]}...")
            else:
                score = viral_analysis.get("viral_score", 0) if viral_analysis else 0
                print(f"      ❌ [{idx}/{len(extracted_articles)}] Score {score}/100: Low viral potential")

            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            logger.warning(f"      ⚠️ [{idx}] Error scoring article: {e}")
            continue

    print(f"\n   📊 Found {len(viral_candidates)} viral-worthy articles (score >= 60)")

    # Step 4: Sort by viral score and return top N
    viral_candidates.sort(key=lambda x: x['viral_score'], reverse=True)

    # Deduplicate by title similarity
    unique_viral = _deduplicate_by_title(viral_candidates)

    top_viral = unique_viral[:max_results]

    print(f"   🎯 Selected top {len(top_viral)} viral stories:\n")
    for idx, item in enumerate(top_viral, 1):
        print(f"      {idx}. [{item['viral_score']}/100] {item['title'][:60]}...")

    return top_viral


def _score_viral_potential_with_openai(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use OpenAI to analyze article and score its viral potential

    Returns:
        {
            "viral_score": 0-100,
            "viral_reason": "Why this could go viral",
            "category": "politics|cricket|bollywood|economy|tech|world"
        }
    """

    # Prepare article summary for analysis
    title = article.get("title", "")
    description = article.get("description_5line", article.get("full_text", ""))[:800]

    prompt = f"""Analyze this news article for VIRAL POTENTIAL on Indian social media (Instagram, Twitter, Facebook).

NEWS:
Title: {title}
Description: {description}

VIRAL SCORING CRITERIA (score 0-100):
- Controversy/Scandal: Does it involve conflict, scandal, outrage, backlash? (+30)
- Emotional Trigger: Anger, shock, joy, pride, humor? (+25)
- Celebrity/Sports/Politics: Involves famous people (Virat Kohli, Modi, Shah Rukh Khan, etc.)? (+20)
- Money/Numbers: Mentions ₹ amounts, percentages, dramatic figures? (+15)
- Shareability: Would people share this to express their opinion? (+10)

PENALTIES:
- Boring/routine news (meetings, statements, generic announcements): -30
- Too complex/technical: -20

Respond with JSON only:
{{
  "viral_score": 0-100,
  "viral_reason": "1-2 sentence explanation of why this is/isn't viral-worthy",
  "category": "politics|cricket|bollywood|economy|tech|world|breaking",
  "controversy_level": "high|medium|low",
  "emotion": "anger|shock|joy|pride|humor|neutral"
}}

Examples:
HIGH SCORE (85+): "Virat Kohli dropped from T20 squad—BCCI faces backlash" → Controversy + Celebrity + Emotion
LOW SCORE (30-): "Finance Minister announces new committee meeting" → Boring + No emotion"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a viral content analyzer for Indian social media. Score news objectively for viral potential."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON response
        if content.startswith("```"):
            content = "\n".join(line for line in content.splitlines() if not line.strip().startswith("```"))

        result = json.loads(content)
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e}, content: {content[:100]}")
        return {"viral_score": 0, "viral_reason": "Parse error", "category": "general"}
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return {"viral_score": 0, "viral_reason": "API error", "category": "general"}


def _deduplicate_by_title(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate/similar items based on title similarity
    """
    unique = []
    seen_words = []

    for item in items:
        title = item.get('title', '').lower()
        # Extract key words (ignore common words)
        words = set(re.findall(r'\b\w{4,}\b', title))  # Words with 4+ chars

        # Check if this is too similar to any seen item
        is_duplicate = False
        for seen in seen_words:
            overlap = len(words & seen)
            if overlap >= 3:  # If 3+ words match, consider duplicate
                is_duplicate = True
                break

        if not is_duplicate:
            unique.append(item)
            seen_words.append(words)

    return unique
