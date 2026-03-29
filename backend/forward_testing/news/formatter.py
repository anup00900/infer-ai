from __future__ import annotations

from typing import Dict, List, Optional

from forward_testing.news.aggregator import AggregatedNews
from forward_testing.news.models import NewsItem, PriceData, DailyMarketSnapshot


# ---------------------------------------------------------------------------
# Tag mapping
# ---------------------------------------------------------------------------

_CATEGORY_TAG: Dict[str, str] = {
    "geopolitical": "GEOPOLITICAL",
    "us_politics": "US POLICY",
    "macro": "MACRO",
    "energy": "ENERGY",
    "ai_policy": "AI/TECH",
    "global_markets": "GLOBAL",
}

_SENTIMENT_CATEGORIES = {"sentiment", "reddit"}


def _tag(item: NewsItem) -> str:
    """Return the display tag for a news item."""
    if item.ticker:
        return item.ticker
    return _CATEGORY_TAG.get(item.category, item.category.upper())


def _context_for_change(change_pct: float) -> str:
    """Return a simple context string based on change magnitude."""
    abs_chg = abs(change_pct)
    if abs_chg >= 2.0:
        direction = "Strong rally" if change_pct > 0 else "Sharp sell-off"
    elif abs_chg >= 0.5:
        direction = "Modest gain" if change_pct > 0 else "Modest decline"
    else:
        direction = "Roughly flat"
    return direction


# ---------------------------------------------------------------------------
# MDFormatter
# ---------------------------------------------------------------------------

