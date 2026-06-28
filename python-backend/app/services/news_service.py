"""
Catholic news intelligence layer.

Fetches recent headlines from trusted Catholic news sources (Vatican News,
Catholic News Agency, EWTN/CNA) to enrich content ideas and email hooks with
current, real-world relevance.

Rules (enforced by callers, documented here):
  - News is SUPPORTIVE context only, never a doctrinal authority.
  - Never override defined Catholic doctrine with news commentary.

Design: a single in-memory cache (30 min TTL) keeps the dashboard snappy and is
resilient to source outages — a failed fetch never raises to the caller; it
falls back to the last good cache (or an empty list with a note).
"""

import asyncio
import logging
import time
from typing import Any
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)

# Trusted Catholic RSS sources. Order = display priority.
_SOURCES = [
    ("Vatican News", "https://www.vaticannews.va/en.rss.xml"),
    ("Catholic News Agency", "https://www.catholicnewsagency.com/rss/news.xml"),
    ("EWTN / CNA", "https://www.catholicnewsagency.com/rss/vatican.xml"),
]

_CACHE: dict[str, Any] = {"data": None, "expires_at": 0.0}
_TTL_SECONDS = 1800  # 30 minutes
_PER_SOURCE_LIMIT = 6
_TOTAL_LIMIT = 18


def _strip(text: str | None) -> str:
    return (text or "").strip()


def _parse_feed(source: str, xml_text: str) -> list[dict]:
    """Parse an RSS/Atom feed into a list of {source, title, link, published}."""
    items: list[dict] = []
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        logger.warning("Could not parse feed from %s: %s", source, exc)
        return items

    # RSS 2.0 (<channel><item>) — the format all three sources use.
    for item in root.iter("item"):
        title = _strip(item.findtext("title"))
        link = _strip(item.findtext("link"))
        # Defense in depth: never propagate a non-http(s) link (no javascript:/data:).
        if not link.lower().startswith(("http://", "https://")):
            link = ""
        published = _strip(item.findtext("pubDate"))
        if title:
            items.append({
                "source": source,
                "title": title,
                "link": link,
                "published": published,
            })
        if len(items) >= _PER_SOURCE_LIMIT:
            break
    return items


async def _fetch_one(client: httpx.AsyncClient, source: str, url: str) -> list[dict]:
    try:
        resp = await client.get(url, headers={"User-Agent": "OdiliTruthSeeker/1.0"})
        resp.raise_for_status()
        return _parse_feed(source, resp.text)
    except Exception as exc:  # noqa: BLE001 — one bad source must not break the layer
        logger.warning("Catholic news fetch failed for %s: %s", source, exc)
        return []


async def get_catholic_news(force_refresh: bool = False) -> dict[str, Any]:
    """
    Return recent Catholic headlines plus a fetch note.

    Shape: {"headlines": [...], "count": int, "cached": bool, "note": str|None}.
    Never raises — on total failure returns the last good cache or an empty list.
    """
    now = time.monotonic()
    if not force_refresh and _CACHE["data"] is not None and now < _CACHE["expires_at"]:
        return {**_CACHE["data"], "cached": True}

    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        results = await asyncio.gather(
            *(_fetch_one(client, src, url) for src, url in _SOURCES)
        )

    headlines: list[dict] = []
    for batch in results:
        headlines.extend(batch)
    headlines = headlines[:_TOTAL_LIMIT]

    if not headlines:
        # Total failure — serve stale cache if we have one, else an empty note.
        if _CACHE["data"] is not None:
            return {**_CACHE["data"], "cached": True, "note": "Showing last cached headlines (sources unreachable)."}
        return {"headlines": [], "count": 0, "cached": False,
                "note": "Catholic news sources are currently unreachable."}

    payload = {"headlines": headlines, "count": len(headlines), "note": None}
    _CACHE.update(data=payload, expires_at=time.monotonic() + _TTL_SECONDS)
    return {**payload, "cached": False}


async def headline_titles(limit: int = 6) -> list[str]:
    """A flat list of recent headline titles for injecting into AI prompts."""
    data = await get_catholic_news()
    return [h["title"] for h in data.get("headlines", [])[:limit]]
