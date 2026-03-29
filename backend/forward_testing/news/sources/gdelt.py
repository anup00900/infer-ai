import logging
from datetime import datetime, timezone
from typing import List

import requests

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem

logger = logging.getLogger(__name__)

GDELT_PRIORITY_QUERIES = {
    "geopolitical": [
        "Iran Hormuz oil conflict",
        "China trade tariffs",
        "Middle East war",
        "Russia Ukraine",
        "OPEC oil production",
    ],
    "us_politics": [
        "White House executive order",
        "Congress legislation economy",
        "Federal Reserve chair nomination",
        "Supreme Court ruling",
    ],
    "energy": [
        "crude oil price supply",
        "natural gas LNG",
        "gold price safe haven",
    ],
    "macro": [
        "US economy GDP inflation",
        "global recession risk",
        "treasury bond yield",
    ],
    "global_markets": [
        "ECB interest rate eurozone",
        "China economy slowdown",
        "emerging markets currency",
    ],
}


def _parse_seendate(seendate: str) -> datetime:
    """Parse GDELT seendate format '20260329T140000Z' into a datetime."""
    try:
        return datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


class GdeltFetcher:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.timeout = 15

    def fetch_topic(self, query: str, category: str) -> List[NewsItem]:
        """Fetch articles from the GDELT DOC API for a given query and category."""
        try:
            params = {
                "query": query,
                "mode": "ArtList",
                "maxrecords": 20,
                "timespan": "1d",
                "format": "json",
                "sort": "DateDesc",
            }
            resp = requests.get(self.config.gdelt_base_url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            articles = data.get("articles") or []
            items = []
            for article in articles:
                title = article.get("title", "")
                url = article.get("url", "")
                seendate = article.get("seendate", "")
                domain = article.get("domain", "")
                published_at = _parse_seendate(seendate)

                items.append(NewsItem(
                    title=title,
                    summary="",
                    source="gdelt",
                    category=category,
                    url=url,
                    published_at=published_at,
                    ticker=None,
                    raw_data=article,
                ))
            return items
        except Exception as e:
            logger.warning(f"GDELT fetch failed for '{query}': {e}")
            return []

    def fetch_all(self) -> List[NewsItem]:
        """Fetch articles across all priority queries and categories."""
        all_items: List[NewsItem] = []
        for category, queries in GDELT_PRIORITY_QUERIES.items():
            for query in queries:
                items = self.fetch_topic(query, category=category)
                all_items.extend(items)
        logger.info(f"GDELT: fetched {len(all_items)} total items")
        return all_items
