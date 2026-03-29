import logging
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote

import feedparser
import requests

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


class GoogleNewsFetcher:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.timeout = 15

    def fetch_ticker(self, ticker: str) -> List[NewsItem]:
        query = f"{ticker} stock"
        return self._fetch(query, category="ticker", ticker=ticker)

    def fetch_topic(self, topic: str, category: str) -> List[NewsItem]:
        return self._fetch(topic, category=category)

    def fetch_all(self) -> List[NewsItem]:
        all_items: List[NewsItem] = []
        for ticker in self.config.tickers:
            items = self.fetch_ticker(ticker)
            all_items.extend(items)
        for category, terms in self.config.query_terms.items():
            for term in terms:
                items = self.fetch_topic(term, category=category)
                all_items.extend(items)
        logger.info(f"GoogleNews: fetched {len(all_items)} total items")
        return all_items

    def _fetch(self, query: str, category: str, ticker: Optional[str] = None) -> List[NewsItem]:
        try:
            url = GOOGLE_NEWS_RSS.format(query=quote(query))
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            items = []
            for entry in feed.entries:  # No limit — include all results
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                items.append(NewsItem(
                    title=entry.get("title", ""),
                    summary=entry.get("description", entry.get("summary", "")),
                    source="google_news",
                    category=category,
                    ticker=ticker,
                    url=entry.get("link", ""),
                    published_at=published or datetime.now(timezone.utc),
                ))
            return items
        except Exception as e:
            logger.warning(f"GoogleNews fetch failed for '{query}': {e}")
            return []
