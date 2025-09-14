# ---------------- Hard-coded feeds ----------------
from datetime import datetime, timedelta, timezone
import time
import requests
from urllib.parse import urlparse
import feedparser
import re
from dateutil import parser as dateutil_parser
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import json
DEFAULT_FEEDS_MAP = {
  "tech": [
    "https://timesofindia.indiatimes.com/rssfeeds/66949542.cms",
    "https://feeds.feedburner.com/gadgets360-latest",
    "https://timesofindia.indiatimes.com/rssfeeds/5880659.cms",
    "https://www.thehindu.com/sci-tech/feeder/default.rss"
  ],
  "fitness": [
    "https://www.thehindu.com/life-and-style/fitness/feeder/default.rss"
  ],
  "stock_market": [
    "https://www.thehindu.com/business/markets/feeder/default.rss"
  ],
  "astrology": [
    "https://timesofindia.indiatimes.com/rssfeeds/65857041.cms"
  ]
}

IST_OFFSET = timedelta(hours=5, minutes=30)
USER_AGENT = "Mozilla/5.0 (compatible; TheAIPoint/1.0)"
REQUEST_TIMEOUT = 6
POLITE_SLEEP = 0.4

def _parse_iso_or_none(s: str):
    if not s:
        return None
    try:
        dt = dateutil_parser.parse(s, fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None
def _fetch_article_published_time(url: str) -> datetime:
    """Best-effort: fetch article and extract meta published time. Return UTC datetime or None."""
    try:
        headers = {"User-Agent": USER_AGENT}
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # common meta fields
        for meta_prop in ("article:published_time", "article:published", "og:updated_time", "og:published_time"):
            tag = soup.find("meta", property=meta_prop) or soup.find("meta", attrs={"name": meta_prop})
            if tag and tag.get("content"):
                parsed = _parse_iso_or_none(tag["content"])
                if parsed:
                    return parsed
        # look for <time datetime="...">
        t = soup.find("time")
        if t:
            val = t.get("datetime") or t.get_text()
            parsed = _parse_iso_or_none(val)
            if parsed:
                return parsed
        # sometimes in JSON-LD script type="application/ld+json"
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json as _json
                payload = _json.loads(script.string or "{}")
                # try common keys
                for key in ("datePublished", "dateModified", "published", "uploadDate"):
                    if isinstance(payload, dict) and payload.get(key):
                        parsed = _parse_iso_or_none(payload.get(key))
                        if parsed:
                            return parsed
                # if list, try first object
                if isinstance(payload, list) and payload:
                    for obj in payload:
                        if isinstance(obj, dict):
                            for key in ("datePublished", "dateModified"):
                                if obj.get(key):
                                    parsed = _parse_iso_or_none(obj.get(key))
                                    if parsed:
                                        return parsed
            except Exception:
                pass
    except Exception:
        pass
    return None

def collect_latest_from_rss(
    feeds_map: Dict[str, Any],   # values can be str or List[str]
    max_per_feed: int = 3,
    hours_window: int = 8,
    try_fetch_missing_ts: bool = True,
    debug: bool = True
) -> List[Dict[str, Any]]:
    """
    Fetch RSS feeds and return up to `max_per_feed` latest fresh items per interest.

    Params:
      feeds_map: { interest: feed_url_or_list_of_feed_urls, ... }
      max_per_feed: max fresh items to return per interest
      hours_window: rolling window in hours (e.g., 8 or 24)
      try_fetch_missing_ts: if True, fetch article page to attempt to extract published time
      debug: prints debug info

    Returns items like:
      {
        "interest": "politics",
        "title": "...",
        "excerpt": "...",
        "news_time": "ISO UTC string",
        "url": "...",
        "source": "feed title or domain"
      }
    """
    out: List[Dict[str, Any]] = []
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + IST_OFFSET
    threshold_ist = now_ist - timedelta(hours=hours_window)

    if debug:
        print(f">>> Now (IST): {now_ist.isoformat()}")
        print(f">>> Keeping items with IST timestamp >= {threshold_ist.isoformat()} (last {hours_window} hours)\n")

    # normalize feeds_map so each interest maps to a list of candidate feed urls
    normalized_feeds_map: Dict[str, List[str]] = {}
    for interest, value in feeds_map.items():
        if isinstance(value, (list, tuple)):
            normalized_feeds_map[interest] = [str(v).strip() for v in value if v]
        elif isinstance(value, str):
            normalized_feeds_map[interest] = [value.strip()]
        else:
            # unexpected type: skip
            normalized_feeds_map[interest] = []

    for interest, feed_list in normalized_feeds_map.items():
        if debug:
            print(f"\n>>> Processing interest='{interest}' with {len(feed_list)} feed candidates")
        kept_for_interest: List[Dict[str, Any]] = []
        seen_titles = set()

        # iterate candidate feeds until we have enough fresh items
        for feed_url in feed_list:
            if len(kept_for_interest) >= max_per_feed:
                break

            if not feed_url:
                continue

            if debug:
                print(f"  -> Trying feed: {feed_url}")

            try:
                d = feedparser.parse(feed_url)
            except Exception as e:
                if debug:
                    print(f"    feedparser error for {feed_url}: {e}")
                continue

            feed_title = (getattr(d, "feed", {}) and d.feed.get("title")) or interest

            entries = d.entries or []
            if not entries:
                if debug:
                    print(f"    empty feed: {feed_url}")
                continue

            # process entries newest-first (feedparser usually returns newest first but ensure ordering)
            for e in entries:
                if len(kept_for_interest) >= max_per_feed:
                    break

                title = (e.get("title") or "").strip()
                if not title:
                    continue
                title_key = re.sub(r"\s+", " ", title.lower()).strip()
                if title_key in seen_titles:
                    continue
                # compute or skip duplicate
                # we'll only mark as seen when we actually keep it, so we don't block other fresher duplicates across feeds

                url = e.get("link") or ""
                excerpt = (e.get("summary") or e.get("description") or "").strip()
                excerpt = re.sub(r"<[^>]+>", "", excerpt).strip()

                # parse published fields
                news_dt_utc = None
                for fld in ("published", "published_parsed", "updated", "updated_parsed", "pubDate"):
                    if e.get(fld):
                        try:
                            if fld.endswith("_parsed"):
                                t = e.get(fld)
                                news_dt_utc = datetime(*t[:6], tzinfo=timezone.utc)
                            else:
                                news_dt_utc = _parse_iso_or_none(e.get(fld))
                            break
                        except Exception:
                            news_dt_utc = None

                fetched_note = ""
                if not news_dt_utc and try_fetch_missing_ts and url:
                    try:
                        fetched = _fetch_article_published_time(url)
                        if fetched:
                            news_dt_utc = fetched
                            fetched_note = " (fetched ts)"
                    except Exception:
                        news_dt_utc = None

                if not news_dt_utc:
                    if debug:
                        print(f"    SKIP (no timestamp): {title!r} -> {url}")
                    continue

                # convert to IST and check window
                news_dt_ist = news_dt_utc + IST_OFFSET
                if news_dt_ist < threshold_ist or news_dt_ist > now_ist:
                    if debug:
                        print(f"    SKIP (outside window): {title!r}")
                        if debug:
                            print(f"      news IST: {news_dt_ist.isoformat()} vs threshold {threshold_ist.isoformat()}")
                    continue

                # Passed freshness filter — keep it
                item = {
                    "interest": interest,
                    "title": title,
                    "excerpt": excerpt,
                    "news_time": news_dt_utc.isoformat(),  # UTC ISO normalized
                    "url": url,
                    "source": (feed_title or (urlparse(url).netloc if url else ""))
                }
                kept_for_interest.append(item)
                seen_titles.add(title_key)
                if debug:
                    print(f"    KEEP: {title!r} at {news_dt_ist.isoformat()}{fetched_note}")

            # polite pause between feed fetches
            time.sleep(0.12)

        # final sort newest-first and trim to max_per_feed
        kept_for_interest.sort(key=lambda x: x.get("news_time") or "", reverse=True)
        if kept_for_interest:
            out.extend(kept_for_interest[:max_per_feed])
        else:
            if debug:
                print(f"  WARNING: No fresh items found for interest='{interest}' across provided feeds.")

    if debug:
        print(f"\n>>> Collected {len(out)} fresh items across interests\n")
    return out


def fetch_html(url: str):
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text, r.url


def _clean_text(s: str) -> str:
    if not s:
        return ""
    # remove excessive whitespace and repeated newlines; keep paragraph breaks
    s = re.sub(r"\r", " ", s)
    s = re.sub(r"\n\s*\n+", "\n\n", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = s.strip()
    return s

def _lead_from_text(full_text: str, max_sentences: int = 5) -> str:
    if not full_text:
        return ""
    # naive sentence split good enough for social copy
    sentences = re.split(r'(?<=[\.\?\!])\s+', full_text.strip())
    lead = " ".join(sentences[:max_sentences]).strip()
    # if lead is empty (very short text), fallback to truncated full text
    if not lead:
        return (full_text[:500] + "...") if len(full_text) > 500 else full_text
    return lead

def _detect_paywall(soup) -> bool:
    text = " ".join([t.get_text(" ", strip=True) for t in soup.find_all(["div","p","section"])[:30]])
    paywall_signs = ["subscribe to read", "subscribe to continue", "sign in to continue", "you are reading a premium article"]
    text_low = text.lower()
    return any(sig in text_low for sig in paywall_signs)

# === normalize paragraphs, dedupe, cut unrelated sections ===
def _normalize_and_dedupe_full_text(raw: str, max_chars: int = 30000) -> str:
    if not raw:
        return ""
    # split into paragraphs (preserve order)
    paras = [p.strip() for p in re.split(r'\n\s*\n+', raw) if p.strip()]
    # remove exact/near-duplicate paragraphs while preserving order
    seen = set()
    deduped = []
    for p in paras:
        key = p[:300]  # use prefix as signature (keeps memory small)
        key_norm = re.sub(r'\s+', ' ', key).lower()
        if key_norm in seen:
            continue
        seen.add(key_norm)
        deduped.append(p)

    # join but stop if we hit common "related" or footer markers
    stop_markers = [
        "related stories", "also read", "read more", "you may like",
        "join our", "subscribe to", "follow us on", "advertisement", "download the app",
        "team india sponsor", "go beyond the boundary", "subscribe now"
    ]
    out_paras = []
    for p in deduped:
        low = p.lower()
        # if paragraph looks like a small UI copy (subscribe/read more), stop
        if any(marker in low for marker in stop_markers):
            break
        out_paras.append(p)

    final = "\n\n".join(out_paras).strip()
    # collapse huge content
    if max_chars and len(final) > max_chars:
        final = final[:max_chars].rsplit("\n", 1)[0]  # avoid chopping mid-paragraph
    return final
def extract_description(url: str) -> Dict[str, Any]:
    """
    Robust article extraction:
      - returns title, url, source, published_at (UTC ISO or None),
        description_5line (lead), and full_text.
    - Uses newspaper3k if available; otherwise falls back to BeautifulSoup heuristics.
    """
    html, final_url = fetch_html(url)  # uses your existing fetch_html (requests)
    soup = BeautifulSoup(html, "html.parser")

    # 1) Try newspaper3k (best-effort, optional)
    full_text = ""
    title = ""
    published_iso: Optional[str] = None
    canonical = final_url or url

    try:
        from newspaper import Article
        a = Article(final_url)
        a.download(input_html=html)
        a.parse()
        # strong preference to use newspaper3k parsed content if available
        if getattr(a, "text", None) and len(a.text.strip()) > 50:
            full_text = a.text.strip()
            title = a.title or title
            canonical = getattr(a, "canonical_link", canonical) or canonical
            # publish_date may be naive
            pd = getattr(a, "publish_date", None)
            if pd:
                try:
                    if pd.tzinfo is None:
                        pd = pd.replace(tzinfo=timezone.utc)
                    published_iso = pd.astimezone(timezone.utc).isoformat()
                except Exception:
                    published_iso = None
    except Exception:
        # newspaper not installed or failed — fall back to heuristics
        pass

    # 2) If newspaper failed to get text, use heuristics
    if not full_text:
        # title: prefer og:title then <title>
        og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "title"})
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        # prefer <article> first
        article_tag = soup.find("article")
        if article_tag:
            paras = [p.get_text(" ", strip=True) for p in article_tag.find_all("p") if p.get_text(strip=True)]
            full_text = "\n\n".join(paras).strip()
        else:
            # schema.org articleBody or itemprop
            article_body = soup.find(attrs={"itemprop": "articleBody"}) or soup.find(attrs={"name": "articleBody"})
            if article_body:
                paras = [p.get_text(" ", strip=True) for p in article_body.find_all("p") if p.get_text(strip=True)]
                full_text = "\n\n".join(paras).strip()
            else:
                # JSON-LD may contain article body or headline
                try:
                    for script in soup.find_all("script", type="application/ld+json"):
                        try:
                            payload = json.loads(script.string or "{}")
                            if isinstance(payload, dict):
                                if not title and payload.get("headline"):
                                    title = payload.get("headline")
                                # try articleBody or articleSection
                                if payload.get("articleBody"):
                                    full_text = payload.get("articleBody")
                                    break
                                if payload.get("articleBody") is None and payload.get("articleBody") is None:
                                    pass
                        except Exception:
                            continue
                except Exception:
                    pass

                # fallback: longest contiguous paragraph block heuristic
                if not full_text:
                    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
                    if paragraphs:
                        # choose the longest window up to N paras (heuristic)
                        best = ""
                        # limit window to 10 paras to avoid huge joins
                        for i in range(len(paragraphs)):
                            joined = "\n\n".join(paragraphs[i: i + 10])
                            if len(joined) > len(best):
                                best = joined
                        full_text = best or paragraphs[0]
                    else:
                        full_text = ""

    full_text = _clean_text(full_text or "")
    full_text = _normalize_and_dedupe_full_text(full_text, max_chars=30000)
    # fallback short description from meta tags if article body is tiny
    if not full_text:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            full_text = og_desc["content"].strip()
        else:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                full_text = meta_desc["content"].strip()

    # published_at: try meta tags, <time>, JSON-LD
    if not published_iso:
        # meta/property
        meta_dt = soup.find("meta", property="article:published_time") or soup.find("meta", attrs={"name": "pubdate"})
        if meta_dt and meta_dt.get("content"):
            try:
                dt = dateutil_parser.parse(meta_dt.get("content"), fuzzy=True)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                published_iso = dt.astimezone(timezone.utc).isoformat()
            except Exception:
                published_iso = None
        # check <time>
        if not published_iso:
            time_tag = soup.find("time")
            if time_tag:
                val = time_tag.get("datetime") or time_tag.get_text()
                try:
                    dt = dateutil_parser.parse(val, fuzzy=True)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    published_iso = dt.astimezone(timezone.utc).isoformat()
                except Exception:
                    published_iso = None
        # JSON-LD
        if not published_iso:
            try:
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        payload = json.loads(script.string or "{}")
                        if isinstance(payload, dict) and payload.get("datePublished"):
                            dt = dateutil_parser.parse(payload.get("datePublished"), fuzzy=True)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            published_iso = dt.astimezone(timezone.utc).isoformat()
                            break
                    except Exception:
                        continue
            except Exception:
                pass

    # description_5line: lead from full_text (3-5 sentences)
    description_5line = _lead_from_text(full_text, max_sentences=5)
    # paywall detection (flag only)
    is_paywalled = _detect_paywall(soup)

    source = urlparse(final_url or url).netloc.lower()

    return {
        "title": (title or "")[:300],
        "url": final_url or url,
        "source": source,
        "published_at": published_iso,
        "description_5line": description_5line or "",
        "full_text": full_text or "",
        "is_paywalled": is_paywalled
    }
