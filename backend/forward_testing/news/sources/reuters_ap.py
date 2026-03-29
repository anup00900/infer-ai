import logging
from datetime import datetime, timezone
from typing import List

import feedparser
import requests

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem

logger = logging.getLogger(__name__)

MACRO_KEYWORDS = [
    "federal reserve", "interest rate", "inflation", "gdp", "unemployment",
    "treasury", "cpi", "jobs report", "consumer spending", "retail sales",
    "central bank", "monetary policy", "fiscal policy", "debt ceiling",
    "government shutdown", "budget",
]

GEOPOLITICAL_KEYWORDS = [
    "iran", "hormuz", "sanctions", "china", "trade war", "tariff", "nato",
    "opec", "middle east", "russia", "ukraine", "north korea", "taiwan",
    "conflict", "war", "military", "geopolit",
]

ENERGY_KEYWORDS = [
    "crude oil", "natural gas", "gold", "copper", "uranium", "lng",
    "gasoline", "opec", "oil inventory", "renewable energy", "oil price",
    "energy",
]

US_POLITICS_KEYWORDS = [
    "white house", "congress", "supreme court", "election", "senate",
    "house of representatives", "president", "executive order", "legislation",
    "democrat", "republican", "capitol",
]


class ReutersAPFetcher:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.timeout = 15

    def fetch_all(self) -> List[NewsItem]:
        all_items: List[NewsItem] = []
        for feed_name, url in self.config.rss_feeds.items():
            if not (feed_name.startswith("reuters") or feed_name.startswith("ap")):
                continue
            items = self._fetch_feed(url, feed_name)
            all_items.extend(items)
        logger.info(f"ReutersAP: fetched {len(all_items)} total items")
        return all_items

    def _fetch_feed(self, url: str, feed_name: str) -> List[NewsItem]:
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            items = []
            for entry in feed.entries[:20]:
                title = entry.get("title", "")
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                items.append(NewsItem(
                    title=title,
                    summary=entry.get("description", entry.get("summary", "")),
                    source="reuters_ap",
                    category=self._classify(title, feed_name),
                    url=entry.get("link", ""),
                    published_at=published or datetime.now(timezone.utc),
                ))
            return items
        except Exception as e:
            logger.warning(f"ReutersAP fetch failed for '{feed_name}' ({url}): {e}")
            return []

    def _classify(self, title: str, feed_name: str) -> str:
        if "politics" in feed_name:
            return "us_politics"

        title_lower = title.lower()

        for kw in MACRO_KEYWORDS:
            if kw in title_lower:
                return "macro"

        for kw in ENERGY_KEYWORDS:
            if kw in title_lower:
                return "energy"

        for kw in GEOPOLITICAL_KEYWORDS:
            if kw in title_lower:
                return "geopolitical"

        for kw in US_POLITICS_KEYWORDS:
            if kw in title_lower:
                return "us_politics"

        # Default based on feed_name
        if "business" in feed_name:
            return "macro"
        if "world" in feed_name:
            return "geopolitical"

        return "general"
