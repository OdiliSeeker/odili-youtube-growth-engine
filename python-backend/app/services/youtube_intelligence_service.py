"""
YouTube Intelligence Engine.

Required environment variables:
  YOUTUBE_API_KEY    — YouTube Data API v3 key (Google Cloud Console)
  YOUTUBE_CHANNEL_ID — YouTube channel ID (e.g. UCxxxxxxxxxxxxxxxx)

Optional:
  OPENAI_API_KEY     — GPT-4o analysis (falls back gracefully if missing/quota exceeded)
"""

import json
import logging
import os
import re
import time
from collections import Counter
from typing import Any

import httpx
from openai import OpenAI

logger = logging.getLogger(__name__)

_YT_BASE = "https://www.googleapis.com/youtube/v3"

# Short-TTL in-memory cache for channel insights. The upstream call is slow
# (YouTube API + GPT-4o, ~15-30s) and the data changes slowly, so we serve a
# cached payload for a few minutes to keep the dashboard snappy and avoid
# burning API quota on repeated refreshes.
_INSIGHTS_CACHE: dict[str, Any] = {"data": None, "expires_at": 0.0, "key": None}
_INSIGHTS_TTL_SECONDS = 300  # 5 minutes

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "it", "my", "your", "we", "they", "this", "that",
    "are", "was", "be", "have", "has", "by", "from", "not", "no", "as",
    "do", "did", "will", "can", "about", "how", "what", "why", "when",
    "who", "all", "you", "our", "its", "i", "am", "up", "he", "she",
    "his", "her", "their", "more", "new", "get", "got", "so", "if", "then",
    "than", "very", "just", "now", "here", "there", "also", "only", "even",
}

_PATTERN_KEYWORDS = [
    "pope", "hell", "quiz", "truth", "catholic", "faith", "heaven",
    "sin", "prayer", "mary", "jesus", "god", "church", "saint",
    "mass", "bible", "confession", "holy", "grace", "soul",
    "devil", "satan", "demon", "miracle", "rosary", "lent",
    "advent", "easter", "christmas", "purgatory", "vatican",
]


# ── helpers ──────────────────────────────────────────────────────────────────

def _extract_keywords(titles: list[str]) -> list[dict]:
    """Count significant words across all titles, excluding common stopwords."""
    tokens: list[str] = []
    for title in titles:
        cleaned = re.sub(r"[^\w\s'-]", " ", title.lower())
        tokens.extend(t for t in cleaned.split() if t not in _STOPWORDS and len(t) > 2)
    counter = Counter(tokens)
    return [{"keyword": k, "count": v} for k, v in counter.most_common(20)]


def _detect_patterns(titles: list[str]) -> list[dict]:
    """Find recurring topic patterns (e.g. 'Pope', 'Hell', 'Quiz') across titles."""
    patterns: list[dict] = []
    for kw in _PATTERN_KEYWORDS:
        matches = [t for t in titles if kw in t.lower()]
        if matches:
            patterns.append({
                "pattern":  kw.title(),
                "count":    len(matches),
                "examples": matches[:3],
            })
    return sorted(patterns, key=lambda p: p["count"], reverse=True)


async def _fetch_videos(channel_id: str, api_key: str) -> list[dict]:
    """
    Fetch the latest 20 public videos from a channel using YouTube Data API v3.
    Makes 3 sequential API calls: channels → playlistItems → videos.
    """
    async with httpx.AsyncClient(timeout=20) as client:
        # 1. Resolve uploads playlist
        ch = await client.get(f"{_YT_BASE}/channels", params={
            "part": "contentDetails",
            "id":   channel_id,
            "key":  api_key,
        })
        ch.raise_for_status()
        ch_items = ch.json().get("items", [])
        if not ch_items:
            raise ValueError(
                f"Channel '{channel_id}' not found — verify YOUTUBE_CHANNEL_ID."
            )
        uploads_id = ch_items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # 2. Get 20 most recent video IDs
        pl = await client.get(f"{_YT_BASE}/playlistItems", params={
            "part":       "contentDetails",
            "playlistId": uploads_id,
            "maxResults": 20,
            "key":        api_key,
        })
        pl.raise_for_status()
        video_ids = [
            item["contentDetails"]["videoId"]
            for item in pl.json().get("items", [])
        ]
        if not video_ids:
            raise ValueError("No videos found in the channel uploads playlist.")

        # 3. Fetch title + statistics for all IDs in one request
        vr = await client.get(f"{_YT_BASE}/videos", params={
            "part": "snippet,statistics",
            "id":   ",".join(video_ids),
            "key":  api_key,
        })
        vr.raise_for_status()

        videos: list[dict] = []
        for v in vr.json().get("items", []):
            snippet = v.get("snippet", {})
            stats   = v.get("statistics", {})
            videos.append({
                "id":           v["id"],
                "title":        snippet.get("title", ""),
                "published_at": snippet.get("publishedAt", ""),
                "views":        int(stats.get("viewCount", 0)),
                "likes":        int(stats.get("likeCount", 0)),
                "url":          f"https://youtu.be/{v['id']}",
            })

        return videos