class MDFormatter:
    """Formats an AggregatedNews snapshot into a Markdown daily update."""

    def __init__(self, config) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format(self, data: AggregatedNews, date_label: str) -> str:
        sections: List[str] = []

        sections.append(f"## Daily Update — {date_label}")
        sections.append("")

        sections.append(self._market_close_section(data.market_snapshot))
        sections.append("")

        sections.append(self._ticker_price_action_section(data.prices))
        sections.append("")

        sections.append(self._news_section(
            "### Political & Geopolitical Developments",
            ["geopolitical", "us_politics"],
            data.grouped,
        ))
        sections.append("")

        sections.append(self._news_section(
            "### Financial & Economic News",
            ["macro"],
            data.grouped,
        ))
        sections.append("")

        sections.append(self._news_section(
            "### Energy & Commodities",
            ["energy"],
            data.grouped,
        ))
        sections.append("")

        sections.append(self._news_section(
            "### AI & Tech Industry",
            ["ai_policy"],
            data.grouped,
        ))
        sections.append("")

        sections.append(self._ticker_updates_section(data.grouped))
        sections.append("")

        sections.append(self._sentiment_section(data.grouped))
        sections.append("")

        sections.append("---")

        return "\n".join(sections)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _market_close_section(self, snapshot: Optional[DailyMarketSnapshot]) -> str:
        lines = ["### Market Close", ""]
        lines.append("| Indicator | Close | Change | Context |")
        lines.append("| --- | --- | --- | --- |")

        if snapshot is None:
            lines.append("| *(no data)* | — | — | — |")
            return "\n".join(lines)

        def row(indicator: str, close_str: str, change_str: str, context: str) -> str:
            return f"| {indicator} | {close_str} | {change_str} | {context} |"

        lines.append(row(
            "S&P 500",
            f"{snapshot.sp500:,.0f}",
            f"{snapshot.sp500_change_pct:+.1f}%",
            _context_for_change(snapshot.sp500_change_pct),
        ))
        lines.append(row(
            "VIX",
            f"{snapshot.vix:.2f}",
            "—",
            "High" if snapshot.vix > 25 else ("Elevated" if snapshot.vix > 20 else "Low"),
        ))
        lines.append(row(
            "10-Year Treasury",
            f"{snapshot.treasury_10y:.2f}%",
            "—",
            "Above 4%" if snapshot.treasury_10y >= 4.0 else "Below 4%",
        ))
        lines.append(row(
            "Brent Crude",
            f"${snapshot.brent_crude:.2f}",
            "—",
            "Elevated" if snapshot.brent_crude > 90 else "Moderate",
        ))
        lines.append(row(
            "Gold",
            f"${snapshot.gold:,.2f}",
            "—",
            "High" if snapshot.gold > 2000 else "Moderate",
        ))
        lines.append(row(
            "Dollar Index",
            f"{snapshot.dollar_index:.2f}",
            "—",
            "Strong" if snapshot.dollar_index > 103 else "Moderate",
        ))
        if snapshot.us_gasoline is not None:
            lines.append(row(
                "US Gasoline",
                f"${snapshot.us_gasoline:.2f}",
                "—",
                "High" if snapshot.us_gasoline > 3.5 else "Moderate",
            ))

        return "\n".join(lines)

    def _ticker_price_action_section(self, prices: List[PriceData]) -> str:
        lines = ["### Ticker Price Action", ""]
        lines.append("| Ticker | Close | Change | Volume vs Avg | Key Driver |")
        lines.append("| --- | --- | --- | --- | --- |")

        sorted_tickers = sorted(
            prices,
            key=lambda p: abs(p.change_pct),
            reverse=True,
        )

        for price in sorted_tickers:
            vol_ratio = price.volume_vs_avg
            vol_str = f"{vol_ratio:.2f}x"
            driver = _context_for_change(price.change_pct)
            lines.append(
                f"| {price.ticker} | ${price.close:,.2f} | {price.change_pct:+.1f}% "
                f"| {vol_str} | {driver} |"
            )

        if not sorted_tickers:
            lines.append("| *(no data)* | — | — | — | — |")

        return "\n".join(lines)

    def _news_section(
        self,
        header: str,
        categories: List[str],
        grouped: Dict[str, List[NewsItem]],
    ) -> str:
        lines = [header, ""]
        items: List[NewsItem] = []
        for cat in categories:
            items.extend(grouped.get(cat, []))

        if not items:
            lines.append("*(no items)*")
        else:
            for item in items:
                tag = _tag(item)
                lines.append(f"- **[{tag}]** {item.title}")
                # Include full article text if available
                if item.full_text:
                    # Indent the full text as a blockquote — no truncation
                    body = item.full_text.strip()
                    for para in body.split("\n\n"):
                        para = para.strip()
                        if para:
                            lines.append(f"  > {para}")
                    lines.append("")

        return "\n".join(lines)

    def _ticker_updates_section(self, grouped: Dict[str, List[NewsItem]]) -> str:
        lines = ["### Ticker Updates", ""]

        ticker_items: Dict[str, List[NewsItem]] = {}
        for item in grouped.get("ticker", []):
            if item.ticker:
                ticker_items.setdefault(item.ticker, []).append(item)

        # Also scan all categories for items tagged with a config ticker
        for cat_items in grouped.values():
            for item in cat_items:
                if item.ticker and item.ticker in self.config.tickers:
                    ticker_items.setdefault(item.ticker, [])
                    if item not in ticker_items[item.ticker]:
                        ticker_items[item.ticker].append(item)

        # Preserve config ticker order
        ordered_tickers = [t for t in self.config.tickers if t in ticker_items]

        if not ordered_tickers:
            lines.append("*(no ticker updates)*")
        else:
            for ticker in ordered_tickers:
                top_items = ticker_items[ticker]  # All items, no limit
                lines.append(f"**{ticker}:**")
                for item in top_items:
                    lines.append(f"- {item.title}")
                    if item.full_text:
                        body = item.full_text.strip()
                        for para in body.split("\n\n"):
                            para = para.strip()
                            if para:
                                lines.append(f"  > {para}")
                lines.append("")

        return "\n".join(lines)

    def _sentiment_section(self, grouped: Dict[str, List[NewsItem]]) -> str:
        lines = ["### Market Sentiment & Retail", ""]

        items: List[NewsItem] = []
        for cat in _SENTIMENT_CATEGORIES:
            items.extend(grouped.get(cat, []))

        if not items:
            lines.append("*(no sentiment data)*")
        else:
            for item in items:
                raw = item.raw_data or {}
                subreddit = raw.get("subreddit", item.source)
                score = raw.get("score", 0)
                comments = raw.get("num_comments", 0)
                ticker_tag = f"${item.ticker}" if item.ticker else ""
                ticker_part = f" {ticker_tag}" if ticker_tag else ""
                lines.append(
                    f"- **[r/{subreddit}]**{ticker_part} {item.title} "
                    f"(score: {score}, comments: {comments})"
                )

        return "\n".join(lines)
