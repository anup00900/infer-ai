"""Tests for MDFormatter."""
from datetime import datetime, timezone, date

import pytest

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem, PriceData, DailyMarketSnapshot
from forward_testing.news.aggregator import AggregatedNews
from forward_testing.news.formatter import MDFormatter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snapshot() -> DailyMarketSnapshot:
    return DailyMarketSnapshot(
        date=datetime(2026, 3, 29, tzinfo=timezone.utc),
        sp500=5600.0,
        sp500_change_pct=-0.8,
        vix=21.5,
        treasury_10y=4.45,
        brent_crude=88.0,
        gold=2350.0,
        dollar_index=104.1,
        us_gasoline=3.65,
    )


def _make_prices() -> list:
    return [
        PriceData(
            ticker="NVDA",
            close=890.0,
            change_pct=3.2,
            volume=80_000_000,
            avg_volume=60_000_000,
            date=datetime(2026, 3, 29, tzinfo=timezone.utc),
        ),
        PriceData(
            ticker="AAPL",
            close=185.0,
            change_pct=-1.1,
            volume=50_000_000,
            avg_volume=55_000_000,
            date=datetime(2026, 3, 29, tzinfo=timezone.utc),
        ),
        PriceData(
            ticker="META",
            close=530.0,
            change_pct=0.5,
            volume=20_000_000,
            avg_volume=22_000_000,
            date=datetime(2026, 3, 29, tzinfo=timezone.utc),
        ),
    ]


def _make_grouped() -> dict:
    ts = datetime(2026, 3, 29, tzinfo=timezone.utc)
    return {
        "geopolitical": [
            NewsItem(
                title="Tensions rise in Middle East after drone strike",
                summary="...",
                source="gdelt",
                category="geopolitical",
                url="https://example.com/geo1",
                published_at=ts,
            ),
            NewsItem(
                title="NATO allies boost defense spending to 3% GDP",
                summary="...",
                source="reuters",
                category="geopolitical",
                url="https://example.com/geo2",
                published_at=ts,
            ),
        ],
        "us_politics": [
            NewsItem(
                title="White House signs new executive order on AI exports",
                summary="...",
                source="ap_news",
                category="us_politics",
                url="https://example.com/pol1",
                published_at=ts,
            ),
        ],
        "macro": [
            NewsItem(
                title="Fed holds rates steady at March FOMC meeting",
                summary="...",
                source="reuters",
                category="macro",
                url="https://example.com/macro1",
                published_at=ts,
            ),
            NewsItem(
                title="CPI inflation comes in at 3.1% year-over-year",
                summary="...",
                source="ap_news",
                category="macro",
                url="https://example.com/macro2",
                published_at=ts,
            ),
        ],
        "energy": [
            NewsItem(
                title="Brent crude retreats on demand fears",
                summary="...",
                source="reuters",
                category="energy",
                url="https://example.com/energy1",
                published_at=ts,
            ),
        ],
        "ai_policy": [
            NewsItem(
                title="CHIPS Act funding reaches $52B milestone",
                summary="...",
                source="reuters",
                category="ai_policy",
                url="https://example.com/ai1",
                published_at=ts,
            ),
            NewsItem(
                title="EU AI Act enforcement begins in 2026",
                summary="...",
                source="gdelt",
                category="ai_policy",
                url="https://example.com/ai2",
                published_at=ts,
            ),
        ],
        "ticker": [
            NewsItem(
                title="NVIDIA launches next-gen Blackwell GPU",
                summary="...",
                source="google_news",
                category="ticker",
                ticker="NVDA",
                url="https://example.com/nvda1",
                published_at=ts,
            ),
            NewsItem(
                title="NVIDIA beats Q1 estimates by wide margin",
                summary="...",
                source="yahoo_finance",
                category="ticker",
                ticker="NVDA",
                url="https://example.com/nvda2",
                published_at=ts,
            ),
            NewsItem(
                title="Apple faces antitrust probe in EU",
                summary="...",
                source="reuters",
                category="ticker",
                ticker="AAPL",
                url="https://example.com/aapl1",
                published_at=ts,
            ),
        ],
        "sentiment": [
            NewsItem(
                title="NVDA to the moon — earnings play thread",
                summary="...",
                source="wallstreetbets",
                category="sentiment",
                ticker="NVDA",
                url="https://reddit.com/r/wsb/nvda",
                published_at=ts,
                raw_data={
                    "subreddit": "wallstreetbets",
                    "score": 4821,
                    "num_comments": 312,
                },
            ),
            NewsItem(
                title="Is the Fed done hiking? Discussion",
                summary="...",
                source="investing",
                category="sentiment",
                ticker=None,
                url="https://reddit.com/r/investing/fed",
                published_at=ts,
                raw_data={
                    "subreddit": "investing",
                    "score": 1023,
                    "num_comments": 98,
                },
            ),
        ],
    }


def _build_aggregated() -> AggregatedNews:
    return AggregatedNews(
        date=date(2026, 3, 29),
        news_items=[],  # flat list not used by formatter directly
        prices=_make_prices(),
        market_snapshot=_make_snapshot(),
        grouped=_make_grouped(),
        source_counts={"gdelt": 2, "reuters": 3, "yahoo_finance": 1},
    )


def _get_formatted() -> str:
    config = ForwardTestingConfig()
    formatter = MDFormatter(config)
    data = _build_aggregated()
    return formatter.format(data, "March 29 2026")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMDFormatterHeader:
    def test_header_present(self):
        output = _get_formatted()
        assert "## Daily Update" in output

    def test_header_contains_date_label(self):
        output = _get_formatted()
        assert "## Daily Update — March 29 2026" in output


