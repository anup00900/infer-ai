"""
CLI entry point for the forward testing news pipeline.
Usage:
    python -m forward_testing.cli init                 # Initialize live seed from original
    python -m forward_testing.cli fetch-prices         # Fetch prices only
    python -m forward_testing.cli fetch-news           # Fetch news + append to MD
    python -m forward_testing.cli status               # Show pipeline status
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.aggregator import NewsAggregator
from forward_testing.news.formatter import MDFormatter
from forward_testing.augmenter.md_augmenter import MDAugmenter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("forward_testing")


def cmd_init(config, args):
    original = args.original or os.path.join(
        os.path.dirname(config.base_dir), "demo", "financial_seed_mar25_2026-2.md"
    )
    if not os.path.exists(original):
        # Try relative to project root
        original = os.path.join(config.base_dir, "..", "demo", "financial_seed_mar25_2026-2.md")
    if not os.path.exists(original):
        logger.error(f"Original seed file not found: {original}")
        sys.exit(1)
    augmenter = MDAugmenter(config)
    path = augmenter.initialize_from_original(original)
    logger.info(f"Live seed initialized at: {path}")


def cmd_fetch_prices(config, args):
    from forward_testing.news.sources.yahoo_finance import YahooFinanceFetcher
    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yahoo = YahooFinanceFetcher(config)
    prices = yahoo.fetch_all_prices()
    snapshot = yahoo.fetch_market_snapshot()
    day_dir = os.path.join(config.results_dir, date_str)
    os.makedirs(day_dir, exist_ok=True)
    output = {
        "date": date_str,
        "prices": [{"ticker": p.ticker, "close": p.close, "change_pct": p.change_pct} for p in prices],
        "snapshot": {
            "sp500": snapshot.sp500, "vix": snapshot.vix,
            "treasury_10y": snapshot.treasury_10y, "brent_crude": snapshot.brent_crude,
            "gold": snapshot.gold,
        } if snapshot else None,
    }
    path = os.path.join(day_dir, "prices.json")
    with open(path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"Prices saved to {path}")
    for p in prices:
        logger.info(f"  {p.ticker}: ${p.close:.2f} ({p.change_pct:+.1f}%)")


def cmd_fetch_news(config, args):
    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    date_label = dt.strftime("%B %d, %Y")
    augmenter = MDAugmenter(config)
    if not os.path.exists(augmenter.live_path):
        logger.error("Live seed not initialized. Run: python -m forward_testing.cli init")
        sys.exit(1)
    aggregator = NewsAggregator(config)
    result = aggregator.fetch_all()
    aggregator.save_raw(result, date_str)
    formatter = MDFormatter(config)
    daily_md = formatter.format(result, date_label)
    augmenter.append_daily(daily_md, date_str)
    logger.info(f"Pipeline complete for {date_str}:")
    logger.info(f"  Total news items: {len(result.news_items)}")
    logger.info(f"  Prices fetched: {len(result.prices)}")
    logger.info(f"  Sources: {result.source_counts}")


def cmd_status(config, args):
    augmenter = MDAugmenter(config)
    if os.path.exists(augmenter.live_path):
        size = os.path.getsize(augmenter.live_path)
        content = augmenter.get_full_content()
        daily_count = content.count("## Daily Update")
        logger.info(f"Live seed: {augmenter.live_path} ({size:,} bytes, {daily_count} daily updates)")
    else:
        logger.info("Live seed: NOT INITIALIZED")
    if os.path.exists(config.results_dir):
        days = sorted([d for d in os.listdir(config.results_dir) if d.startswith("20")])
        logger.info(f"Results: {len(days)} days in {config.results_dir}")
        if days:
            logger.info(f"  Latest: {days[-1]}")
    else:
        logger.info("Results: no data yet")


def main():
    parser = argparse.ArgumentParser(description="Infer Forward Testing Pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize live seed file")
    init_parser.add_argument("--original", help="Path to original seed MD file")

    prices_parser = subparsers.add_parser("fetch-prices", help="Fetch market close prices")
    prices_parser.add_argument("--date", help="Override date (YYYY-MM-DD)")

    news_parser = subparsers.add_parser("fetch-news", help="Fetch news and append to seed")
    news_parser.add_argument("--date", help="Override date (YYYY-MM-DD)")

    subparsers.add_parser("status", help="Show pipeline status")
    args = parser.parse_args()
    config = ForwardTestingConfig()
    commands = {
        "init": cmd_init,
        "fetch-prices": cmd_fetch_prices,
        "fetch-news": cmd_fetch_news,
        "status": cmd_status,
    }
    commands[args.command](config, args)


if __name__ == "__main__":
    main()
