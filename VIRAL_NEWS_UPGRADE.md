# 🔥 Viral News Upgrade - Hybrid RSS + AI Search

## What Changed?

Your news generation system has been upgraded from **10 RSS-only posts** to a **hybrid system** that generates **5 highly targeted posts**:

- **2 Trending RSS Posts** - Verified news from established sources
- **3 Viral Search Posts** - Discovered using AI-powered search for trending/controversial content

## Why This Matters

### Before (RSS Only - 10 posts)
- ❌ 6-12 hours behind breaking news
- ❌ Same news as major outlets (competing with Times of India, NDTV)
- ❌ No controversy/viral angle detection
- ❌ 0 followers in 2 months

### After (Hybrid - 5 posts)
- ✅ Real-time viral/trending detection
- ✅ Controversial angles automatically found
- ✅ Social proof (what's already trending on Twitter/Reddit)
- ✅ Higher engagement potential (emotional triggers, shock value, controversy)

## New Architecture

```
┌─────────────────────────────────────────────────┐
│          CONTENT DISCOVERY                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  📰 RSS Feeds (2 posts)                         │
│  ├─ Top Stories                                 │
│  ├─ World News                                  │
│  ├─ Markets                                     │
│  ├─ Bollywood                                   │
│  └─ Cricket                                     │
│                                                 │
│  🔥 Viral Search (3 posts)                      │
│  ├─ Twitter India trending                      │
│  ├─ Controversial political news                │
│  ├─ Shocking viral stories                      │
│  ├─ Reddit India hot discussions                │
│  ├─ Cricket/Bollywood drama                     │
│  └─ Stock market reactions                      │
│                                                 │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│         VIRAL SCORING ENGINE                    │
│  - Controversy detection (+20 pts)              │
│  - Emotional triggers (+15 pts)                 │
│  - Social proof/trending (+15 pts)              │
│  - Numbers/data points (+10 pts)                │
│  - Celebrity/Cricket/Politics (+10 pts)         │
│  - Boring words penalty (-20 pts)               │
│  └─> Score 0-100, keep only 70+                 │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│         POST GENERATION                         │
│  - ChatGPT transforms to viral format           │
│  - Power hooks in headlines                     │
│  - Punchy AI Point (25-35 words)                │
│  - Viral hashtags (no generic tags)             │
│  - Professional image generation                │
└─────────────────────────────────────────────────┘
```

## New Files Added

### 1. `app/services/viral_search_service.py`
**Main viral discovery engine**

Key functions:
- `search_viral_news(max_results=3)` - Main entry point
- `_calculate_viral_score(item)` - Scores viral potential 0-100
- `_parse_viral_response(text)` - Extracts news from Perplexity results
- `_deduplicate_by_title(items)` - Removes similar stories

### 2. `app/services/perplexity_service.py` (MODIFIED)
**Updated to hybrid approach**

Changes:
- `transform_rss_with_perplexity()` now returns 5 posts (was 10)
- Selects top 2 trending RSS posts (by recency)
- Calls `search_viral_news()` for 3 viral posts
- Graceful fallback to RSS if viral search fails

## Viral Scoring Algorithm

Each news item is scored 0-100 based on:

| Factor | Points | Examples |
|--------|--------|----------|
| **Controversy** | +20 | "shocking", "scandal", "outrage", "backlash", "viral" |
| **Emotion** | +15 | "shock", "fury", "amazing", "incredible", "insane" |
| **Social Proof** | +15 | "twitter", "reddit", "viral", "trending", "#1" |
| **Numbers/Data** | +10 | "₹5 crore", "50%", "10x increase" |
| **High-Engagement** | +10 | Virat Kohli, Modi, Shah Rukh Khan, RBI, BCCI |
| **Boring Words** | -20 | "meeting", "conference", "statement" |

**Minimum threshold:** 70/100 to be included

## Search Queries Used

The system runs 6 viral-focused searches:

1. `"What's trending on Twitter India right now most viral controversial"`
2. `"Most controversial political news India today angry people reactions"`
3. `"Shocking news India today that went viral social media"`
4. `"Reddit India hot discussions trending topics past 12 hours"`
5. `"Indian cricket latest controversy drama news today viral"`
6. `"Bollywood breaking scandal gossip trending social media India today"`

## API Requirements

### Required Environment Variables

```bash
# OpenAI (for content transformation)
OPENAI_API_KEY=sk-...

# Perplexity (for viral search - NEW!)
PERPLEXITY_API_KEY=pplx-...
PERPLEXITY_MODEL=pplx-7b-online  # Default, or use pplx-70b-online for better results

# Email (unchanged)
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_TO=recipient@example.com

# Image generation (unchanged)
NEBIUS_API_KEY=...  # OR GOOGLE_API_KEY
```

### Cost Estimate

**Before:** ~$5-10/month (OpenAI only)

**After:** ~$40-50/month
- OpenAI (content transformation): ~$10/month
- Perplexity API (6 searches per run): ~$30-40/month
  - Per search: ~$0.05-0.08
  - Per run (6 searches): ~$0.30-0.50
  - Daily runs: ~$9-15/month
  - Plus retry/error margin

**ROI:** One viral post (10K+ reach) can get 500-1000 followers = $0.04-0.08 per follower (cheaper than Instagram ads at $0.50-$2 per follower)

## Expected Results

### Engagement Metrics

| Metric | Before (RSS Only) | After (Hybrid) |
|--------|------------------|----------------|
| Posts per run | 10 | 5 (more focused) |
| Engagement rate | <1% | 5-15% expected |
| Viral posts/week | 0 | 1-2 expected |
| Follower growth | 0 in 2 months | 500-2K/month expected |

### Content Mix

- **40%** RSS (credibility anchor) - verified news
- **60%** Viral Search (engagement driver) - controversial/trending

## How to Use

### Run Normally
```bash
python app/main.py
```

The system automatically:
1. Fetches 7 RSS articles
2. Selects top 2 trending
3. Searches for 3 viral stories
4. Transforms all 5 with ChatGPT
5. Generates images
6. Sends email digest

### Graceful Degradation

If viral search fails:
- ✅ Falls back to additional RSS posts
- ✅ Ensures you always get 5 posts minimum
- ✅ No pipeline breakage

### Monitor Performance

Watch the logs for:
```
🔍 Starting HYBRID news curation (2 RSS + 3 Viral Search = 5 total)...
📰 PART 1: Fetching top 2 trending RSS posts...
🔥 PART 2: Fetching top 3 viral posts from search...
🎯 FINAL SELECTION: 5 posts ready
   📰 RSS Posts: 2
   🔥 Viral Posts: 3
```

## Viral Score Breakdown Examples

### High Score (90/100) - VIRAL
```
Title: "Shock: Virat Kohli dropped from T20 squad—BCCI's ₹15cr dilemma"

Scoring:
+20 Controversy ("shock", "dropped")
+15 Emotion ("shock")
+15 Social proof (trending topic)
+10 Numbers (₹15cr)
+10 High engagement (Virat Kohli, BCCI)
+20 Base
= 90/100 ✅ SELECTED
```

### Low Score (40/100) - REJECTED
```
Title: "Finance Minister announces new banking regulations"

Scoring:
+50 Base
-20 Boring ("announces", "regulations")
+10 Category (finance)
= 40/100 ❌ REJECTED
```

## Troubleshooting

### Issue: "Missing PERPLEXITY_API_KEY"
**Solution:** Get API key from https://www.perplexity.ai/settings/api
```bash
export PERPLEXITY_API_KEY=pplx-xxxxx
```

### Issue: "No viral posts found"
**Possible causes:**
1. API rate limit hit (wait 1 hour)
2. No trending news at that moment (normal, try later)
3. Network issues

**Fallback:** System automatically uses more RSS posts

### Issue: Cost too high
**Solutions:**
1. Reduce search frequency (run twice daily instead of hourly)
2. Use cheaper Perplexity model: `PERPLEXITY_MODEL=pplx-7b-online`
3. Reduce search queries from 6 to 3 (edit `viral_search_service.py` line 29)

## Customization

### Adjust Viral Thresholds

Edit `app/services/viral_search_service.py`:

```python
# Line 141-169: Adjust scoring weights
controversy_words = ['shocking', 'controversial', ...]  # Add your keywords
score += 25  # Increase from 20 to make controversy more important
```

### Add More Search Queries

Edit `app/services/viral_search_service.py`:

```python
# Line 22-30: Add new queries
search_queries = [
    "What's trending on Twitter India right now",
    "Your custom query here",  # ADD THIS
]
```

### Change RSS vs Viral Ratio

Edit `app/services/perplexity_service.py`:

```python
# Line 78-80
TARGET_RSS_POSTS = 3     # Change from 2 to 3
TARGET_VIRAL_POSTS = 2   # Change from 3 to 2
TARGET_TOTAL = 5         # Keep total = 5
```

## What's Next?

Recommended enhancements:
1. **Analytics Dashboard** - Track which posts go viral
2. **A/B Testing** - Test different headline styles
3. **Auto-posting** - Schedule posts to Instagram/Twitter
4. **Sentiment Analysis** - Detect anger/joy/shock emotions
5. **Reddit/Twitter API Integration** - Direct trending detection

## Support

Created as part of the viral news upgrade initiative.

For questions or issues, check the logs or review:
- `app/services/viral_search_service.py` - Viral search logic
- `app/services/perplexity_service.py` - Main orchestration
- `app/main.py` - Entry point (unchanged)
