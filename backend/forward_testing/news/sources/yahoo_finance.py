import logging
from datetime import datetime, timezone
from typing import List, Optional

import yfinance as yf

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import DailyMarketSnapshot, NewsItem, PriceData

logger = logging.getLogger(__name__)

# yfinance symbols for macro market indicators
MARKET_SYMBOLS = {
    "sp500": "^GSPC",
    "vix": "^VIX",
    "treasury_10y": "^TNX",
    "brent_crude": "BZ=F",
    "gold": "GC=F",
    "dollar_index": "DX-Y.NYB",
    "us_gasoline": "RB=F",
}


class YahooFinanceFetcher:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config

    def fetch_price(self, ticker: str) -> Optional[PriceData]:
        """Fetch latest price data for a single ticker using 2-day history."""
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")

            if hist is None or len(hist) < 2:
                logger.warning(f"YahooFinance: insufficient history for {ticker} (got {len(hist) if hist is not None else 0} rows)")
                return None

            latest = hist.iloc[-1]
            prev = hist.iloc[-2]

            close = float(latest["Close"])
            prev_close = float(prev["Close"])
            change_pct = ((close - prev_close) / prev_close) * 100 if prev_close != 0 else 0.0
            volume = int(latest["Volume"])

            info = t.info or {}
            avg_volume = int(info.get("averageVolume", 0) or 0)

            # Use the index (timestamp) as the date
            date = latest.name
            if hasattr(date, "to_pydatetime"):
                date = date.to_pydatetime()
            if not isinstance(date, datetime):
                date = datetime.now(timezone.utc)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)

            return PriceData(
                ticker=ticker,
                close=close,
                change_pct=change_pct,
                volume=volume,
                avg_volume=avg_volume,
                date=date,
                open=float(latest["Open"]) if "Open" in latest else None,
                high=float(latest["High"]) if "High" in latest else None,
                low=float(latest["Low"]) if "Low" in latest else None,
            )
        except Exception as e:
            logger.warning(f"YahooFinance: fetch_price failed for {ticker}: {e}")
            return None

    def fetch_all_prices(self) -> List[PriceData]:
        """Fetch price data for all configured tickers."""
        results: List[PriceData] = []
        for ticker in self.config.tickers:
            price = self.fetch_price(ticker)
            if price is not None:
                results.append(price)
        logger.info(f"YahooFinance: fetched prices for {len(results)}/{len(self.config.tickers)} tickers")
        return results

    def fetch_ticker_news(self, ticker: str) -> List[NewsItem]:
        """Fetch news items for a single ticker from yfinance."""
        try:
            t = yf.Ticker(ticker)
            raw_news = t.news or []
            items: List[NewsItem] = []
            for article in raw_news:
                # yfinance news items are dicts with providerPublishTime (unix timestamp)
                pub_ts = article.get("providerPublishTime")
                if pub_ts:
                    published_at = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
                else:
                    published_at = datetime.now(timezone.utc)

                items.append(NewsItem(
                    title=article.get("title", ""),
                    summary=article.get("summary", article.get("title", "")),
                    source="yahoo_finance",
                    category="ticker",
                    ticker=ticker,
                    url=article.get("link", ""),
                    published_at=published_at,
                    raw_data=article,
                ))
            return items
        except Exception as e:
            logger.warning(f"YahooFinance: fetch_ticker_news failed for {ticker}: {e}")
            return []

    def fetch_all_news(self) -> List[NewsItem]:
        """Fetch news for all configured tickers."""
        all_items: List[NewsItem] = []
        for ticker in self.config.tickers:
            items = self.fetch_ticker_news(ticker)
            all_items.extend(items)
        logger.info(f"YahooFinance: fetched {len(all_items)} total news items")
        return all_items

    def fetch_market_snapshot(self) -> Optional[DailyMarketSnapshot]:
        """Fetch macro market indicators to build a DailyMarketSnapshot."""
        try:
            values: dict = {}
            dates: list = []

            for field_name, symbol in MARKET_SYMBOLS.items():
                try:
                    t = yf.Ticker(symbol)
                    hist = t.history(period="2d")
                    if hist is None or len(hist) == 0:
                        logger.warning(f"YahooFinance: no history for {symbol}")
                        values[field_name] = None
                        continue

                    latest = hist.iloc[-1]
                    values[field_name] = float(latest["Close"])

                    if field_name == "sp500":
                        # Also compute change_pct for SP500
                        if len(hist) >= 2:
                            prev_close = float(hist.iloc[-2]["Close"])
                            cur_close = float(latest["Close"])
                            values["sp500_change_pct"] = (
                                ((cur_close - prev_close) / prev_close) * 100
                                if prev_close != 0 else 0.0
                            )
                        else:
                            values["sp500_change_pct"] = 0.0

                        date = latest.name
                        if hasattr(date, "to_pydatetime"):
                            date = date.to_pydatetime()
                        if not isinstance(date, datetime):
                            date = datetime.now(timezone.utc)
                        if date.tzinfo is None:
                            date = date.replace(tzinfo=timezone.utc)
                        dates.append(date)

                except Exception as e:
                    logger.warning(f"YahooFinance: failed to fetch {symbol} ({field_name}): {e}")
                    values[field_name] = None

            snapshot_date = dates[0] if dates else datetime.now(timezone.utc)

            # sp500 and vix are required; treat missing as failure
            if values.get("sp500") is None or values.get("vix") is None:
                logger.warning("YahooFinance: missing required snapshot fields (sp500/vix)")
                return None

            return DailyMarketSnapshot(
                date=snapshot_date,
                sp500=values.get("sp500", 0.0),
                sp500_change_pct=values.get("sp500_change_pct", 0.0),
                vix=values.get("vix", 0.0),
                treasury_10y=values.get("treasury_10y", 0.0),
                brent_crude=values.get("brent_crude", 0.0),
                gold=values.get("gold", 0.0),
                dollar_index=values.get("dollar_index", 0.0),
                us_gasoline=values.get("us_gasoline"),
            )
        except Exception as e:
            logger.warning(f"YahooFinance: fetch_market_snapshot failed: {e}")
            return None
