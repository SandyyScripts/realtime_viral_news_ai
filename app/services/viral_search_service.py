"""
Viral News Search Service
Uses Perplexity API to discover trending, controversial, and viral-worthy news
"""

import logging
import time
from typing import List, Dict, Any
from app.config import PPLX_API_KEY, PERPLEXITY_MODEL
from app.services.perplexity_service import call_perplexity, extract_text
import json
import re

logger = logging.getLogger(__name__)


def search_viral_news(max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search for viral-worthy news using Perplexity API with trending queries

    Args:
        max_results: Maximum number of viral news items to return

    Returns:
        List of viral news items with viral_score, title, description, source, category
    """
    logger.info(f"🔥 Searching for viral news (target: {max_results} posts)...")

    # Viral-focused search queries
    search_queries = [
        "What's trending on Twitter India right now today most viral controversial",
        "Most controversial political news India today angry people reactions",
        "Shocking news India today that went viral social media",
        "Reddit India hot discussions trending topics past 12 hours",
        "Indian cricket latest controversy drama news today viral",
        "Bollywood breaking scandal gossip trending social media India today",
        "Stock market crash rise shocking India today investors reactions",
        "Unpopular opinion trending India social media today hot takes"
    ]

    all_viral_candidates = []

    # Execute searches and collect results
    for idx, query in enumerate(search_queries[:6], 1):  # Limit to 6 searches to control cost
        try:
            logger.info(f"  🔍 Query {idx}/6: {query[:60]}...")

            # Call Perplexity with viral-focused prompt
            result = call_perplexity(
                prompt=f"""{query}

Requirements:
- Only news from past 12 hours
- Focus on viral/trending/controversial stories
- Include social media reaction context
- Provide 1-2 specific news items with:
  * Title
  * Brief description (2-3 sentences)
  * Why it's viral/trending
  * Source
  * Category (politics/cricket/bollywood/economy/tech/world)

Format as JSON array:
[
  {{
    "title": "...",
    "description": "...",
    "viral_reason": "...",
    "source": "...",
    "category": "politics|cricket|bollywood|economy|tech|world"
  }}
]
""",
                model=PERPLEXITY_MODEL,
                retries=2,
                timeout=45
            )

            if result:
                text = extract_text(result)
                parsed_items = _parse_viral_response(text)

                if parsed_items:
                    logger.info(f"    ✅ Found {len(parsed_items)} viral candidates")
                    all_viral_candidates.extend(parsed_items)
                else:
                    logger.info(f"    ⚠️ No items parsed from response")
            else:
                logger.warning(f"    ⚠️ No result from query")

            # Polite rate limiting
            time.sleep(1.5)

        except Exception as e:
            logger.error(f"    ❌ Error in query {idx}: {e}")
            continue

    logger.info(f"\n📊 Total viral candidates collected: {len(all_viral_candidates)}")

    # Score and rank viral potential
    scored_candidates = []
    for item in all_viral_candidates:
        score = _calculate_viral_score(item)
        item['viral_score'] = score
        scored_candidates.append(item)

    # Sort by viral score (highest first) and deduplicate
    scored_candidates.sort(key=lambda x: x['viral_score'], reverse=True)

    # Deduplicate by title similarity
    unique_items = _deduplicate_by_title(scored_candidates)

    # Return top N with highest viral scores
    top_viral = unique_items[:max_results]

    logger.info(f"🎯 Selected {len(top_viral)} top viral stories:")
    for idx, item in enumerate(top_viral, 1):
        logger.info(f"  {idx}. [{item['viral_score']}/100] {item.get('title', '')[:70]}...")

    return top_viral


def _parse_viral_response(text: str) -> List[Dict[str, Any]]:
    """
    Parse Perplexity response to extract viral news items
    Handles both JSON and text formats
    """
    items = []

    # Try JSON parsing first
    try:
        # Look for JSON array in the text
        json_match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict) and item.get('title')]
    except json.JSONDecodeError:
        pass

    # Fallback: try to parse text format
    # Look for patterns like "Title:", "Description:", etc.
    sections = re.split(r'\n\s*\n+', text)
    current_item = {}

    for section in sections:
        lines = section.strip().split('\n')
        for line in lines:
            line = line.strip()

            # Match key-value patterns
            if ':' in line:
                parts = line.split(':', 1)
                key = parts[0].strip().lower()
                value = parts[1].strip() if len(parts) > 1 else ''

                if 'title' in key and value:
                    if current_item:  # Save previous item
                        items.append(current_item)
                    current_item = {'title': value}
                elif 'description' in key and value:
                    current_item['description'] = value
                elif 'viral' in key or 'trending' in key or 'reason' in key:
                    current_item['viral_reason'] = value
                elif 'source' in key and value:
                    current_item['source'] = value
                elif 'category' in key and value:
                    current_item['category'] = value.lower()

    if current_item and current_item.get('title'):
        items.append(current_item)

    # If still no items, try extracting from general text
    if not items and len(text) > 50:
        # Extract first meaningful paragraph as a news item
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]
        if paragraphs:
            items.append({
                'title': paragraphs[0][:200],
                'description': paragraphs[0] if len(paragraphs) == 1 else paragraphs[1][:500],
                'viral_reason': 'Trending search result',
                'source': 'Multiple sources',
                'category': 'general'
            })

    return items


def _calculate_viral_score(item: Dict[str, Any]) -> int:
    """
    Calculate viral potential score (0-100) based on multiple factors
    """
    score = 50  # Base score

    title = (item.get('title', '') + ' ' + item.get('description', '')).lower()
    viral_reason = item.get('viral_reason', '').lower()

    # Controversy indicators (+20)
    controversy_words = ['shocking', 'controversial', 'scandal', 'outrage', 'viral', 'trending',
                         'angry', 'protest', 'backlash', 'slammed', 'criticized', 'drama']
    if any(word in title or word in viral_reason for word in controversy_words):
        score += 20

    # Emotion triggers (+15)
    emotion_words = ['shock', 'anger', 'fury', 'rage', 'amazing', 'incredible', 'stunning',
                     'unbelievable', 'insane', 'wild', 'crazy']
    if any(word in title for word in emotion_words):
        score += 15

    # Numbers/data points (+10)
    if re.search(r'₹|crore|lakh|\d+%|\d+cr|\d+L', title):
        score += 10

    # Social proof (+15)
    social_words = ['twitter', 'reddit', 'viral', 'trending', 'social media', 'reactions', 'netizens']
    if any(word in title or word in viral_reason for word in social_words):
        score += 15

    # Celebrity/Cricket/Politics (high engagement categories) (+10)
    high_engagement = ['virat', 'dhoni', 'rohit', 'modi', 'rahul gandhi', 'shah rukh',
                       'salman', 'rbi', 'bcci', 'ipl', 'bollywood']
    if any(name in title for name in high_engagement):
        score += 10

    # Negative score for boring words (-20)
    boring_words = ['meeting', 'conference', 'statement', 'announces', 'inaugurates']
    if any(word in title for word in boring_words):
        score -= 20

    # Has viral reason (+10)
    if item.get('viral_reason') and len(item['viral_reason']) > 10:
        score += 10

    # Clamp score between 0-100
    return max(0, min(100, score))


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