import traceback
def extract_articles_from_links(urls: List[str], debug: bool = True) -> List[Dict[str, Any]]:
    """
    Synchronous extraction (simple). Returns list of article dicts.
    You can easily parallelize this function with ThreadPoolExecutor if desired.
    """
    out: List[Dict[str, Any]] = []
    for u in urls:
        if debug:
            print(f"\n>>> Extracting: {u}")
        try:
            art = extract_description(u)
            out.append(art)
            if debug:
                # keep prints concise
                print(json.dumps({
                    "title": art.get("title"),
                    "url": art.get("url"),
                    "published_at": art.get("published_at"),
                    "source": art.get("source"),
                    "is_paywalled": art.get("is_paywalled")
                }, indent=2, ensure_ascii=False))
        except Exception as e:
            traceback.print_exc()
            print("  !! Error extracting", u, e)
        time.sleep(POLITE_SLEEP)
    return out
# ---------------- Test Flow ----------------
if __name__ == "__main__":
    import json

    interests = ["politics", "cricket", "bollywood", "tech", "stock_market", "travel", "fashion"]
    MAX_PER_INTEREST = 3
    MAX_EXTRACT_URLS = 8

    print("\nSTEP 0: Using hard-coded curated feeds (DEFAULT_FEEDS_MAP)")
    feeds_map_for_collection = {i: DEFAULT_FEEDS_MAP[i] for i in interests if i in DEFAULT_FEEDS_MAP}

    print("\nSTEP 1: Collect latest RSS items (fresh, deduped)")
    collected = collect_latest_from_rss(
        feeds_map=feeds_map_for_collection,
        max_per_feed=MAX_PER_INTEREST,
        hours_window=8,
        try_fetch_missing_ts=True,
        debug=True
    )

    print(f"\nCollected total items: {len(collected)}")

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

    print("\nSTEP 2: Extract article descriptions")
    extracted = extract_articles_from_links(urls, debug=True)

    print("\n=== FINAL OUTPUT ===")
    print(json.dumps(extracted, indent=2, ensure_ascii=False))