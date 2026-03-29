import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.aggregator import AggregatedNews, NewsAggregator
from forward_testing.news.models import DailyMarketSnapshot, NewsItem, PriceData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(title: str, category: str = "macro", source: str = "test") -> NewsItem:
    return NewsItem(
        title=title,
        summary="",
        source=source,
        category=category,
        url="https://example.com",
        published_at=datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Deduplication tests
# ---------------------------------------------------------------------------

class TestDeduplicate:
    def setup_method(self):
        self.aggregator = NewsAggregator(ForwardTestingConfig())

    def test_dedup_removes_exact_duplicate_titles(self):
        items = [
            _make_item("Fed Holds Rates Steady"),
            _make_item("Fed Holds Rates Steady"),
        ]
        result = self.aggregator._deduplicate(items)
        assert len(result) == 1

    def test_dedup_removes_case_insensitive_duplicates(self):
        items = [
            _make_item("Fed Holds Rates Steady at March Meeting"),
            _make_item("fed holds rates steady at march meeting"),
        ]
        result = self.aggregator._deduplicate(items)
        assert len(result) == 1

    def test_dedup_removes_punctuation_differences(self):
        items = [
            _make_item("Fed Holds Rates Steady!"),
            _make_item("Fed Holds Rates Steady"),
        ]
        result = self.aggregator._deduplicate(items)
        assert len(result) == 1

    def test_dedup_keeps_first_seen(self):
        first = _make_item("Fed Holds Rates Steady", source="reuters")
        duplicate = _make_item("Fed Holds Rates Steady", source="ap_news")
        result = self.aggregator._deduplicate([first, duplicate])
        assert len(result) == 1
        assert result[0].source == "reuters"

    def test_dedup_keeps_distinct_titles(self):
        items = [
            _make_item("Fed Holds Rates Steady"),
            _make_item("Oil Prices Fall on Demand Fears"),
            _make_item("NVIDIA Earnings Beat Estimates"),
        ]
        result = self.aggregator._deduplicate(items)
        assert len(result) == 3

    def test_dedup_empty_list(self):
        result = self.aggregator._deduplicate([])
        assert result == []

    def test_dedup_single_item(self):
        items = [_make_item("Single Article")]
        result = self.aggregator._deduplicate(items)
        assert len(result) == 1

    def test_dedup_preserves_order_of_first_occurrences(self):
        items = [
            _make_item("Article A"),
            _make_item("Article B"),
            _make_item("Article A"),  # duplicate of first
            _make_item("Article C"),
        ]
        result = self.aggregator._deduplicate(items)
        assert len(result) == 3
        assert [i.title for i in result] == ["Article A", "Article B", "Article C"]


# ---------------------------------------------------------------------------
# Group by category tests
# ---------------------------------------------------------------------------

class TestGroupByCategory:
    def setup_method(self):
        self.aggregator = NewsAggregator(ForwardTestingConfig())

    def test_group_by_category_basic(self):
        items = [
            _make_item("Macro article 1", category="macro"),
            _make_item("Macro article 2", category="macro"),
            _make_item("Geo article 1", category="geopolitical"),
        ]
        grouped = self.aggregator._group_by_category(items)
        assert "macro" in grouped
        assert "geopolitical" in grouped
        assert len(grouped["macro"]) == 2
        assert len(grouped["geopolitical"]) == 1

    def test_group_by_category_empty(self):
        grouped = self.aggregator._group_by_category([])
        assert grouped == {}

    def test_group_by_category_single_category(self):
        items = [_make_item(f"Article {i}", category="energy") for i in range(5)]
        grouped = self.aggregator._group_by_category(items)
        assert list(grouped.keys()) == ["energy"]
        assert len(grouped["energy"]) == 5

    def test_group_by_category_all_different_categories(self):
        categories = ["macro", "geopolitical", "energy", "us_politics", "sentiment", "ticker"]
        items = [_make_item(f"Article about {cat}", category=cat) for cat in categories]
        grouped = self.aggregator._group_by_category(items)
        assert set(grouped.keys()) == set(categories)
        for cat in categories:
            assert len(grouped[cat]) == 1

    def test_group_by_category_preserves_items(self):
        items = [
            _make_item("Fed raises rates", category="macro"),
            _make_item("Oil falls", category="energy"),
        ]
        grouped = self.aggregator._group_by_category(items)
        assert grouped["macro"][0].title == "Fed raises rates"
        assert grouped["energy"][0].title == "Oil falls"


# ---------------------------------------------------------------------------
# fetch_all integration test (all fetchers mocked)
# ---------------------------------------------------------------------------

GOOGLE_ITEMS = [_make_item("Google article 1", category="ticker", source="google_news")]
YAHOO_NEWS_ITEMS = [_make_item("Yahoo article 1", category="ticker", source="yahoo_finance")]
GDELT_ITEMS = [_make_item("GDELT article 1", category="geopolitical", source="gdelt")]
REUTERS_ITEMS = [_make_item("Reuters article 1", category="macro", source="reuters_ap")]
FED_ITEMS = [_make_item("Fed article 1", category="macro", source="fed_gov")]
REDDIT_ITEMS = [_make_item("Reddit post 1", category="sentiment", source="reddit")]

SAMPLE_PRICES = [
    PriceData(
        ticker="NVDA",
        close=900.0,
        change_pct=1.5,
        volume=80_000_000,
        avg_volume=60_000_000,
        date=datetime(2026, 3, 29, tzinfo=timezone.utc),
    )
]

SAMPLE_SNAPSHOT = DailyMarketSnapshot(
    date=datetime(2026, 3, 29, tzinfo=timezone.utc),
    sp500=5800.0,
    sp500_change_pct=-0.3,
    vix=20.0,
    treasury_10y=4.2,
    brent_crude=85.0,
    gold=2300.0,
    dollar_index=103.0,
)


class TestFetchAll:
    @patch("forward_testing.news.aggregator.RedditSentimentFetcher")
    @patch("forward_testing.news.aggregator.FedGovFetcher")
    @patch("forward_testing.news.aggregator.ReutersAPFetcher")
    @patch("forward_testing.news.aggregator.GdeltFetcher")
    @patch("forward_testing.news.aggregator.YahooFinanceFetcher")
    @patch("forward_testing.news.aggregator.GoogleNewsFetcher")
    def test_fetch_all_calls_all_six_sources(
        self,
        mock_google_cls,
        mock_yahoo_cls,
        mock_gdelt_cls,
        mock_reuters_cls,
        mock_fed_cls,
        mock_reddit_cls,
    ):
        # Configure each mock fetcher instance
        mock_google = MagicMock()
        mock_google.fetch_all.return_value = GOOGLE_ITEMS
        mock_google_cls.return_value = mock_google

        mock_yahoo = MagicMock()
        mock_yahoo.fetch_all_news.return_value = YAHOO_NEWS_ITEMS
        mock_yahoo.fetch_all_prices.return_value = SAMPLE_PRICES
        mock_yahoo.fetch_market_snapshot.return_value = SAMPLE_SNAPSHOT
        mock_yahoo_cls.return_value = mock_yahoo

        mock_gdelt = MagicMock()
        mock_gdelt.fetch_all.return_value = GDELT_ITEMS
        mock_gdelt_cls.return_value = mock_gdelt

        mock_reuters = MagicMock()
        mock_reuters.fetch_all.return_value = REUTERS_ITEMS
        mock_reuters_cls.return_value = mock_reuters

        mock_fed = MagicMock()
        mock_fed.fetch_all.return_value = FED_ITEMS
        mock_fed_cls.return_value = mock_fed

        mock_reddit = MagicMock()
        mock_reddit.fetch_all.return_value = REDDIT_ITEMS
        mock_reddit_cls.return_value = mock_reddit

        config = ForwardTestingConfig()
        aggregator = NewsAggregator(config)
        result = aggregator.fetch_all()

        # All 6 news fetchers must have been called
        mock_google.fetch_all.assert_called_once()
        mock_yahoo.fetch_all_news.assert_called_once()
        mock_gdelt.fetch_all.assert_called_once()
        mock_reuters.fetch_all.assert_called_once()
        mock_fed.fetch_all.assert_called_once()
        mock_reddit.fetch_all.assert_called_once()

        # Prices and market snapshot fetchers must have been called
        mock_yahoo.fetch_all_prices.assert_called_once()
        mock_yahoo.fetch_market_snapshot.assert_called_once()

    @patch("forward_testing.news.aggregator.RedditSentimentFetcher")
    @patch("forward_testing.news.aggregator.FedGovFetcher")
    @patch("forward_testing.news.aggregator.ReutersAPFetcher")
    @patch("forward_testing.news.aggregator.GdeltFetcher")
    @patch("forward_testing.news.aggregator.YahooFinanceFetcher")
    @patch("forward_testing.news.aggregator.GoogleNewsFetcher")
    def test_fetch_all_returns_aggregated_news_dataclass(
        self,
        mock_google_cls,
        mock_yahoo_cls,
        mock_gdelt_cls,
        mock_reuters_cls,
        mock_fed_cls,
        mock_reddit_cls,
    ):
        for mock_cls, items in [
            (mock_google_cls, GOOGLE_ITEMS),
            (mock_gdelt_cls, GDELT_ITEMS),
            (mock_reuters_cls, REUTERS_ITEMS),
            (mock_fed_cls, FED_ITEMS),
            (mock_reddit_cls, REDDIT_ITEMS),
        ]:
            inst = MagicMock()
            inst.fetch_all.return_value = items
            mock_cls.return_value = inst

        mock_yahoo = MagicMock()
        mock_yahoo.fetch_all_news.return_value = YAHOO_NEWS_ITEMS
        mock_yahoo.fetch_all_prices.return_value = SAMPLE_PRICES
        mock_yahoo.fetch_market_snapshot.return_value = SAMPLE_SNAPSHOT
        mock_yahoo_cls.return_value = mock_yahoo

        aggregator = NewsAggregator(ForwardTestingConfig())
        result = aggregator.fetch_all()

        assert isinstance(result, AggregatedNews)
        assert result.news_items is not None
        assert result.prices == SAMPLE_PRICES
        assert result.market_snapshot == SAMPLE_SNAPSHOT
        assert isinstance(result.grouped, dict)
        assert isinstance(result.source_counts, dict)

    @patch("forward_testing.news.aggregator.RedditSentimentFetcher")
    @patch("forward_testing.news.aggregator.FedGovFetcher")
    @patch("forward_testing.news.aggregator.ReutersAPFetcher")
    @patch("forward_testing.news.aggregator.GdeltFetcher")
    @patch("forward_testing.news.aggregator.YahooFinanceFetcher")
    @patch("forward_testing.news.aggregator.GoogleNewsFetcher")
    def test_fetch_all_deduplicates_across_sources(
        self,
        mock_google_cls,
        mock_yahoo_cls,
        mock_gdelt_cls,
        mock_reuters_cls,
        mock_fed_cls,
        mock_reddit_cls,
    ):
        # Two sources emit the same headline
        shared_title = "Fed Holds Rates Steady"
        google_items = [_make_item(shared_title, source="google_news")]
        reuters_items = [_make_item(shared_title, source="reuters_ap")]

        mock_google = MagicMock()
        mock_google.fetch_all.return_value = google_items
        mock_google_cls.return_value = mock_google

        mock_yahoo = MagicMock()
        mock_yahoo.fetch_all_news.return_value = []
        mock_yahoo.fetch_all_prices.return_value = []
        mock_yahoo.fetch_market_snapshot.return_value = None
        mock_yahoo_cls.return_value = mock_yahoo

        mock_gdelt = MagicMock()
        mock_gdelt.fetch_all.return_value = []
        mock_gdelt_cls.return_value = mock_gdelt

        mock_reuters = MagicMock()
        mock_reuters.fetch_all.return_value = reuters_items
        mock_reuters_cls.return_value = mock_reuters

        mock_fed = MagicMock()
        mock_fed.fetch_all.return_value = []
        mock_fed_cls.return_value = mock_fed

        mock_reddit = MagicMock()
        mock_reddit.fetch_all.return_value = []
        mock_reddit_cls.return_value = mock_reddit

        aggregator = NewsAggregator(ForwardTestingConfig())
        result = aggregator.fetch_all()

        # Duplicate across sources should be collapsed to 1
        assert len(result.news_items) == 1
        # The first seen (google_news) should be kept
        assert result.news_items[0].source == "google_news"

    @patch("forward_testing.news.aggregator.RedditSentimentFetcher")
    @patch("forward_testing.news.aggregator.FedGovFetcher")
    @patch("forward_testing.news.aggregator.ReutersAPFetcher")
    @patch("forward_testing.news.aggregator.GdeltFetcher")
    @patch("forward_testing.news.aggregator.YahooFinanceFetcher")
    @patch("forward_testing.news.aggregator.GoogleNewsFetcher")
    def test_fetch_all_source_counts_populated(
        self,
        mock_google_cls,
        mock_yahoo_cls,
        mock_gdelt_cls,
        mock_reuters_cls,
        mock_fed_cls,
        mock_reddit_cls,
    ):
        for mock_cls, items in [
            (mock_google_cls, GOOGLE_ITEMS),
            (mock_gdelt_cls, GDELT_ITEMS),
            (mock_reuters_cls, REUTERS_ITEMS),
            (mock_fed_cls, FED_ITEMS),
            (mock_reddit_cls, REDDIT_ITEMS),
        ]:
            inst = MagicMock()
            inst.fetch_all.return_value = items
            mock_cls.return_value = inst

        mock_yahoo = MagicMock()
        mock_yahoo.fetch_all_news.return_value = YAHOO_NEWS_ITEMS
        mock_yahoo.fetch_all_prices.return_value = []
        mock_yahoo.fetch_market_snapshot.return_value = None
        mock_yahoo_cls.return_value = mock_yahoo

        aggregator = NewsAggregator(ForwardTestingConfig())
        result = aggregator.fetch_all()

        assert "google_news" in result.source_counts
        assert "yahoo_finance" in result.source_counts
        assert "gdelt" in result.source_counts
        assert "reuters_ap" in result.source_counts
        assert "fed_gov" in result.source_counts
        assert "reddit" in result.source_counts

        assert result.source_counts["google_news"] == len(GOOGLE_ITEMS)
        assert result.source_counts["yahoo_finance"] == len(YAHOO_NEWS_ITEMS)


# ---------------------------------------------------------------------------
# save_raw tests
# ---------------------------------------------------------------------------

class TestSaveRaw:
    def setup_method(self):
        self.config = ForwardTestingConfig()
        self.aggregator = NewsAggregator(self.config)

    def test_save_raw_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.config.results_dir = tmpdir
            result = AggregatedNews(
                date=datetime(2026, 3, 29).date(),
                news_items=[_make_item("Test article")],
                prices=[],
                market_snapshot=None,
                grouped={"macro": [_make_item("Test article")]},
                source_counts={"google_news": 1},
            )
            path = self.aggregator.save_raw(result, "2026-03-29")
            assert os.path.isfile(path)
            assert path.endswith("daily_news.json")

    def test_save_raw_correct_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.config.results_dir = tmpdir
            result = AggregatedNews(
                date=datetime(2026, 3, 29).date(),
                news_items=[],
                prices=[],
                market_snapshot=None,
                grouped={},
                source_counts={},
            )
            path = self.aggregator.save_raw(result, "2026-03-29")
            expected = os.path.join(tmpdir, "2026-03-29", "daily_news.json")
            assert path == expected

    def test_save_raw_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.config.results_dir = tmpdir
            result = AggregatedNews(
                date=datetime(2026, 3, 29).date(),
                news_items=[_make_item("Article A"), _make_item("Article B")],
                prices=SAMPLE_PRICES,
                market_snapshot=SAMPLE_SNAPSHOT,
                grouped={"macro": [_make_item("Article A")]},
                source_counts={"google_news": 2},
            )
            path = self.aggregator.save_raw(result, "2026-03-29")
            with open(path, "r") as f:
                data = json.load(f)

            assert data["date"] == "2026-03-29"
            assert data["total_items"] == 2
            assert len(data["news_items"]) == 2
            assert "macro" in data["grouped"]
            assert data["source_counts"]["google_news"] == 2

    def test_save_raw_creates_directory_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.config.results_dir = tmpdir
            new_date = "2099-01-01"
            result = AggregatedNews(
                date=datetime(2099, 1, 1).date(),
                news_items=[],
                prices=[],
                market_snapshot=None,
                grouped={},
                source_counts={},
            )
            path = self.aggregator.save_raw(result, new_date)
            assert os.path.isdir(os.path.join(tmpdir, new_date))
            assert os.path.isfile(path)
