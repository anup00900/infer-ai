import logging
from datetime import datetime, timezone
from typing import List

import feedparser
import requests

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem

logger = logging.getLogger(__name__)


class FedGovFetcher:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.timeout = 15

    def fetch_all(self) -> List[NewsItem]:
        all_items: List[NewsItem] = []
        for feed_name, url in self.config.rss_feeds.items():
            if not feed_name.startswith("fed"):
                continue
            items = self._fetch_feed(url, feed_name)
            all_items.extend(items)
        logger.info(f"FedGov: fetched {len(all_items)} total items")
        return all_items

    def _fetch_feed(self, url: str, feed_name: str) -> List[NewsItem]:
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            items = []
            for entry in feed.entries[:20]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                items.append(NewsItem(
                    title=entry.get("title", ""),
                    summary=entry.get("description", entry.get("summary", "")),
                    source="fed_gov",
                    category="macro",
                    url=entry.get("link", ""),
                    published_at=published or datetime.now(timezone.utc),
                ))
            return items
        except Exception as e:
            logger.warning(f"FedGov fetch failed for '{feed_name}' ({url}): {e}")
            return []
