"""Fetches actual market data for scoring matured predictions.

Uses explicit date ranges to ensure correct close prices and % changes.
Runs at 2 AM UAE when US market is fully closed for the previous day.
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import yfinance as yf

logger = logging.getLogger(__name__)

MARKET_TICKERS = {
    "sp500": "^GSPC",
    "vix": "^VIX",
    "treasury_10y": "^TNX",
    "brent_crude": "BZ=F",
    "gold": "GC=F",
    "dollar_index": "DX-Y.NYB",
}


def _get_last_two_trading_days(symbol: str, target_date: str):
    """Fetch the close price for target_date and the previous trading day.

    Uses a 10-day lookback window to handle weekends/holidays, then finds
    the exact target date and the day before it.

    Returns (target_close, prev_close, target_date_str, prev_date_str) or None.
    """
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    # Fetch 10 days ending day after target to ensure we capture it
    start = (dt - timedelta(days=10)).strftime("%Y-%m-%d")
    end = (dt + timedelta(days=2)).strftime("%Y-%m-%d")

    try:
        t = yf.Ticker(symbol)
        hist = t.history(start=start, end=end)
        if hist.empty:
            return None

        # Find rows up to and including target date
        hist.index = hist.index.tz_localize(None) if hist.index.tz else hist.index
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")

        # Get all trading days up to target
        valid = hist[hist.index.normalize() <= target_dt]
        if len(valid) < 2:
            return None

        target_row = valid.iloc[-1]
        prev_row = valid.iloc[-2]

        target_close = round(float(target_row["Close"]), 2)
        prev_close = round(float(prev_row["Close"]), 2)
        target_date_actual = valid.index[-1].strftime("%Y-%m-%d")
        prev_date_actual = valid.index[-2].strftime("%Y-%m-%d")

        return target_close, prev_close, target_date_actual, prev_date_actual

    except Exception as e:
        logger.warning(f"Failed to fetch {symbol} for {target_date}: {e}")
        return None


def fetch_actuals(date_str: str, tickers: list[str], output_dir: str) -> dict:
    """Fetch actual close prices and % change for a specific trading date.

    The % change is: (target_date_close - prev_trading_day_close) / prev_trading_day_close * 100

    Args:
        date_str: YYYY-MM-DD — the target trading date
        tickers: List of stock tickers to fetch
        output_dir: Where to save actuals.json
    """
    actuals = {
        "date": date_str,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    # Market indices
    market = {}
    for name, symbol in MARKET_TICKERS.items():
        result = _get_last_two_trading_days(symbol, date_str)
        if result:
            target_close, prev_close, target_dt, prev_dt = result
            change_pct = round(((target_close - prev_close) / prev_close) * 100, 2) if prev_close != 0 else 0
            market[name] = {
                "close": target_close,
                "prev_close": prev_close,
                "change_pct": change_pct,
                "date": target_dt,
                "prev_date": prev_dt,
            }
    actuals["market"] = market

    # Individual tickers
    ticker_data = {}
    for ticker in tickers:
        result = _get_last_two_trading_days(ticker, date_str)
        if result:
            target_close, prev_close, target_dt, prev_dt = result
            change_pct = round(((target_close - prev_close) / prev_close) * 100, 2) if prev_close != 0 else 0
            ticker_data[ticker] = {
                "close": target_close,
                "prev_close": prev_close,
                "change_pct": change_pct,
                "date": target_dt,
                "prev_date": prev_dt,
            }
    actuals["tickers"] = ticker_data

    # Save
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "actuals.json")
    with open(path, "w") as f:
        json.dump(actuals, f, indent=2)

    logger.info(f"Actuals saved to {path}")
    return actuals
