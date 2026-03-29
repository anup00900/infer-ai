import pytest
from datetime import datetime, timezone
from forward_testing.news.models import NewsItem, PriceData, DailyMarketSnapshot


def test_news_item_creation():
    item = NewsItem(
        title="NVDA hits new high",
        summary="NVIDIA shares rose 3% on strong earnings",
        source="google_news",
        category="ticker",
        ticker="NVDA",
        url="https://example.com/article",
        published_at=datetime(2026, 3, 29, 14, 0, tzinfo=timezone.utc),
    )
    assert item.title == "NVDA hits new high"
    assert item.category == "ticker"
    assert item.ticker == "NVDA"


def test_news_item_without_ticker():
    item = NewsItem(
        title="Iran signals diplomacy",
        summary="Iranian foreign minister...",
        source="gdelt",
        category="geopolitical",
        url="https://example.com/iran",
        published_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
    )
    assert item.ticker is None
    assert item.category == "geopolitical"


def test_news_item_dedup_key():
    item = NewsItem(
        title="Fed Holds Rates Steady",
        summary="The Federal Reserve...",
        source="reuters",
        category="macro",
        url="https://example.com/fed",
        published_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
    )
    key = item.dedup_key()
    assert isinstance(key, str)
    assert len(key) > 0


def test_duplicate_items_same_key():
    item1 = NewsItem(
        title="Fed Holds Rates Steady at March Meeting",
        summary="Summary 1",
        source="reuters",
        category="macro",
        url="https://example.com/1",
        published_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
    )
    item2 = NewsItem(
        title="Fed holds rates steady at march meeting",
        summary="Summary 2",
        source="ap_news",
        category="macro",
        url="https://example.com/2",
        published_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
    )
    assert item1.dedup_key() == item2.dedup_key()


def test_price_data():
    p = PriceData(
        ticker="NVDA",
        close=892.50,
        change_pct=1.2,
        volume=85_000_000,
        avg_volume=65_000_000,
        date=datetime(2026, 3, 29, tzinfo=timezone.utc),
    )
    assert p.ticker == "NVDA"
    assert p.volume_vs_avg == pytest.approx(1.307, abs=0.01)


def test_daily_market_snapshot():
    snap = DailyMarketSnapshot(
        date=datetime(2026, 3, 29, tzinfo=timezone.utc),
        sp500=6592.0,
        sp500_change_pct=-0.4,
        vix=23.4,
        treasury_10y=4.31,
        brent_crude=102.3,
        gold=4280.0,
        dollar_index=104.2,
        us_gasoline=3.94,
    )
    assert snap.sp500 == 6592.0
    assert snap.brent_crude == 102.3
