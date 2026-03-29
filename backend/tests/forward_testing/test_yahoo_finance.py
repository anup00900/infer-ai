from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import DailyMarketSnapshot, NewsItem, PriceData
from forward_testing.news.sources.yahoo_finance import YahooFinanceFetcher


# ---------------------------------------------------------------------------
# Helpers to build mock yf.Ticker objects
# ---------------------------------------------------------------------------

def _make_history(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal DataFrame that mimics yf history output."""
    if not rows:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    df = pd.DataFrame(rows)
    df.index = pd.to_datetime(df.pop("date"))
    return df


def _mock_ticker(history_df: pd.DataFrame, info: dict = None, news: list = None):
    t = MagicMock()
    t.history.return_value = history_df
    t.info = info or {}
    t.news = news or []
    return t


# ---------------------------------------------------------------------------
# Test fetch_price
# ---------------------------------------------------------------------------

@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_price_returns_price_data(mock_ticker_cls):
    hist = _make_history([
        {"date": "2026-03-28", "Open": 100.0, "High": 105.0, "Low": 99.0, "Close": 102.0, "Volume": 1_000_000},
        {"date": "2026-03-29", "Open": 102.0, "High": 110.0, "Low": 101.0, "Close": 108.0, "Volume": 1_200_000},
    ])
    mock_ticker_cls.return_value = _mock_ticker(hist, info={"averageVolume": 900_000})

    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    result = fetcher.fetch_price("NVDA")

    assert isinstance(result, PriceData)
    assert result.ticker == "NVDA"
    assert result.close == pytest.approx(108.0)
    assert result.change_pct == pytest.approx((108.0 - 102.0) / 102.0 * 100)
    assert result.volume == 1_200_000
    assert result.avg_volume == 900_000
    assert isinstance(result.date, datetime)
    assert result.open == pytest.approx(102.0)
    assert result.high == pytest.approx(110.0)
    assert result.low == pytest.approx(101.0)


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_price_insufficient_history_returns_none(mock_ticker_cls):
    # Only 1 row — cannot compute change_pct
    hist = _make_history([
        {"date": "2026-03-29", "Open": 100.0, "High": 105.0, "Low": 99.0, "Close": 102.0, "Volume": 500_000},
    ])
    mock_ticker_cls.return_value = _mock_ticker(hist)

    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    result = fetcher.fetch_price("NVDA")

    assert result is None


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_price_exception_returns_none(mock_ticker_cls):
    mock_ticker_cls.side_effect = Exception("network error")

    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    result = fetcher.fetch_price("NVDA")

    assert result is None


# ---------------------------------------------------------------------------
# Test fetch_all_prices
# ---------------------------------------------------------------------------

@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_all_prices_returns_11_items(mock_ticker_cls):
    hist = _make_history([
        {"date": "2026-03-28", "Open": 100.0, "High": 105.0, "Low": 99.0, "Close": 102.0, "Volume": 1_000_000},
        {"date": "2026-03-29", "Open": 102.0, "High": 110.0, "Low": 101.0, "Close": 108.0, "Volume": 1_200_000},
    ])
    mock_ticker_cls.return_value = _mock_ticker(hist, info={"averageVolume": 900_000})

    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    results = fetcher.fetch_all_prices()

    assert len(results) == 11
    assert all(isinstance(r, PriceData) for r in results)
    # Default config has 11 tickers
    expected_tickers = {"NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMZN", "AMD", "AVGO", "ORCL", "MU", "QCOM"}
    returned_tickers = {r.ticker for r in results}
    assert returned_tickers == expected_tickers


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_all_prices_skips_failed_tickers(mock_ticker_cls):
    """If some tickers fail, only successful ones are returned."""
    hist = _make_history([
        {"date": "2026-03-28", "Open": 100.0, "High": 105.0, "Low": 99.0, "Close": 102.0, "Volume": 1_000_000},
        {"date": "2026-03-29", "Open": 102.0, "High": 110.0, "Low": 101.0, "Close": 108.0, "Volume": 1_200_000},
    ])

    call_count = {"n": 0}

    def side_effect(ticker):
        call_count["n"] += 1
        if call_count["n"] % 3 == 0:
            raise Exception("timeout")
        return _mock_ticker(hist, info={"averageVolume": 500_000})

    mock_ticker_cls.side_effect = side_effect

    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    results = fetcher.fetch_all_prices()

    assert len(results) < 11
    assert all(isinstance(r, PriceData) for r in results)


# ---------------------------------------------------------------------------
# Test fetch_ticker_news
# ---------------------------------------------------------------------------

SAMPLE_NEWS = [
    {
        "title": "NVIDIA announces new GPU",
        "summary": "NVIDIA unveiled its next-gen chip today.",
        "link": "https://finance.yahoo.com/news/nvda-gpu",
        "providerPublishTime": 1743206400,  # some unix timestamp
    },
    {
        "title": "NVDA stock surges 5%",
        "summary": "Shares rose on strong earnings guidance.",
        "link": "https://finance.yahoo.com/news/nvda-surge",
        "providerPublishTime": 1743120000,
    },
]


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_ticker_news_returns_news_items(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(
        _make_history([]),  # history not used for news
        news=SAMPLE_NEWS,
    )

    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    items = fetcher.fetch_ticker_news("NVDA")

    assert len(items) == 2
    assert all(isinstance(item, NewsItem) for item in items)
    assert items[0].source == "yahoo_finance"
    assert items[0].category == "ticker"
    assert items[0].ticker == "NVDA"
    assert "NVIDIA" in items[0].title
    assert isinstance(items[0].published_at, datetime)


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_ticker_news_empty_returns_empty_list(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(_make_history([]), news=[])

    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    items = fetcher.fetch_ticker_news("NVDA")

    assert items == []


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_ticker_news_exception_returns_empty_list(mock_ticker_cls):
    mock_ticker_cls.side_effect = Exception("API error")

    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    items = fetcher.fetch_ticker_news("NVDA")

    assert items == []


# ---------------------------------------------------------------------------
# Test fetch_all_news
# ---------------------------------------------------------------------------

@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_all_news_aggregates_all_tickers(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(
        _make_history([]),
        news=SAMPLE_NEWS,
    )

    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all_news()

    # 11 tickers × 2 articles each
    assert len(items) == 11 * 2
    assert all(isinstance(item, NewsItem) for item in items)


# ---------------------------------------------------------------------------
# Test fetch_market_snapshot
# ---------------------------------------------------------------------------

def _build_snapshot_side_effect():
    """Return a side_effect function for yf.Ticker that returns sensible data
    for all 7 macro symbols."""

    symbol_values = {
        "^GSPC": (5500.0, 5450.0),    # (latest, prev)
        "^VIX":  (18.5,  19.0),
        "^TNX":  (4.25,  4.20),
        "BZ=F":  (85.0,  84.5),
        "GC=F":  (3200.0, 3180.0),
        "DX-Y.NYB": (103.5, 103.0),
        "RB=F":  (2.85,  2.80),
    }

    def side_effect(symbol):
        latest_close, prev_close = symbol_values.get(symbol, (100.0, 99.0))
        hist = _make_history([
            {"date": "2026-03-28", "Open": prev_close, "High": prev_close + 1,
             "Low": prev_close - 1, "Close": prev_close, "Volume": 100_000},
            {"date": "2026-03-29", "Open": latest_close, "High": latest_close + 1,
             "Low": latest_close - 1, "Close": latest_close, "Volume": 120_000},
        ])
        return _mock_ticker(hist)

    return side_effect


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_market_snapshot_returns_daily_snapshot(mock_ticker_cls):
    mock_ticker_cls.side_effect = _build_snapshot_side_effect()

    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    snapshot = fetcher.fetch_market_snapshot()

    assert isinstance(snapshot, DailyMarketSnapshot)
    assert snapshot.sp500 == pytest.approx(5500.0)
    assert snapshot.sp500_change_pct == pytest.approx((5500.0 - 5450.0) / 5450.0 * 100)
    assert snapshot.vix == pytest.approx(18.5)
    assert snapshot.treasury_10y == pytest.approx(4.25)
    assert snapshot.brent_crude == pytest.approx(85.0)
    assert snapshot.gold == pytest.approx(3200.0)
    assert snapshot.dollar_index == pytest.approx(103.5)
    assert snapshot.us_gasoline == pytest.approx(2.85)
    assert isinstance(snapshot.date, datetime)


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_market_snapshot_missing_sp500_returns_none(mock_ticker_cls):
    """If the SP500 symbol fails, snapshot should return None."""

    def side_effect(symbol):
        if symbol == "^GSPC":
            raise Exception("SP500 unavailable")
        hist = _make_history([
            {"date": "2026-03-28", "Open": 18.0, "High": 19.0, "Low": 17.0, "Close": 18.5, "Volume": 1000},
            {"date": "2026-03-29", "Open": 18.5, "High": 20.0, "Low": 18.0, "Close": 19.0, "Volume": 1100},
        ])
        return _mock_ticker(hist)

    mock_ticker_cls.side_effect = side_effect

    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    snapshot = fetcher.fetch_market_snapshot()

    assert snapshot is None


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_market_snapshot_exception_returns_none(mock_ticker_cls):
    mock_ticker_cls.side_effect = Exception("total failure")

    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    snapshot = fetcher.fetch_market_snapshot()

    assert snapshot is None