def _gpt_analyse(
    top_videos: list[dict],
    underperforming: list[dict],
    keywords: list[dict],
    patterns: list[dict],
) -> tuple[dict, str | None]:
    """
    Call GPT-4o to generate:
      - 10 viral topic ideas
      - 5 title improvements for underperforming videos
      - 3 playlist ideas

    Returns (result_dict, error_string_or_None).
    """
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_key:
        return {}, "OPENAI_API_KEY is not set — AI analysis skipped."

    top_block  = "\n".join(
        f"  • {v['title']} ({v['views']:,} views, {v['likes']:,} likes)"
        for v in top_videos
    )
    weak_block = "\n".join(
        f"  • {v['title']} ({v['views']:,} views)"
        for v in underperforming
    )
    kw_list  = ", ".join(k["keyword"] for k in keywords[:15])
    pat_list = ", ".join(f"{p['pattern']} ({p['count']}x)" for p in patterns[:8])

    prompt = f"""You are a YouTube content strategist for Odili Truth Seeker, a Catholic media ministry focused on teaching authentic Catholic faith, defending truth, and engaging popular culture from a Catholic perspective.

TOP-PERFORMING VIDEOS (by views):
{top_block}

UNDERPERFORMING VIDEOS (lowest views):
{weak_block}

RECURRING TITLE KEYWORDS: {kw_list}
TOPIC PATTERNS DETECTED: {pat_list}

Based solely on what is already working for this channel, provide:

1. VIRAL_TOPICS — 10 specific, punchy video ideas that match audience interest patterns. Be concrete (not generic). Each should work as a clickable YouTube title.

2. TITLE_IMPROVEMENTS — Improved titles for each of the 5 underperforming videos listed above. Keep the Catholic subject matter but make the title more compelling and searchable.

3. PLAYLIST_IDEAS — 3 thematic playlist concepts that could group existing and future content. Include a one-sentence description of each.

Respond ONLY with valid JSON in this exact structure (no markdown, no preamble):
{{
  "viral_topics": ["...", "...", "...", "...", "...", "...", "...", "...", "...", "..."],
  "title_improvements": [
    {{"original": "...", "improved": "..."}},
    {{"original": "...", "improved": "..."}},
    {{"original": "...", "improved": "..."}},
    {{"original": "...", "improved": "..."}},
    {{"original": "...", "improved": "..."}}
  ],
  "playlist_ideas": [
    {{"title": "...", "description": "..."}},
    {{"title": "...", "description": "..."}},
    {{"title": "...", "description": "..."}}
  ]
}}"""

    try:
        client   = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.8,
        )
        return json.loads(response.choices[0].message.content), None
    except Exception as exc:
        logger.warning("GPT-4o analysis failed: %s", exc)
        return {}, str(exc)


# ── public API ────────────────────────────────────────────────────────────────

async def get_channel_insights(force_refresh: bool = False) -> dict[str, Any]:
    """
    Fetch the latest 20 videos from the configured YouTube channel,
    analyse performance, and return AI-powered insights.

    Results are cached in-memory for ``_INSIGHTS_TTL_SECONDS`` to keep the
    dashboard responsive; pass ``force_refresh=True`` to bypass the cache.

    Raises ValueError for configuration errors.
    Raises httpx.HTTPStatusError / httpx.RequestError for YouTube API failures.
    """
    api_key    = os.getenv("YOUTUBE_API_KEY", "").strip()
    channel_id = os.getenv("YOUTUBE_CHANNEL_ID", "").strip()

    if not api_key:
        raise ValueError(
            "YOUTUBE_API_KEY is not set. "
            "Create a key at console.cloud.google.com → APIs → YouTube Data API v3."
        )
    if not channel_id:
        raise ValueError(
            "YOUTUBE_CHANNEL_ID is not set. "
            "Find your channel ID at studio.youtube.com → Settings → Channel → Advanced."
        )

    # ── 0. Serve from short-TTL cache when fresh ─────────────────────────────
    now = time.monotonic()
    if (
        not force_refresh
        and _INSIGHTS_CACHE["data"] is not None
        and _INSIGHTS_CACHE["key"] == channel_id
        and now < _INSIGHTS_CACHE["expires_at"]
    ):
        logger.info("Serving channel insights from cache (%.0fs remaining)", _INSIGHTS_CACHE["expires_at"] - now)
        return _INSIGHTS_CACHE["data"]

    # ── 1. Fetch raw video data ──────────────────────────────────────────────
    logger.info("Fetching videos for channel %s", channel_id)
    videos = await _fetch_videos(channel_id, api_key)
    logger.info("Fetched %d videos", len(videos))

    # ── 2. Performance ranking ───────────────────────────────────────────────
    by_views        = sorted(videos, key=lambda v: v["views"], reverse=True)
    top_5           = by_views[:5]
    underperforming = by_views[-5:] if len(by_views) >= 5 else by_views

    # ── 3. Keyword & pattern analysis ────────────────────────────────────────
    all_titles = [v["title"] for v in videos]
    keywords   = _extract_keywords(all_titles)
    patterns   = _detect_patterns(all_titles)

    # ── 4. GPT-4o analysis ───────────────────────────────────────────────────
    gpt_result, ai_note = _gpt_analyse(top_5, underperforming, keywords, patterns)

    result = {
        "channel_id":         channel_id,
        "videos_analysed":    len(videos),
        "top_videos":         top_5,
        "underperforming":    underperforming,
        "keyword_patterns":   keywords,
        "topic_patterns":     patterns,
        "suggested_topics":   gpt_result.get("viral_topics", []),
        "title_improvements": gpt_result.get("title_improvements", []),
        "playlist_ideas":     gpt_result.get("playlist_ideas", []),
        "ai_note":            ai_note,
    }

    _INSIGHTS_CACHE.update(
        data=result,
        key=channel_id,
        expires_at=time.monotonic() + _INSIGHTS_TTL_SECONDS,
    )
    return result


def peek_cached_insights() -> dict[str, Any] | None:
    """
    Return the cached channel-insights payload if one is still fresh, else None.

    Never triggers a network fetch — safe to call from latency-sensitive paths
    (e.g. /youtube/optimize) that should degrade gracefully when no data exists.
    """
    if (
        _INSIGHTS_CACHE["data"] is not None
        and time.monotonic() < _INSIGHTS_CACHE["expires_at"]
    ):
        return _INSIGHTS_CACHE["data"]
    return None
