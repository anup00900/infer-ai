import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import DailyMarketSnapshot, NewsItem, PriceData
from forward_testing.news.sources.fed_gov import FedGovFetcher
from forward_testing.news.sources.gdelt import GdeltFetcher
from forward_testing.news.sources.google_news import GoogleNewsFetcher
from forward_testing.news.sources.reddit_sentiment import RedditSentimentFetcher
from forward_testing.news.sources.reuters_ap import ReutersAPFetcher
from forward_testing.news.sources.yahoo_finance import YahooFinanceFetcher

logger = logging.getLogger(__name__)


@dataclass
class AggregatedNews:
    date: date
    news_items: List[NewsItem] = field(default_factory=list)
    prices: List[PriceData] = field(default_factory=list)
    market_snapshot: Optional[DailyMarketSnapshot] = None
    grouped: Dict[str, List[NewsItem]] = field(default_factory=dict)
    source_counts: Dict[str, int] = field(default_factory=dict)


class NewsAggregator:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.google_news = GoogleNewsFetcher(config)
        self.yahoo_finance = YahooFinanceFetcher(config)
        self.gdelt = GdeltFetcher(config)
        self.reuters_ap = ReutersAPFetcher(config)
        self.fed_gov = FedGovFetcher(config)
        self.reddit_sentiment = RedditSentimentFetcher(config)

    def fetch_all(self) -> AggregatedNews:
        """Call all sources, deduplicate news, group by category, and return AggregatedNews."""
        today = datetime.utcnow().date()

        # Collect news from all sources, tracking per-source counts before dedup
        raw_items: List[NewsItem] = []
        source_counts: Dict[str, int] = {}

        sources = [
            ("google_news", lambda: self.google_news.fetch_all()),
            ("yahoo_finance", lambda: self.yahoo_finance.fetch_all_news()),
            ("gdelt", lambda: self.gdelt.fetch_all()),
            ("reuters_ap", lambda: self.reuters_ap.fetch_all()),
            ("fed_gov", lambda: self.fed_gov.fetch_all()),
            ("reddit", lambda: self.reddit_sentiment.fetch_all()),
        ]

        for source_name, fetcher_fn in sources:
            try:
                items = fetcher_fn()
                source_counts[source_name] = len(items)
                raw_items.extend(items)
                logger.info(f"{source_name}: collected {len(items)} items")
            except Exception as e:
                logger.warning(f"{source_name}: fetch failed: {e}")
                source_counts[source_name] = 0

        # Fetch prices and market snapshot from Yahoo Finance
        try:
            prices = self.yahoo_finance.fetch_all_prices()
        except Exception as e:
            logger.warning(f"YahooFinance prices fetch failed: {e}")
            prices = []

        try:
            market_snapshot = self.yahoo_finance.fetch_market_snapshot()
        except Exception as e:
            logger.warning(f"YahooFinance market snapshot fetch failed: {e}")
            market_snapshot = None

        # Deduplicate
        deduped_items = self._deduplicate(raw_items)

        # Scrape full article text for top items
        try:
            from forward_testing.news.article_scraper import enrich_with_full_text
            deduped_items = enrich_with_full_text(deduped_items, max_workers=10, max_articles=80)
        except Exception as e:
            logger.warning(f"Article scraping failed (continuing with headlines): {e}")

        grouped = self._group_by_category(deduped_items)

        logger.info(
            f"Aggregator: {len(raw_items)} raw -> {len(deduped_items)} deduped "
            f"across {len(grouped)} categories"
        )

        return AggregatedNews(
            date=today,
            news_items=deduped_items,
            prices=prices,
            market_snapshot=market_snapshot,
            grouped=grouped,
            source_counts=source_counts,
        )

    def _deduplicate(self, items: List[NewsItem]) -> List[NewsItem]:
        """Remove duplicate items using dedup_key(); keeps the first occurrence."""
        seen: set = set()
        result: List[NewsItem] = []
        for item in items:
            key = item.dedup_key()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    def _group_by_category(self, items: List[NewsItem]) -> Dict[str, List[NewsItem]]:
        """Group news items by their category field."""
        groups: Dict[str, List[NewsItem]] = {}
        for item in items:
            category = item.category or "general"
            groups.setdefault(category, []).append(item)
        return groups

    def save_raw(self, result: AggregatedNews, date_str: str) -> str:
        """Save aggregated news to JSON at results_dir/date_str/daily_news.json.

        Returns the absolute path of the saved file.
        """
        output_dir = os.path.join(self.config.results_dir, date_str)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "daily_news.json")

        def _serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, date):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        def _item_to_dict(item: NewsItem) -> dict:
            d = {
                "title": item.title,
                "summary": item.summary,
                "source": item.source,
                "category": item.category,
                "url": item.url,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "ticker": item.ticker,
            }
            if item.full_text:
                d["full_text"] = item.full_text
            return d

        def _price_to_dict(p: PriceData) -> dict:
            return {
                "ticker": p.ticker,
                "close": p.close,
                "change_pct": p.change_pct,
                "volume": p.volume,
                "avg_volume": p.avg_volume,
                "date": p.date.isoformat() if p.date else None,
                "open": p.open,
                "high": p.high,
                "low": p.low,
            }

        def _snapshot_to_dict(s: DailyMarketSnapshot) -> dict:
            return {
                "date": s.date.isoformat() if s.date else None,
                "sp500": s.sp500,
                "sp500_change_pct": s.sp500_change_pct,
                "vix": s.vix,
                "treasury_10y": s.treasury_10y,
                "brent_crude": s.brent_crude,
                "gold": s.gold,
                "dollar_index": s.dollar_index,
                "us_gasoline": s.us_gasoline,
            }

        payload = {
            "date": result.date.isoformat() if result.date else None,
            "source_counts": result.source_counts,
            "total_items": len(result.news_items),
            "news_items": [_item_to_dict(item) for item in result.news_items],
            "prices": [_price_to_dict(p) for p in result.prices],
            "market_snapshot": _snapshot_to_dict(result.market_snapshot) if result.market_snapshot else None,
            "grouped": {
                category: [_item_to_dict(item) for item in items]
                for category, items in result.grouped.items()
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=_serialize)

        logger.info(f"Aggregator: saved raw news to {output_path}")
        return output_path