class TestMDFormatterSections:
    def test_market_close_header(self):
        output = _get_formatted()
        assert "### Market Close" in output

    def test_ticker_price_action_header(self):
        output = _get_formatted()
        assert "### Ticker Price Action" in output

    def test_political_geopolitical_header(self):
        output = _get_formatted()
        assert "### Political & Geopolitical Developments" in output

    def test_financial_economic_header(self):
        output = _get_formatted()
        assert "### Financial & Economic News" in output

    def test_energy_commodities_header(self):
        output = _get_formatted()
        assert "### Energy & Commodities" in output

    def test_ai_tech_header(self):
        output = _get_formatted()
        assert "### AI & Tech Industry" in output

    def test_ticker_updates_header(self):
        output = _get_formatted()
        assert "### Ticker Updates" in output

    def test_sentiment_header(self):
        output = _get_formatted()
        assert "### Market Sentiment & Retail" in output

    def test_divider_at_end(self):
        output = _get_formatted()
        assert output.strip().endswith("---")


class TestMDFormatterMarketClose:
    def test_sp500_value(self):
        output = _get_formatted()
        assert "5,600" in output

    def test_sp500_change(self):
        output = _get_formatted()
        assert "-0.8%" in output

    def test_vix_present(self):
        output = _get_formatted()
        assert "VIX" in output

    def test_treasury_present(self):
        output = _get_formatted()
        assert "10-Year Treasury" in output

    def test_brent_crude_present(self):
        output = _get_formatted()
        assert "Brent Crude" in output

    def test_gold_present(self):
        output = _get_formatted()
        assert "Gold" in output

    def test_dollar_index_present(self):
        output = _get_formatted()
        assert "Dollar Index" in output

    def test_us_gasoline_present(self):
        output = _get_formatted()
        assert "US Gasoline" in output


class TestMDFormatterTickerData:
    def test_nvda_in_price_table(self):
        output = _get_formatted()
        assert "NVDA" in output

    def test_aapl_in_price_table(self):
        output = _get_formatted()
        assert "AAPL" in output

    def test_ticker_change_pct(self):
        output = _get_formatted()
        # NVDA has +3.2% change
        assert "+3.2%" in output

    def test_sorted_by_abs_change(self):
        """NVDA (+3.2%) should appear before AAPL (-1.1%) in the price table."""
        output = _get_formatted()
        nvda_pos = output.index("| NVDA |")
        aapl_pos = output.index("| AAPL |")
        assert nvda_pos < aapl_pos

    def test_volume_vs_avg_present(self):
        output = _get_formatted()
        # NVDA volume_vs_avg = 80M/60M = 1.33x
        assert "1.33x" in output

    def test_ticker_updates_nvda(self):
        output = _get_formatted()
        assert "**NVDA:**" in output

    def test_ticker_updates_aapl(self):
        output = _get_formatted()
        assert "**AAPL:**" in output

    def test_ticker_update_headlines(self):
        output = _get_formatted()
        assert "NVIDIA launches next-gen Blackwell GPU" in output


class TestMDFormatterNewsSections:
    def test_geopolitical_tag(self):
        output = _get_formatted()
        assert "[GEOPOLITICAL]" in output

    def test_us_policy_tag(self):
        output = _get_formatted()
        assert "[US POLICY]" in output

    def test_macro_tag(self):
        output = _get_formatted()
        assert "[MACRO]" in output

    def test_energy_tag(self):
        output = _get_formatted()
        assert "[ENERGY]" in output

    def test_ai_tech_tag(self):
        output = _get_formatted()
        assert "[AI/TECH]" in output

    def test_geopolitical_title_present(self):
        output = _get_formatted()
        assert "Tensions rise in Middle East" in output

    def test_macro_title_present(self):
        output = _get_formatted()
        assert "Fed holds rates steady" in output


class TestMDFormatterSentiment:
    def test_sentiment_subreddit_tag(self):
        output = _get_formatted()
        assert "[r/wallstreetbets]" in output

    def test_sentiment_score(self):
        output = _get_formatted()
        assert "score: 4821" in output

    def test_sentiment_comments(self):
        output = _get_formatted()
        assert "comments: 312" in output

    def test_sentiment_ticker_tag(self):
        output = _get_formatted()
        assert "$NVDA" in output

    def test_sentiment_investing_subreddit(self):
        output = _get_formatted()
        assert "[r/investing]" in output


class TestMDFormatterEdgeCases:
    def test_no_market_snapshot(self):
        config = ForwardTestingConfig()
        formatter = MDFormatter(config)
        data = AggregatedNews(
            date=date(2026, 3, 29),
            grouped={},
            prices={},
        )
        output = formatter.format(data, "March 29 2026")
        assert "### Market Close" in output
        assert "*(no data)*" in output

    def test_no_prices(self):
        config = ForwardTestingConfig()
        formatter = MDFormatter(config)
        data = AggregatedNews(
            date=date(2026, 3, 29),
            grouped={},
            prices={},
        )
        output = formatter.format(data, "March 29 2026")
        assert "*(no data)*" in output

    def test_no_sentiment(self):
        config = ForwardTestingConfig()
        formatter = MDFormatter(config)
        data = AggregatedNews(
            date=date(2026, 3, 29),
            grouped={},
            prices={},
        )
        output = formatter.format(data, "March 29 2026")
        assert "*(no sentiment data)*" in output

    def test_no_ticker_updates(self):
        config = ForwardTestingConfig()
        formatter = MDFormatter(config)
        data = AggregatedNews(
            date=date(2026, 3, 29),
            grouped={},
            prices={},
        )
        output = formatter.format(data, "March 29 2026")
        assert "*(no ticker updates)*" in output
