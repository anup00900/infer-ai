"""Fetches actual market data for scoring matured predictions."""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

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


def fetch_actuals(date_str: str, tickers: list[str], output_dir: str) -> dict:
    """Fetch actual market data for a given date to compare against predictions.

    Args:
        date_str: YYYY-MM-DD — the date to fetch actuals for
        tickers: List of stock tickers to fetch
        output_dir: Where to save actuals.json
    """
    actuals = {"date": date_str, "fetched_at": datetime.now(timezone.utc).isoformat()}

    # Market indices
    market = {}
    for name, symbol in MARKET_TICKERS.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d")
            if not hist.empty:
                latest = hist.iloc[-1]
                prev = hist.iloc[-2]["Close"] if len(hist) > 1 else latest["Close"]
                market[name] = {
                    "close": round(float(latest["Close"]), 2),
                    "change_pct": round(((float(latest["Close"]) - float(prev)) / float(prev)) * 100, 2),
                }
        except Exception as e:
            logger.warning(f"Failed to fetch {name}: {e}")
    actuals["market"] = market

    # Individual tickers
    ticker_data = {}
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if not hist.empty:
                latest = hist.iloc[-1]
                prev = hist.iloc[-2]["Close"] if len(hist) > 1 else latest["Close"]
                ticker_data[ticker] = {
                    "close": round(float(latest["Close"]), 2),
                    "change_pct": round(((float(latest["Close"]) - float(prev)) / float(prev)) * 100, 2),
                }
        except Exception as e:
            logger.warning(f"Failed to fetch {ticker}: {e}")
    actuals["tickers"] = ticker_data

    # Save
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "actuals.json")
    with open(path, "w") as f:
        json.dump(actuals, f, indent=2)

    logger.info(f"Actuals saved to {path}")
    return actuals
