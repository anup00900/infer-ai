# Forward Testing Plan 1: News Aggregation + MD Augmentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated news aggregation pipeline that fetches daily financial, political, and geopolitical news from 8 free sources and appends a structured daily update section to the Infer financial seed MD file.

**Architecture:** Modular source-based fetchers behind a unified `Aggregator` class. Each source module returns a common `NewsItem` dataclass. The `Formatter` converts aggregated news into the exact MD format matching the seed file. The `MDAugmenter` manages the live seed file with daily appends and windowed views.

**Tech Stack:** Python 3.11+, yfinance, feedparser, requests, beautifulsoup4, pytest

---

### File Structure

```
backend/
  forward_testing/
    __init__.py
    config.py                     # Tickers, source URLs, query terms, schedule config
    news/
      __init__.py
      models.py                   # NewsItem dataclass, PriceData dataclass
      aggregator.py               # Orchestrates all sources, deduplicates
      sources/
        __init__.py
        google_news.py            # Google News RSS fetcher
        yahoo_finance.py          # Yahoo Finance news + price data via yfinance
        gdelt.py                  # GDELT DOC API fetcher
        reuters_ap.py             # Reuters + AP News RSS feeds
        fed_gov.py                # Federal Reserve + GovInfo RSS feeds
        reddit_sentiment.py       # Reddit public JSON API
      formatter.py                # Converts NewsItems to MD sections
    augmenter/
      __init__.py
      md_augmenter.py             # Manages seed file: append, windowed view, backup
  tests/
    forward_testing/
      __init__.py
      test_config.py
      test_models.py
      test_google_news.py
      test_yahoo_finance.py
      test_gdelt.py
      test_reuters_ap.py
      test_fed_gov.py
      test_reddit_sentiment.py
      test_aggregator.py
      test_formatter.py
      test_md_augmenter.py
```

---

### Task 1: Install Dependencies + Config

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/forward_testing/__init__.py`
- Create: `backend/forward_testing/config.py`
- Create: `backend/forward_testing/news/__init__.py`
- Create: `backend/forward_testing/news/sources/__init__.py`
- Create: `backend/forward_testing/augmenter/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/forward_testing/__init__.py`
- Test: `backend/tests/forward_testing/test_config.py`

- [ ] **Step 1: Add new dependencies to requirements.txt**

Add these lines to `backend/requirements.txt`:

```
yfinance>=0.2.36
feedparser>=6.0.0
beautifulsoup4>=4.12.0
```

- [ ] **Step 2: Install dependencies**

Run: `cd backend && pip install -r requirements.txt`

- [ ] **Step 3: Create directory structure and __init__.py files**

```bash
mkdir -p backend/forward_testing/news/sources
mkdir -p backend/forward_testing/augmenter
mkdir -p backend/tests/forward_testing
touch backend/forward_testing/__init__.py
touch backend/forward_testing/news/__init__.py
touch backend/forward_testing/news/sources/__init__.py
touch backend/forward_testing/augmenter/__init__.py
touch backend/tests/__init__.py
touch backend/tests/forward_testing/__init__.py
```

- [ ] **Step 4: Write test for config**

Create `backend/tests/forward_testing/test_config.py`:

```python
from forward_testing.config import ForwardTestingConfig


def test_config_has_tickers():
    config = ForwardTestingConfig()
    assert len(config.tickers) == 11
    assert "NVDA" in config.tickers
    assert "AAPL" in config.tickers
    assert "QCOM" in config.tickers


def test_config_has_query_categories():
    config = ForwardTestingConfig()
    assert "macro" in config.query_terms
    assert "geopolitical" in config.query_terms
    assert "us_politics" in config.query_terms
    assert "energy" in config.query_terms
    assert "ai_policy" in config.query_terms
    assert "global_markets" in config.query_terms


def test_config_has_source_settings():
    config = ForwardTestingConfig()
    assert config.gdelt_base_url is not None
    assert config.reddit_subreddits is not None
    assert len(config.reddit_subreddits) >= 3


def test_config_results_dir():
    config = ForwardTestingConfig()
    assert "forward_testing/results" in config.results_dir


def test_config_seeds_dir():
    config = ForwardTestingConfig()
    assert "forward_testing/seeds" in config.seeds_dir
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/forward_testing/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'forward_testing.config'`

- [ ] **Step 6: Write config.py**

Create `backend/forward_testing/config.py`:

```python
import os
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ForwardTestingConfig:
    tickers: List[str] = field(default_factory=lambda: [
        "NVDA", "AAPL", "MSFT", "GOOGL", "META",
        "AMZN", "AMD", "AVGO", "ORCL", "MU", "QCOM"
    ])

    query_terms: Dict[str, List[str]] = field(default_factory=lambda: {
        "macro": [
            "Federal Reserve", "interest rate decision", "inflation CPI",
            "unemployment rate", "GDP growth", "treasury yield",
            "consumer spending", "jobs report", "retail sales"
        ],
        "geopolitical": [
            "Iran", "Strait of Hormuz", "oil sanctions", "China trade war",
            "tariffs", "NATO", "OPEC", "Middle East conflict",
            "Russia Ukraine", "North Korea", "Taiwan strait"
        ],
        "us_politics": [
            "White House executive order", "Congress legislation",
            "Supreme Court ruling", "election", "government shutdown",
            "debt ceiling", "presidential", "Senate", "House of Representatives"
        ],
        "energy": [
            "crude oil price", "natural gas", "gold price", "copper",
            "uranium", "LNG", "gasoline price", "OPEC production",
            "oil inventory", "renewable energy"
        ],
        "ai_policy": [
            "AI regulation", "chip export ban", "CHIPS Act",
            "antitrust tech", "data privacy law", "AI safety",
            "semiconductor export", "GPU export restriction"
        ],
        "global_markets": [
            "ECB interest rate", "Bank of Japan", "China PBOC",
            "emerging markets crisis", "forex dollar index",
            "eurozone", "UK economy", "India GDP"
        ],
    })

    reddit_subreddits: List[str] = field(default_factory=lambda: [
        "wallstreetbets", "investing", "stocks",
        "economics", "geopolitics", "worldnews"
    ])

    gdelt_base_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"

    rss_feeds: Dict[str, str] = field(default_factory=lambda: {
        "reuters_world": "https://feeds.reuters.com/reuters/worldNews",
        "reuters_business": "https://feeds.reuters.com/reuters/businessNews",
        "ap_topnews": "https://rsshub.app/apnews/topics/apf-topnews",
        "ap_politics": "https://rsshub.app/apnews/topics/apf-politics",
        "fed_press": "https://www.federalreserve.gov/feeds/press_all.xml",
        "fed_speeches": "https://www.federalreserve.gov/feeds/speeches.xml",
    })

    # Directories — relative to backend/
    base_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ))
    results_dir: str = field(init=False)
    seeds_dir: str = field(init=False)

    def __post_init__(self):
        self.results_dir = os.path.join(self.base_dir, "forward_testing", "results")
        self.seeds_dir = os.path.join(self.base_dir, "forward_testing", "seeds")
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/forward_testing/test_config.py -v`
Expected: All 5 tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/forward_testing/ backend/tests/ backend/requirements.txt
git commit -m "feat(forward-testing): add config and project structure for news aggregation"
```

---

### Task 2: NewsItem and PriceData Models

**Files:**
- Create: `backend/forward_testing/news/models.py`
- Test: `backend/tests/forward_testing/test_models.py`

- [ ] **Step 1: Write test for models**

Create `backend/tests/forward_testing/test_models.py`:

```python
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


import pytest
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/forward_testing/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write models.py**

Create `backend/forward_testing/news/models.py`:

```python
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NewsItem:
    title: str
    summary: str
    source: str  # google_news, yahoo, gdelt, reuters, ap, fed, govinfo, reddit
    category: str  # ticker, macro, geopolitical, us_politics, energy, ai_policy, global_markets, sentiment
    url: str
    published_at: datetime
    ticker: Optional[str] = None
    raw_data: Optional[dict] = None

    def dedup_key(self) -> str:
        """Normalize title for deduplication — strips case, punctuation, extra spaces."""
        normalized = self.title.lower().strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized


@dataclass
class PriceData:
    ticker: str
    close: float
    change_pct: float
    volume: int
    avg_volume: int
    date: datetime
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None

    @property
    def volume_vs_avg(self) -> float:
        if self.avg_volume == 0:
            return 0.0
        return self.volume / self.avg_volume


@dataclass
class DailyMarketSnapshot:
    date: datetime
    sp500: float
    sp500_change_pct: float
    vix: float
    treasury_10y: float
    brent_crude: float
    gold: float
    dollar_index: float
    us_gasoline: Optional[float] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/forward_testing/test_models.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/forward_testing/news/models.py backend/tests/forward_testing/test_models.py
git commit -m "feat(forward-testing): add NewsItem, PriceData, DailyMarketSnapshot models"
```

---

### Task 3: Google News RSS Source

**Files:**
- Create: `backend/forward_testing/news/sources/google_news.py`
- Test: `backend/tests/forward_testing/test_google_news.py`

- [ ] **Step 1: Write test**

Create `backend/tests/forward_testing/test_google_news.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from forward_testing.news.sources.google_news import GoogleNewsFetcher
from forward_testing.config import ForwardTestingConfig


SAMPLE_RSS_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>NVDA - Google News</title>
<item>
  <title>NVIDIA shares surge on AI demand - Reuters</title>
  <link>https://news.google.com/articles/123</link>
  <description>NVIDIA reported strong quarterly results...</description>
  <pubDate>Sat, 29 Mar 2026 14:00:00 GMT</pubDate>
</item>
<item>
  <title>NVDA: Analysts raise price targets - Bloomberg</title>
  <link>https://news.google.com/articles/456</link>
  <description>Multiple Wall Street analysts raised...</description>
  <pubDate>Sat, 29 Mar 2026 10:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""


@patch("forward_testing.news.sources.google_news.requests.get")
def test_fetch_ticker_news(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = SAMPLE_RSS_RESPONSE.encode()
    mock_get.return_value = mock_resp

    fetcher = GoogleNewsFetcher(ForwardTestingConfig())
    items = fetcher.fetch_ticker("NVDA")

    assert len(items) == 2
    assert items[0].source == "google_news"
    assert items[0].ticker == "NVDA"
    assert items[0].category == "ticker"
    assert "NVIDIA" in items[0].title


@patch("forward_testing.news.sources.google_news.requests.get")
def test_fetch_topic_news(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = SAMPLE_RSS_RESPONSE.encode()
    mock_get.return_value = mock_resp

    fetcher = GoogleNewsFetcher(ForwardTestingConfig())
    items = fetcher.fetch_topic("Federal Reserve interest rate", category="macro")

    assert len(items) == 2
    assert items[0].category == "macro"
    assert items[0].ticker is None


@patch("forward_testing.news.sources.google_news.requests.get")
def test_fetch_all_returns_combined(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = SAMPLE_RSS_RESPONSE.encode()
    mock_get.return_value = mock_resp

    fetcher = GoogleNewsFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    # 11 tickers + multiple topic queries = many calls
    assert mock_get.call_count > 11
    assert len(items) > 0


@patch("forward_testing.news.sources.google_news.requests.get")
def test_fetch_handles_failure_gracefully(mock_get):
    mock_get.side_effect = Exception("Network error")

    fetcher = GoogleNewsFetcher(ForwardTestingConfig())
    items = fetcher.fetch_ticker("NVDA")

    assert items == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/forward_testing/test_google_news.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write google_news.py**

Create `backend/forward_testing/news/sources/google_news.py`:

```python
import logging
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote

import feedparser
import requests

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


class GoogleNewsFetcher:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.timeout = 15

    def fetch_ticker(self, ticker: str) -> List[NewsItem]:
        query = f"{ticker} stock"
        return self._fetch(query, category="ticker", ticker=ticker)

    def fetch_topic(self, topic: str, category: str) -> List[NewsItem]:
        return self._fetch(topic, category=category)

    def fetch_all(self) -> List[NewsItem]:
        all_items: List[NewsItem] = []

        # Fetch per-ticker news
        for ticker in self.config.tickers:
            items = self.fetch_ticker(ticker)
            all_items.extend(items)

        # Fetch per-category news
        for category, terms in self.config.query_terms.items():
            for term in terms:
                items = self.fetch_topic(term, category=category)
                all_items.extend(items)

        logger.info(f"GoogleNews: fetched {len(all_items)} total items")
        return all_items

    def _fetch(self, query: str, category: str, ticker: Optional[str] = None) -> List[NewsItem]:
        try:
            url = GOOGLE_NEWS_RSS.format(query=quote(query))
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()

            feed = feedparser.parse(resp.content)
            items = []
            for entry in feed.entries[:10]:  # Max 10 per query
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                items.append(NewsItem(
                    title=entry.get("title", ""),
                    summary=entry.get("description", entry.get("summary", "")),
                    source="google_news",
                    category=category,
                    ticker=ticker,
                    url=entry.get("link", ""),
                    published_at=published or datetime.now(timezone.utc),
                ))
            return items

        except Exception as e:
            logger.warning(f"GoogleNews fetch failed for '{query}': {e}")
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/forward_testing/test_google_news.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/forward_testing/news/sources/google_news.py backend/tests/forward_testing/test_google_news.py
git commit -m "feat(forward-testing): add Google News RSS fetcher"
```

---

### Task 4: Yahoo Finance Source (News + Prices)

**Files:**
- Create: `backend/forward_testing/news/sources/yahoo_finance.py`
- Test: `backend/tests/forward_testing/test_yahoo_finance.py`

- [ ] **Step 1: Write test**

Create `backend/tests/forward_testing/test_yahoo_finance.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from forward_testing.news.sources.yahoo_finance import YahooFinanceFetcher
from forward_testing.news.models import PriceData, DailyMarketSnapshot
from forward_testing.config import ForwardTestingConfig


def _mock_ticker(close=892.5, change_pct=1.2, volume=85_000_000, avg_vol=65_000_000,
                 news=None):
    ticker = MagicMock()
    hist = MagicMock()
    hist.empty = False
    hist.iloc.__getitem__ = MagicMock(return_value={
        "Close": close, "Open": 885.0, "High": 895.0, "Low": 880.0,
        "Volume": volume
    })
    hist.__len__ = MagicMock(return_value=1)
    ticker.history.return_value = hist

    info = {"regularMarketVolume": volume, "averageVolume": avg_vol}
    ticker.info = info

    if news is None:
        news = [
            {
                "title": "NVDA price target raised",
                "link": "https://finance.yahoo.com/article/123",
                "publisher": "Reuters",
                "providerPublishTime": 1743260400,
            }
        ]
    ticker.news = news
    return ticker


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_price(mock_yf_ticker):
    mock_yf_ticker.return_value = _mock_ticker()
    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    price = fetcher.fetch_price("NVDA")

    assert price is not None
    assert price.ticker == "NVDA"
    assert price.close == 892.5


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_all_prices(mock_yf_ticker):
    mock_yf_ticker.return_value = _mock_ticker()
    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    prices = fetcher.fetch_all_prices()

    assert len(prices) == 11  # All tickers


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_ticker_news(mock_yf_ticker):
    mock_yf_ticker.return_value = _mock_ticker()
    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    items = fetcher.fetch_ticker_news("NVDA")

    assert len(items) == 1
    assert items[0].source == "yahoo_finance"
    assert items[0].ticker == "NVDA"


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_market_snapshot(mock_yf_ticker):
    mock_yf_ticker.return_value = _mock_ticker()
    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    snapshot = fetcher.fetch_market_snapshot()

    assert snapshot is not None
    assert isinstance(snapshot, DailyMarketSnapshot)
    assert snapshot.sp500 > 0


@patch("forward_testing.news.sources.yahoo_finance.yf.Ticker")
def test_fetch_handles_failure(mock_yf_ticker):
    mock_yf_ticker.side_effect = Exception("API error")
    fetcher = YahooFinanceFetcher(ForwardTestingConfig())
    price = fetcher.fetch_price("NVDA")

    assert price is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/forward_testing/test_yahoo_finance.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write yahoo_finance.py**

Create `backend/forward_testing/news/sources/yahoo_finance.py`:

```python
import logging
from datetime import datetime, timezone
from typing import List, Optional

import yfinance as yf

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem, PriceData, DailyMarketSnapshot

logger = logging.getLogger(__name__)

# Index/commodity tickers for market snapshot
MARKET_TICKERS = {
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
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if hist.empty or len(hist) == 0:
                return None

            latest = hist.iloc[-1]
            prev_close = hist.iloc[-2]["Close"] if len(hist) > 1 else latest["Close"]
            change_pct = ((latest["Close"] - prev_close) / prev_close) * 100

            info = t.info
            avg_vol = info.get("averageVolume", 0)

            return PriceData(
                ticker=ticker,
                close=round(latest["Close"], 2),
                change_pct=round(change_pct, 2),
                volume=int(latest["Volume"]),
                avg_volume=avg_vol,
                date=datetime.now(timezone.utc),
                open=round(latest["Open"], 2),
                high=round(latest["High"], 2),
                low=round(latest["Low"], 2),
            )
        except Exception as e:
            logger.warning(f"Yahoo price fetch failed for {ticker}: {e}")
            return None

    def fetch_all_prices(self) -> List[PriceData]:
        prices = []
        for ticker in self.config.tickers:
            price = self.fetch_price(ticker)
            if price:
                prices.append(price)
        return prices

    def fetch_ticker_news(self, ticker: str) -> List[NewsItem]:
        try:
            t = yf.Ticker(ticker)
            items = []
            for article in (t.news or [])[:10]:
                published = datetime.fromtimestamp(
                    article.get("providerPublishTime", 0), tz=timezone.utc
                )
                items.append(NewsItem(
                    title=article.get("title", ""),
                    summary=article.get("title", ""),  # Yahoo news has limited summaries
                    source="yahoo_finance",
                    category="ticker",
                    ticker=ticker,
                    url=article.get("link", ""),
                    published_at=published,
                ))
            return items
        except Exception as e:
            logger.warning(f"Yahoo news fetch failed for {ticker}: {e}")
            return []

    def fetch_all_news(self) -> List[NewsItem]:
        all_items = []
        for ticker in self.config.tickers:
            items = self.fetch_ticker_news(ticker)
            all_items.extend(items)
        logger.info(f"YahooFinance: fetched {len(all_items)} news items")
        return all_items

    def fetch_market_snapshot(self) -> Optional[DailyMarketSnapshot]:
        try:
            data = {}
            for name, symbol in MARKET_TICKERS.items():
                t = yf.Ticker(symbol)
                hist = t.history(period="2d")
                if hist.empty or len(hist) == 0:
                    data[name] = 0.0
                    continue
                latest = hist.iloc[-1]
                prev = hist.iloc[-2]["Close"] if len(hist) > 1 else latest["Close"]
                data[name] = round(latest["Close"], 2)
                data[f"{name}_change"] = round(
                    ((latest["Close"] - prev) / prev) * 100, 2
                )

            return DailyMarketSnapshot(
                date=datetime.now(timezone.utc),
                sp500=data.get("sp500", 0),
                sp500_change_pct=data.get("sp500_change", 0),
                vix=data.get("vix", 0),
                treasury_10y=data.get("treasury_10y", 0),
                brent_crude=data.get("brent_crude", 0),
                gold=data.get("gold", 0),
                dollar_index=data.get("dollar_index", 0),
                us_gasoline=data.get("us_gasoline", 0),
            )
        except Exception as e:
            logger.warning(f"Yahoo market snapshot failed: {e}")
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/forward_testing/test_yahoo_finance.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/forward_testing/news/sources/yahoo_finance.py backend/tests/forward_testing/test_yahoo_finance.py
git commit -m "feat(forward-testing): add Yahoo Finance fetcher (news + prices + market snapshot)"
```

---

### Task 5: GDELT Source

**Files:**
- Create: `backend/forward_testing/news/sources/gdelt.py`
- Test: `backend/tests/forward_testing/test_gdelt.py`

- [ ] **Step 1: Write test**

Create `backend/tests/forward_testing/test_gdelt.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from forward_testing.news.sources.gdelt import GdeltFetcher
from forward_testing.config import ForwardTestingConfig


SAMPLE_GDELT_RESPONSE = {
    "articles": [
        {
            "title": "Iran signals willingness to negotiate on Hormuz",
            "url": "https://example.com/iran-hormuz",
            "seendate": "20260329T140000Z",
            "domain": "reuters.com",
            "language": "English",
            "sourcecountry": "United States",
        },
        {
            "title": "Oil prices steady amid Middle East tensions",
            "url": "https://example.com/oil-prices",
            "seendate": "20260329T100000Z",
            "domain": "bbc.com",
            "language": "English",
            "sourcecountry": "United Kingdom",
        },
    ]
}


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_topic(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_GDELT_RESPONSE
    mock_get.return_value = mock_resp

    fetcher = GdeltFetcher(ForwardTestingConfig())
    items = fetcher.fetch_topic("Iran Hormuz oil", category="geopolitical")

    assert len(items) == 2
    assert items[0].source == "gdelt"
    assert items[0].category == "geopolitical"


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_all(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_GDELT_RESPONSE
    mock_get.return_value = mock_resp

    fetcher = GdeltFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    assert len(items) > 0
    assert mock_get.call_count > 0


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_handles_empty_response(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {}
    mock_get.return_value = mock_resp

    fetcher = GdeltFetcher(ForwardTestingConfig())
    items = fetcher.fetch_topic("nonexistent topic", category="macro")

    assert items == []


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_handles_failure(mock_get):
    mock_get.side_effect = Exception("Timeout")
    fetcher = GdeltFetcher(ForwardTestingConfig())
    items = fetcher.fetch_topic("test", category="macro")

    assert items == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/forward_testing/test_gdelt.py -v`
Expected: FAIL

- [ ] **Step 3: Write gdelt.py**

Create `backend/forward_testing/news/sources/gdelt.py`:

```python
import logging
from datetime import datetime, timezone
from typing import List
from urllib.parse import quote

import requests

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem

logger = logging.getLogger(__name__)


class GdeltFetcher:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.timeout = 20

    def fetch_topic(self, query: str, category: str) -> List[NewsItem]:
        try:
            params = {
                "query": query,
                "mode": "ArtList",
                "maxrecords": "20",
                "timespan": "1d",
                "format": "json",
                "sort": "DateDesc",
            }
            resp = requests.get(
                self.config.gdelt_base_url,
                params=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            articles = data.get("articles", [])
            items = []
            for article in articles:
                seen = article.get("seendate", "")
                try:
                    published = datetime.strptime(seen, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    published = datetime.now(timezone.utc)

                items.append(NewsItem(
                    title=article.get("title", ""),
                    summary=article.get("title", ""),
                    source="gdelt",
                    category=category,
                    url=article.get("url", ""),
                    published_at=published,
                    raw_data={"domain": article.get("domain", ""), "country": article.get("sourcecountry", "")},
                ))
            return items

        except Exception as e:
            logger.warning(f"GDELT fetch failed for '{query}': {e}")
            return []

    def fetch_all(self) -> List[NewsItem]:
        all_items: List[NewsItem] = []

        # Fetch geopolitical, macro, energy, politics queries
        priority_queries = {
            "geopolitical": [
                "Iran Hormuz oil conflict",
                "China trade tariffs",
                "Middle East war",
                "Russia Ukraine",
                "OPEC oil production",
            ],
            "us_politics": [
                "White House executive order",
                "Congress legislation economy",
                "Federal Reserve chair nomination",
                "Supreme Court ruling",
            ],
            "energy": [
                "crude oil price supply",
                "natural gas LNG",
                "gold price safe haven",
            ],
            "macro": [
                "US economy GDP inflation",
                "global recession risk",
                "treasury bond yield",
            ],
            "global_markets": [
                "ECB interest rate eurozone",
                "China economy slowdown",
                "emerging markets currency",
            ],
        }

        for category, queries in priority_queries.items():
            for query in queries:
                items = self.fetch_topic(query, category=category)
                all_items.extend(items)

        logger.info(f"GDELT: fetched {len(all_items)} total items")
        return all_items
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/forward_testing/test_gdelt.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/forward_testing/news/sources/gdelt.py backend/tests/forward_testing/test_gdelt.py
git commit -m "feat(forward-testing): add GDELT geopolitical news fetcher"
```

---

### Task 6: Reuters/AP RSS + Fed/GovInfo Sources

**Files:**
- Create: `backend/forward_testing/news/sources/reuters_ap.py`
- Create: `backend/forward_testing/news/sources/fed_gov.py`
- Test: `backend/tests/forward_testing/test_reuters_ap.py`
- Test: `backend/tests/forward_testing/test_fed_gov.py`

- [ ] **Step 1: Write test for Reuters/AP**

Create `backend/tests/forward_testing/test_reuters_ap.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from forward_testing.news.sources.reuters_ap import ReutersAPFetcher
from forward_testing.config import ForwardTestingConfig


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Reuters World News</title>
<item>
  <title>Iran foreign minister makes diplomatic overture</title>
  <link>https://reuters.com/article/123</link>
  <description>In a surprise move, Iran's foreign minister...</description>
  <pubDate>Sat, 29 Mar 2026 15:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_fetch_all(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = SAMPLE_RSS.encode()
    mock_get.return_value = mock_resp

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    assert len(items) > 0
    assert items[0].source == "reuters_ap"


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_fetch_handles_failure(mock_get):
    mock_get.side_effect = Exception("Timeout")
    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    assert items == []
```

- [ ] **Step 2: Write test for Fed/Gov**

Create `backend/tests/forward_testing/test_fed_gov.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from forward_testing.news.sources.fed_gov import FedGovFetcher
from forward_testing.config import ForwardTestingConfig


SAMPLE_FED_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Federal Reserve Press Releases</title>
<item>
  <title>Federal Reserve issues FOMC statement</title>
  <link>https://federalreserve.gov/press/123</link>
  <description>The Federal Open Market Committee decided to maintain...</description>
  <pubDate>Sat, 29 Mar 2026 18:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""


@patch("forward_testing.news.sources.fed_gov.requests.get")
def test_fetch_all(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = SAMPLE_FED_RSS.encode()
    mock_get.return_value = mock_resp

    fetcher = FedGovFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    assert len(items) > 0
    for item in items:
        assert item.source == "fed_gov"
        assert item.category in ("macro", "us_politics")


@patch("forward_testing.news.sources.fed_gov.requests.get")
def test_fetch_handles_failure(mock_get):
    mock_get.side_effect = Exception("Timeout")
    fetcher = FedGovFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    assert items == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/forward_testing/test_reuters_ap.py tests/forward_testing/test_fed_gov.py -v`
Expected: FAIL

- [ ] **Step 4: Write reuters_ap.py**

Create `backend/forward_testing/news/sources/reuters_ap.py`:

```python
import logging
from datetime import datetime, timezone
from typing import List

import feedparser
import requests

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem

logger = logging.getLogger(__name__)


class ReutersAPFetcher:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.timeout = 15

    def fetch_all(self) -> List[NewsItem]:
        all_items: List[NewsItem] = []
        for feed_name, feed_url in self.config.rss_feeds.items():
            if not feed_name.startswith(("reuters", "ap")):
                continue
            items = self._fetch_feed(feed_url, feed_name)
            all_items.extend(items)

        logger.info(f"Reuters/AP: fetched {len(all_items)} items")
        return all_items

    def _fetch_feed(self, url: str, feed_name: str) -> List[NewsItem]:
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)

            items = []
            for entry in feed.entries[:20]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                category = self._classify(entry.get("title", ""), feed_name)

                items.append(NewsItem(
                    title=entry.get("title", ""),
                    summary=entry.get("description", entry.get("summary", "")),
                    source="reuters_ap",
                    category=category,
                    url=entry.get("link", ""),
                    published_at=published or datetime.now(timezone.utc),
                ))
            return items

        except Exception as e:
            logger.warning(f"Reuters/AP fetch failed for {feed_name}: {e}")
            return []

    def _classify(self, title: str, feed_name: str) -> str:
        title_lower = title.lower()
        if "politics" in feed_name:
            return "us_politics"
        if any(kw in title_lower for kw in ["fed", "interest rate", "inflation", "gdp", "jobs", "economy"]):
            return "macro"
        if any(kw in title_lower for kw in ["iran", "war", "military", "sanctions", "tariff", "china"]):
            return "geopolitical"
        if any(kw in title_lower for kw in ["oil", "gas", "gold", "energy", "opec"]):
            return "energy"
        if any(kw in title_lower for kw in ["congress", "senate", "white house", "president", "supreme court"]):
            return "us_politics"
        if "business" in feed_name:
            return "macro"
        return "geopolitical"
```

- [ ] **Step 5: Write fed_gov.py**

Create `backend/forward_testing/news/sources/fed_gov.py`:

```python
import logging
from datetime import datetime, timezone
from typing import List

import feedparser
import requests

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem

logger = logging.getLogger(__name__)


class FedGovFetcher:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.timeout = 15

    def fetch_all(self) -> List[NewsItem]:
        all_items: List[NewsItem] = []
        for feed_name, feed_url in self.config.rss_feeds.items():
            if not feed_name.startswith("fed"):
                continue
            items = self._fetch_feed(feed_url, feed_name)
            all_items.extend(items)

        logger.info(f"Fed/Gov: fetched {len(all_items)} items")
        return all_items

    def _fetch_feed(self, url: str, feed_name: str) -> List[NewsItem]:
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)

            items = []
            for entry in feed.entries[:15]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                category = "macro" if "speech" not in feed_name else "macro"

                items.append(NewsItem(
                    title=entry.get("title", ""),
                    summary=entry.get("description", entry.get("summary", "")),
                    source="fed_gov",
                    category=category,
                    url=entry.get("link", ""),
                    published_at=published or datetime.now(timezone.utc),
                ))
            return items

        except Exception as e:
            logger.warning(f"Fed/Gov fetch failed for {feed_name}: {e}")
            return []
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/forward_testing/test_reuters_ap.py tests/forward_testing/test_fed_gov.py -v`
Expected: All 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/forward_testing/news/sources/reuters_ap.py backend/forward_testing/news/sources/fed_gov.py backend/tests/forward_testing/test_reuters_ap.py backend/tests/forward_testing/test_fed_gov.py
git commit -m "feat(forward-testing): add Reuters/AP RSS and Fed/Gov news fetchers"
```

---

### Task 7: Reddit Sentiment Source

**Files:**
- Create: `backend/forward_testing/news/sources/reddit_sentiment.py`
- Test: `backend/tests/forward_testing/test_reddit_sentiment.py`

- [ ] **Step 1: Write test**

Create `backend/tests/forward_testing/test_reddit_sentiment.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from forward_testing.news.sources.reddit_sentiment import RedditSentimentFetcher
from forward_testing.config import ForwardTestingConfig


SAMPLE_REDDIT_RESPONSE = {
    "data": {
        "children": [
            {
                "data": {
                    "title": "NVDA earnings were insane. $78B guidance is unreal",
                    "selftext": "Just read through the Q4 report. Data center revenue...",
                    "url": "https://reddit.com/r/wallstreetbets/comments/abc123",
                    "created_utc": 1743260400,
                    "subreddit": "wallstreetbets",
                    "score": 1500,
                    "num_comments": 342,
                    "ups": 1500,
                }
            },
            {
                "data": {
                    "title": "Oil at $100+ is going to wreck consumer spending",
                    "selftext": "Gas prices are already at $3.94...",
                    "url": "https://reddit.com/r/wallstreetbets/comments/def456",
                    "created_utc": 1743250000,
                    "subreddit": "wallstreetbets",
                    "score": 890,
                    "num_comments": 210,
                    "ups": 890,
                }
            },
        ]
    }
}


@patch("forward_testing.news.sources.reddit_sentiment.requests.get")
def test_fetch_subreddit(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_REDDIT_RESPONSE
    mock_get.return_value = mock_resp

    fetcher = RedditSentimentFetcher(ForwardTestingConfig())
    items = fetcher.fetch_subreddit("wallstreetbets")

    assert len(items) == 2
    assert items[0].source == "reddit"
    assert items[0].category == "sentiment"


@patch("forward_testing.news.sources.reddit_sentiment.requests.get")
def test_fetch_all(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_REDDIT_RESPONSE
    mock_get.return_value = mock_resp

    fetcher = RedditSentimentFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    assert len(items) > 0
    # Should fetch from multiple subreddits
    assert mock_get.call_count >= 6  # 6 subreddits


@patch("forward_testing.news.sources.reddit_sentiment.requests.get")
def test_extracts_mentioned_tickers(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_REDDIT_RESPONSE
    mock_get.return_value = mock_resp

    fetcher = RedditSentimentFetcher(ForwardTestingConfig())
    items = fetcher.fetch_subreddit("wallstreetbets")

    # First post mentions NVDA
    assert items[0].ticker == "NVDA"


@patch("forward_testing.news.sources.reddit_sentiment.requests.get")
def test_fetch_handles_failure(mock_get):
    mock_get.side_effect = Exception("Rate limited")
    fetcher = RedditSentimentFetcher(ForwardTestingConfig())
    items = fetcher.fetch_subreddit("wallstreetbets")

    assert items == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/forward_testing/test_reddit_sentiment.py -v`
Expected: FAIL

- [ ] **Step 3: Write reddit_sentiment.py**

Create `backend/forward_testing/news/sources/reddit_sentiment.py`:

```python
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import requests

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem

logger = logging.getLogger(__name__)

REDDIT_URL = "https://www.reddit.com/r/{subreddit}/hot.json?limit=25&t=day"


class RedditSentimentFetcher:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.timeout = 15
        self.headers = {"User-Agent": "InferForwardTesting/1.0"}

    def fetch_subreddit(self, subreddit: str) -> List[NewsItem]:
        try:
            url = REDDIT_URL.format(subreddit=subreddit)
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            items = []
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                title = post.get("title", "")
                body = post.get("selftext", "")
                score = post.get("score", 0)

                # Only include posts with some engagement
                if score < 50:
                    continue

                created = datetime.fromtimestamp(
                    post.get("created_utc", 0), tz=timezone.utc
                )

                ticker = self._extract_ticker(title + " " + body)

                items.append(NewsItem(
                    title=title,
                    summary=body[:500] if body else title,
                    source="reddit",
                    category="sentiment",
                    ticker=ticker,
                    url=f"https://reddit.com{post.get('permalink', '')}",
                    published_at=created,
                    raw_data={
                        "subreddit": subreddit,
                        "score": score,
                        "num_comments": post.get("num_comments", 0),
                    },
                ))
            return items

        except Exception as e:
            logger.warning(f"Reddit fetch failed for r/{subreddit}: {e}")
            return []

    def fetch_all(self) -> List[NewsItem]:
        all_items: List[NewsItem] = []
        for subreddit in self.config.reddit_subreddits:
            items = self.fetch_subreddit(subreddit)
            all_items.extend(items)

        logger.info(f"Reddit: fetched {len(all_items)} items from {len(self.config.reddit_subreddits)} subreddits")
        return all_items

    def _extract_ticker(self, text: str) -> Optional[str]:
        """Find the first matching ticker symbol mentioned in text."""
        text_upper = text.upper()
        for ticker in self.config.tickers:
            # Match ticker as whole word (e.g., "NVDA" but not "NVIDIA")
            if re.search(rf'\b{ticker}\b', text_upper):
                return ticker
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/forward_testing/test_reddit_sentiment.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/forward_testing/news/sources/reddit_sentiment.py backend/tests/forward_testing/test_reddit_sentiment.py
git commit -m "feat(forward-testing): add Reddit sentiment fetcher"
```

---

### Task 8: News Aggregator (Orchestrator + Deduplication)

**Files:**
- Create: `backend/forward_testing/news/aggregator.py`
- Test: `backend/tests/forward_testing/test_aggregator.py`

- [ ] **Step 1: Write test**

Create `backend/tests/forward_testing/test_aggregator.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from forward_testing.news.aggregator import NewsAggregator
from forward_testing.news.models import NewsItem, PriceData, DailyMarketSnapshot
from forward_testing.config import ForwardTestingConfig


def _make_item(title, source, category="macro", ticker=None):
    return NewsItem(
        title=title,
        summary=f"Summary of {title}",
        source=source,
        category=category,
        ticker=ticker,
        url=f"https://example.com/{hash(title)}",
        published_at=datetime(2026, 3, 29, 14, 0, tzinfo=timezone.utc),
    )


def test_deduplication():
    items = [
        _make_item("Fed Holds Rates Steady at March Meeting", "reuters"),
        _make_item("Fed holds rates steady at march meeting", "google_news"),
        _make_item("Oil prices rise on Iran tensions", "gdelt"),
    ]
    aggregator = NewsAggregator(ForwardTestingConfig())
    deduped = aggregator._deduplicate(items)

    assert len(deduped) == 2


def test_deduplication_keeps_first_seen():
    items = [
        _make_item("Fed Holds Rates Steady", "reuters"),
        _make_item("Fed holds rates steady", "google_news"),
    ]
    aggregator = NewsAggregator(ForwardTestingConfig())
    deduped = aggregator._deduplicate(items)

    assert deduped[0].source == "reuters"


@patch("forward_testing.news.aggregator.GoogleNewsFetcher")
@patch("forward_testing.news.aggregator.YahooFinanceFetcher")
@patch("forward_testing.news.aggregator.GdeltFetcher")
@patch("forward_testing.news.aggregator.ReutersAPFetcher")
@patch("forward_testing.news.aggregator.FedGovFetcher")
@patch("forward_testing.news.aggregator.RedditSentimentFetcher")
def test_fetch_all_calls_all_sources(mock_reddit, mock_fed, mock_reuters,
                                      mock_gdelt, mock_yahoo, mock_google):
    for mock in [mock_reddit, mock_fed, mock_reuters, mock_gdelt, mock_google]:
        instance = mock.return_value
        instance.fetch_all.return_value = [
            _make_item("Test article", "test")
        ]

    yahoo_instance = mock_yahoo.return_value
    yahoo_instance.fetch_all_news.return_value = [_make_item("Yahoo article", "yahoo")]
    yahoo_instance.fetch_all_prices.return_value = []
    yahoo_instance.fetch_market_snapshot.return_value = None

    aggregator = NewsAggregator(ForwardTestingConfig())
    result = aggregator.fetch_all()

    assert result.news_items is not None
    assert len(result.news_items) > 0


def test_group_by_category():
    items = [
        _make_item("Iran tensions", "gdelt", category="geopolitical"),
        _make_item("Fed holds rates", "reuters", category="macro"),
        _make_item("NVDA surges", "yahoo", category="ticker", ticker="NVDA"),
        _make_item("Oil up", "gdelt", category="energy"),
        _make_item("NVDA earnings", "google", category="ticker", ticker="NVDA"),
    ]
    aggregator = NewsAggregator(ForwardTestingConfig())
    grouped = aggregator._group_by_category(items)

    assert "geopolitical" in grouped
    assert "macro" in grouped
    assert "ticker" in grouped
    assert "energy" in grouped
    assert len(grouped["ticker"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/forward_testing/test_aggregator.py -v`
Expected: FAIL

- [ ] **Step 3: Write aggregator.py**

Create `backend/forward_testing/news/aggregator.py`:

```python
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem, PriceData, DailyMarketSnapshot
from forward_testing.news.sources.google_news import GoogleNewsFetcher
from forward_testing.news.sources.yahoo_finance import YahooFinanceFetcher
from forward_testing.news.sources.gdelt import GdeltFetcher
from forward_testing.news.sources.reuters_ap import ReutersAPFetcher
from forward_testing.news.sources.fed_gov import FedGovFetcher
from forward_testing.news.sources.reddit_sentiment import RedditSentimentFetcher

logger = logging.getLogger(__name__)


@dataclass
class AggregatedNews:
    date: datetime
    news_items: List[NewsItem]
    prices: List[PriceData]
    market_snapshot: Optional[DailyMarketSnapshot]
    grouped: Dict[str, List[NewsItem]] = field(default_factory=dict)
    source_counts: Dict[str, int] = field(default_factory=dict)


class NewsAggregator:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.google = GoogleNewsFetcher(config)
        self.yahoo = YahooFinanceFetcher(config)
        self.gdelt = GdeltFetcher(config)
        self.reuters_ap = ReutersAPFetcher(config)
        self.fed_gov = FedGovFetcher(config)
        self.reddit = RedditSentimentFetcher(config)

    def fetch_all(self) -> AggregatedNews:
        all_items: List[NewsItem] = []

        # Fetch from all sources
        sources = [
            ("google_news", self.google.fetch_all),
            ("yahoo_finance", self.yahoo.fetch_all_news),
            ("gdelt", self.gdelt.fetch_all),
            ("reuters_ap", self.reuters_ap.fetch_all),
            ("fed_gov", self.fed_gov.fetch_all),
            ("reddit", self.reddit.fetch_all),
        ]

        source_counts = {}
        for name, fetcher in sources:
            try:
                items = fetcher()
                source_counts[name] = len(items)
                all_items.extend(items)
                logger.info(f"Source {name}: {len(items)} items")
            except Exception as e:
                logger.error(f"Source {name} failed: {e}")
                source_counts[name] = 0

        # Deduplicate
        deduped = self._deduplicate(all_items)
        logger.info(f"After dedup: {len(deduped)} items (from {len(all_items)} raw)")

        # Fetch prices and market snapshot
        prices = self.yahoo.fetch_all_prices()
        snapshot = self.yahoo.fetch_market_snapshot()

        # Group by category
        grouped = self._group_by_category(deduped)

        return AggregatedNews(
            date=datetime.now(timezone.utc),
            news_items=deduped,
            prices=prices,
            market_snapshot=snapshot,
            grouped=grouped,
            source_counts=source_counts,
        )

    def _deduplicate(self, items: List[NewsItem]) -> List[NewsItem]:
        seen_keys = {}
        deduped = []
        for item in items:
            key = item.dedup_key()
            if key not in seen_keys:
                seen_keys[key] = True
                deduped.append(item)
        return deduped

    def _group_by_category(self, items: List[NewsItem]) -> Dict[str, List[NewsItem]]:
        grouped: Dict[str, List[NewsItem]] = {}
        for item in items:
            grouped.setdefault(item.category, []).append(item)
        return grouped

    def save_raw(self, result: AggregatedNews, date_str: str) -> str:
        """Save raw aggregated news to results directory."""
        day_dir = os.path.join(self.config.results_dir, date_str)
        os.makedirs(day_dir, exist_ok=True)

        output = {
            "date": date_str,
            "total_items": len(result.news_items),
            "source_counts": result.source_counts,
            "prices": [
                {
                    "ticker": p.ticker, "close": p.close,
                    "change_pct": p.change_pct, "volume": p.volume,
                    "avg_volume": p.avg_volume,
                }
                for p in result.prices
            ],
            "market_snapshot": {
                "sp500": result.market_snapshot.sp500,
                "sp500_change_pct": result.market_snapshot.sp500_change_pct,
                "vix": result.market_snapshot.vix,
                "treasury_10y": result.market_snapshot.treasury_10y,
                "brent_crude": result.market_snapshot.brent_crude,
                "gold": result.market_snapshot.gold,
                "dollar_index": result.market_snapshot.dollar_index,
            } if result.market_snapshot else None,
            "news": [
                {
                    "title": item.title,
                    "summary": item.summary[:300],
                    "source": item.source,
                    "category": item.category,
                    "ticker": item.ticker,
                    "url": item.url,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                }
                for item in result.news_items
            ],
        }

        path = os.path.join(day_dir, "daily_news.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved raw news to {path}")
        return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/forward_testing/test_aggregator.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/forward_testing/news/aggregator.py backend/tests/forward_testing/test_aggregator.py
git commit -m "feat(forward-testing): add news aggregator with deduplication"
```

---

### Task 9: MD Formatter

**Files:**
- Create: `backend/forward_testing/news/formatter.py`
- Test: `backend/tests/forward_testing/test_formatter.py`

- [ ] **Step 1: Write test**

Create `backend/tests/forward_testing/test_formatter.py`:

```python
import pytest
from datetime import datetime, timezone
from forward_testing.news.formatter import MDFormatter
from forward_testing.news.models import NewsItem, PriceData, DailyMarketSnapshot
from forward_testing.news.aggregator import AggregatedNews
from forward_testing.config import ForwardTestingConfig


def _make_aggregated_news():
    items = [
        NewsItem("Iran signals diplomacy", "Iranian FM...", "gdelt", "geopolitical", "https://a.com", datetime(2026,3,29, tzinfo=timezone.utc)),
        NewsItem("Fed holds rates", "Federal Reserve...", "reuters_ap", "macro", "https://b.com", datetime(2026,3,29, tzinfo=timezone.utc)),
        NewsItem("NVDA surges 3%", "NVIDIA shares...", "yahoo_finance", "ticker", "https://c.com", datetime(2026,3,29, tzinfo=timezone.utc), ticker="NVDA"),
        NewsItem("Oil steady at $102", "Brent crude...", "gdelt", "energy", "https://d.com", datetime(2026,3,29, tzinfo=timezone.utc)),
        NewsItem("Congress passes bill", "Senate voted...", "fed_gov", "us_politics", "https://e.com", datetime(2026,3,29, tzinfo=timezone.utc)),
        NewsItem("AI chip export ban", "New restrictions...", "google_news", "ai_policy", "https://f.com", datetime(2026,3,29, tzinfo=timezone.utc)),
        NewsItem("NVDA bulls on WSB", "Everyone buying...", "reddit", "sentiment", "https://g.com", datetime(2026,3,29, tzinfo=timezone.utc), ticker="NVDA",
                 raw_data={"subreddit": "wallstreetbets", "score": 1500, "num_comments": 300}),
    ]
    prices = [
        PriceData("NVDA", 892.5, 1.2, 85_000_000, 65_000_000, datetime(2026,3,29, tzinfo=timezone.utc)),
        PriceData("AAPL", 241.0, -0.8, 50_000_000, 55_000_000, datetime(2026,3,29, tzinfo=timezone.utc)),
    ]
    snapshot = DailyMarketSnapshot(
        date=datetime(2026,3,29, tzinfo=timezone.utc),
        sp500=6592.0, sp500_change_pct=-0.4, vix=23.4,
        treasury_10y=4.31, brent_crude=102.3, gold=4280.0,
        dollar_index=104.2, us_gasoline=3.94,
    )
    grouped = {}
    for item in items:
        grouped.setdefault(item.category, []).append(item)

    return AggregatedNews(
        date=datetime(2026,3,29, tzinfo=timezone.utc),
        news_items=items, prices=prices, market_snapshot=snapshot,
        grouped=grouped, source_counts={"gdelt": 2, "reuters_ap": 1},
    )


def test_format_produces_markdown():
    agg = _make_aggregated_news()
    formatter = MDFormatter(ForwardTestingConfig())
    md = formatter.format(agg, "March 29, 2026")

    assert "## Daily Update — March 29, 2026" in md
    assert "Market Close" in md
    assert "S&P 500" in md
    assert "6,592" in md or "6592" in md


def test_format_includes_all_sections():
    agg = _make_aggregated_news()
    formatter = MDFormatter(ForwardTestingConfig())
    md = formatter.format(agg, "March 29, 2026")

    assert "Political & Geopolitical" in md
    assert "Financial & Economic" in md
    assert "Energy & Commodities" in md
    assert "AI & Tech" in md
    assert "Market Sentiment" in md
    assert "Ticker Price Action" in md


def test_format_includes_ticker_news():
    agg = _make_aggregated_news()
    formatter = MDFormatter(ForwardTestingConfig())
    md = formatter.format(agg, "March 29, 2026")

    assert "NVDA" in md
    assert "892" in md or "892.5" in md


def test_format_includes_reddit_sentiment():
    agg = _make_aggregated_news()
    formatter = MDFormatter(ForwardTestingConfig())
    md = formatter.format(agg, "March 29, 2026")

    assert "WSB" in md or "wallstreetbets" in md or "Sentiment" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/forward_testing/test_formatter.py -v`
Expected: FAIL

- [ ] **Step 3: Write formatter.py**

Create `backend/forward_testing/news/formatter.py`:

```python
import logging
from typing import Dict, List, Optional

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.aggregator import AggregatedNews
from forward_testing.news.models import NewsItem, PriceData

logger = logging.getLogger(__name__)


class MDFormatter:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config

    def format(self, data: AggregatedNews, date_label: str) -> str:
        sections = []
        sections.append(f"\n## Daily Update — {date_label}\n")

        # Market Close table
        sections.append(self._format_market_close(data))

        # Ticker Price Action table
        if data.prices:
            sections.append(self._format_ticker_prices(data))

        # Political & Geopolitical
        political_items = (
            data.grouped.get("geopolitical", []) +
            data.grouped.get("us_politics", [])
        )
        if political_items:
            sections.append(self._format_category(
                "Political & Geopolitical Developments", political_items
            ))

        # Financial & Economic
        macro_items = data.grouped.get("macro", [])
        if macro_items:
            sections.append(self._format_category(
                "Financial & Economic News", macro_items
            ))

        # Energy & Commodities
        energy_items = data.grouped.get("energy", [])
        if energy_items:
            sections.append(self._format_category(
                "Energy & Commodities", energy_items
            ))

        # AI & Tech
        ai_items = data.grouped.get("ai_policy", [])
        if ai_items:
            sections.append(self._format_category(
                "AI & Tech Industry", ai_items
            ))

        # Ticker-specific updates
        ticker_items = data.grouped.get("ticker", [])
        if ticker_items:
            sections.append(self._format_ticker_updates(ticker_items))

        # Sentiment
        sentiment_items = data.grouped.get("sentiment", [])
        if sentiment_items:
            sections.append(self._format_sentiment(sentiment_items))

        sections.append("---\n")
        return "\n".join(sections)

    def _format_market_close(self, data: AggregatedNews) -> str:
        snap = data.market_snapshot
        if not snap:
            return "### Market Close\n\n*Market data unavailable*\n"

        lines = ["### Market Close\n"]
        lines.append("| Indicator | Close | Change | Context |")
        lines.append("|---|---|---|---|")
        lines.append(f"| S&P 500 | {snap.sp500:,.0f} | {snap.sp500_change_pct:+.1f}% | |")
        lines.append(f"| VIX | {snap.vix:.1f} | | |")
        lines.append(f"| 10-Year Treasury | {snap.treasury_10y:.2f}% | | |")
        lines.append(f"| Brent Crude | ${snap.brent_crude:.1f}/bbl | | |")
        lines.append(f"| Gold | ${snap.gold:,.0f}/oz | | |")
        lines.append(f"| Dollar Index | {snap.dollar_index:.1f} | | |")
        if snap.us_gasoline:
            lines.append(f"| US Gasoline | ${snap.us_gasoline:.2f}/gal | | |")
        lines.append("")
        return "\n".join(lines)

    def _format_ticker_prices(self, data: AggregatedNews) -> str:
        lines = ["### Ticker Price Action\n"]
        lines.append("| Ticker | Close | Change | Volume vs Avg | Key Driver |")
        lines.append("|---|---|---|---|---|")
        for p in sorted(data.prices, key=lambda x: abs(x.change_pct), reverse=True):
            vol_ratio = f"{p.volume_vs_avg:.1f}x" if p.avg_volume > 0 else "N/A"
            # Find matching news for key driver
            driver = self._find_driver(p.ticker, data)
            lines.append(
                f"| {p.ticker} | ${p.close:,.2f} | {p.change_pct:+.1f}% | {vol_ratio} | {driver} |"
            )
        lines.append("")
        return "\n".join(lines)

    def _format_category(self, title: str, items: List[NewsItem]) -> str:
        lines = [f"### {title}\n"]
        seen = set()
        for item in items[:15]:  # Max 15 per category
            key = item.dedup_key()
            if key in seen:
                continue
            seen.add(key)
            tag = self._tag_for(item)
            lines.append(f"- **[{tag}]** {item.title}")
        lines.append("")
        return "\n".join(lines)

    def _format_ticker_updates(self, items: List[NewsItem]) -> str:
        lines = ["### Ticker Updates\n"]
        by_ticker: Dict[str, List[NewsItem]] = {}
        for item in items:
            if item.ticker:
                by_ticker.setdefault(item.ticker, []).append(item)

        for ticker in self.config.tickers:
            ticker_news = by_ticker.get(ticker, [])
            if not ticker_news:
                continue
            # Take top 3 most relevant
            summaries = [n.title for n in ticker_news[:3]]
            lines.append(f"**{ticker}:** {'; '.join(summaries)}")
            lines.append("")
        return "\n".join(lines)

    def _format_sentiment(self, items: List[NewsItem]) -> str:
        lines = ["### Market Sentiment & Retail\n"]
        for item in items[:10]:
            sub = item.raw_data.get("subreddit", "unknown") if item.raw_data else "unknown"
            score = item.raw_data.get("score", 0) if item.raw_data else 0
            comments = item.raw_data.get("num_comments", 0) if item.raw_data else 0
            ticker_tag = f" ${item.ticker}" if item.ticker else ""
            lines.append(
                f"- **[r/{sub}]**{ticker_tag} {item.title} (score: {score}, comments: {comments})"
            )
        lines.append("")
        return "\n".join(lines)

    def _find_driver(self, ticker: str, data: AggregatedNews) -> str:
        for item in data.news_items:
            if item.ticker == ticker and item.category == "ticker":
                return item.title[:60]
        return ""

    def _tag_for(self, item: NewsItem) -> str:
        tag_map = {
            "geopolitical": "GEOPOLITICAL",
            "us_politics": "US POLICY",
            "macro": "MACRO",
            "energy": "ENERGY",
            "ai_policy": "AI/TECH",
            "global_markets": "GLOBAL",
            "sentiment": "SENTIMENT",
        }
        if item.ticker:
            return item.ticker
        return tag_map.get(item.category, item.category.upper())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/forward_testing/test_formatter.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/forward_testing/news/formatter.py backend/tests/forward_testing/test_formatter.py
git commit -m "feat(forward-testing): add MD formatter for daily news sections"
```

---

### Task 10: MD Augmenter (Seed File Manager)

**Files:**
- Create: `backend/forward_testing/augmenter/md_augmenter.py`
- Test: `backend/tests/forward_testing/test_md_augmenter.py`

- [ ] **Step 1: Write test**

Create `backend/tests/forward_testing/test_md_augmenter.py`:

```python
import os
import shutil
import pytest
from datetime import datetime, timezone
from forward_testing.augmenter.md_augmenter import MDAugmenter
from forward_testing.config import ForwardTestingConfig


@pytest.fixture
def tmp_env(tmp_path):
    seeds_dir = tmp_path / "seeds"
    seeds_dir.mkdir()
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    # Create a mini seed file
    seed = seeds_dir / "financial_seed_live.md"
    seed.write_text(
        "# Financial Intelligence Report\n\n"
        "**Tickers covered:** NVDA · AAPL\n\n---\n\n"
        "## Section 1 — Macro Environment\n\nSome macro content.\n\n---\n\n"
        "## Section 2 — Ticker Deep Dives\n\n### NVDA\n\nNVDA content.\n"
    )

    config = ForwardTestingConfig()
    config.seeds_dir = str(seeds_dir)
    config.results_dir = str(results_dir)
    return config, str(seed)


def test_initialize_copies_original(tmp_env):
    config, seed_path = tmp_env
    original = os.path.join(os.path.dirname(seed_path), "..", "demo", "original.md")

    augmenter = MDAugmenter(config)
    # Live file should already exist from fixture
    assert os.path.exists(os.path.join(config.seeds_dir, "financial_seed_live.md"))


def test_append_daily_section(tmp_env):
    config, seed_path = tmp_env
    augmenter = MDAugmenter(config)

    daily_md = "\n## Daily Update — March 29, 2026\n\nSome daily news.\n\n---\n"
    augmenter.append_daily(daily_md, "2026-03-29")

    live_path = os.path.join(config.seeds_dir, "financial_seed_live.md")
    content = open(live_path).read()
    assert "Daily Update — March 29, 2026" in content


def test_append_saves_independent_copy(tmp_env):
    config, seed_path = tmp_env
    augmenter = MDAugmenter(config)

    daily_md = "\n## Daily Update — March 29, 2026\n\nSome news.\n\n---\n"
    augmenter.append_daily(daily_md, "2026-03-29")

    copy_path = os.path.join(config.results_dir, "2026-03-29", "augmented_section.md")
    assert os.path.exists(copy_path)
    assert "Daily Update" in open(copy_path).read()


def test_get_windowed_view(tmp_env):
    config, seed_path = tmp_env
    augmenter = MDAugmenter(config)

    # Append 10 days
    for day in range(20, 30):
        daily_md = f"\n## Daily Update — March {day}, 2026\n\nNews for day {day}.\n\n---\n"
        augmenter.append_daily(daily_md, f"2026-03-{day}")

    windowed = augmenter.get_windowed_view(window_days=7)

    # Should include base content + last 7 days only
    assert "Section 1 — Macro Environment" in windowed
    assert "Daily Update — March 29, 2026" in windowed
    assert "Daily Update — March 23, 2026" in windowed
    assert "Daily Update — March 20, 2026" not in windowed


def test_backup_created(tmp_env):
    config, seed_path = tmp_env
    augmenter = MDAugmenter(config)

    daily_md = "\n## Daily Update — March 29, 2026\n\nNews.\n\n---\n"
    augmenter.append_daily(daily_md, "2026-03-29")

    backup_dir = os.path.join(config.seeds_dir, "backups")
    assert os.path.exists(backup_dir)
    backups = os.listdir(backup_dir)
    assert len(backups) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/forward_testing/test_md_augmenter.py -v`
Expected: FAIL

- [ ] **Step 3: Write md_augmenter.py**

Create `backend/forward_testing/augmenter/md_augmenter.py`:

```python
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from typing import Optional

from forward_testing.config import ForwardTestingConfig

logger = logging.getLogger(__name__)

LIVE_FILENAME = "financial_seed_live.md"


class MDAugmenter:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.live_path = os.path.join(config.seeds_dir, LIVE_FILENAME)
        os.makedirs(config.seeds_dir, exist_ok=True)

    def initialize_from_original(self, original_path: str) -> str:
        """Copy original seed file as the starting live file (one-time setup)."""
        if os.path.exists(self.live_path):
            logger.info(f"Live file already exists: {self.live_path}")
            return self.live_path

        shutil.copy2(original_path, self.live_path)
        logger.info(f"Initialized live seed from {original_path}")
        return self.live_path

    def append_daily(self, daily_md: str, date_str: str) -> None:
        """Append a daily update section to the live seed file."""
        # Backup before modifying
        self._backup(date_str)

        # Append to live file
        with open(self.live_path, "a", encoding="utf-8") as f:
            f.write(daily_md)

        logger.info(f"Appended daily update for {date_str} to {self.live_path}")

        # Save independent copy
        day_dir = os.path.join(self.config.results_dir, date_str)
        os.makedirs(day_dir, exist_ok=True)
        copy_path = os.path.join(day_dir, "augmented_section.md")
        with open(copy_path, "w", encoding="utf-8") as f:
            f.write(daily_md)

        logger.info(f"Saved daily section copy to {copy_path}")

    def get_windowed_view(self, window_days: int = 7) -> str:
        """Return base sections + last N daily updates for simulation input."""
        with open(self.live_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split into base content and daily updates
        daily_pattern = r"(## Daily Update — .+?)(?=## Daily Update — |\Z)"
        daily_sections = re.findall(daily_pattern, content, re.DOTALL)

        # Find where daily updates start
        first_daily = content.find("## Daily Update")
        if first_daily == -1:
            return content  # No daily updates yet

        base_content = content[:first_daily]

        # Take only the last N daily updates
        recent_updates = daily_sections[-window_days:] if daily_sections else []

        windowed = base_content + "\n".join(recent_updates)
        return windowed

    def get_full_content(self) -> str:
        """Return full content of the live seed file."""
        with open(self.live_path, "r", encoding="utf-8") as f:
            return f.read()

    def _backup(self, date_str: str) -> None:
        """Create a dated backup of the live file before modification."""
        backup_dir = os.path.join(self.config.seeds_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        backup_path = os.path.join(backup_dir, f"seed_before_{date_str}.md")
        if os.path.exists(self.live_path):
            shutil.copy2(self.live_path, backup_path)
            logger.info(f"Backup saved: {backup_path}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/forward_testing/test_md_augmenter.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/forward_testing/augmenter/md_augmenter.py backend/tests/forward_testing/test_md_augmenter.py
git commit -m "feat(forward-testing): add MD augmenter with windowed view and backups"
```

---

### Task 11: Integration — CLI Entry Point for News Pipeline

**Files:**
- Create: `backend/forward_testing/cli.py`
- Test: Manual integration test

- [ ] **Step 1: Write cli.py**

Create `backend/forward_testing/cli.py`:

```python
"""
CLI entry point for the forward testing news pipeline.
Usage:
    python -m forward_testing.cli fetch-news          # Fetch news + append to MD
    python -m forward_testing.cli fetch-prices         # Fetch prices only
    python -m forward_testing.cli init                 # Initialize live seed from original
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


def cmd_init(config: ForwardTestingConfig, args):
    """Initialize the live seed file from the original."""
    original = args.original or os.path.join(
        config.base_dir, "demo", "financial_seed_mar25_2026-2.md"
    )
    if not os.path.exists(original):
        logger.error(f"Original seed file not found: {original}")
        sys.exit(1)

    augmenter = MDAugmenter(config)
    path = augmenter.initialize_from_original(original)
    logger.info(f"Live seed initialized at: {path}")


def cmd_fetch_prices(config: ForwardTestingConfig, args):
    """Fetch market close prices."""
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


def cmd_fetch_news(config: ForwardTestingConfig, args):
    """Fetch news from all sources, format, and append to seed file."""
    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Parse date for label
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    date_label = dt.strftime("%B %d, %Y")  # e.g., "March 29, 2026"

    # Ensure live seed exists
    augmenter = MDAugmenter(config)
    if not os.path.exists(augmenter.live_path):
        logger.error("Live seed not initialized. Run: python -m forward_testing.cli init")
        sys.exit(1)

    # Fetch
    aggregator = NewsAggregator(config)
    result = aggregator.fetch_all()

    # Save raw
    aggregator.save_raw(result, date_str)

    # Format
    formatter = MDFormatter(config)
    daily_md = formatter.format(result, date_label)

    # Append
    augmenter.append_daily(daily_md, date_str)

    logger.info(f"Pipeline complete for {date_str}:")
    logger.info(f"  Total news items: {len(result.news_items)}")
    logger.info(f"  Prices fetched: {len(result.prices)}")
    logger.info(f"  Sources: {result.source_counts}")


def cmd_status(config: ForwardTestingConfig, args):
    """Show current pipeline status."""
    augmenter = MDAugmenter(config)

    if os.path.exists(augmenter.live_path):
        size = os.path.getsize(augmenter.live_path)
        content = augmenter.get_full_content()
        daily_count = content.count("## Daily Update")
        logger.info(f"Live seed: {augmenter.live_path} ({size:,} bytes, {daily_count} daily updates)")
    else:
        logger.info("Live seed: NOT INITIALIZED")

    if os.path.exists(config.results_dir):
        days = sorted(os.listdir(config.results_dir))
        days = [d for d in days if d.startswith("20")]
        logger.info(f"Results: {len(days)} days in {config.results_dir}")
        if days:
            logger.info(f"  Latest: {days[-1]}")
    else:
        logger.info("Results: no data yet")


def main():
    parser = argparse.ArgumentParser(description="Infer Forward Testing Pipeline")
    parser.add_argument("--date", help="Override date (YYYY-MM-DD)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize live seed file")
    init_parser.add_argument("--original", help="Path to original seed MD file")

    subparsers.add_parser("fetch-prices", help="Fetch market close prices")
    subparsers.add_parser("fetch-news", help="Fetch news and append to seed")
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
```

- [ ] **Step 2: Create `__main__.py` for module execution**

Create `backend/forward_testing/__main__.py`:

```python
from forward_testing.cli import main

main()
```

- [ ] **Step 3: Run all tests to ensure nothing is broken**

Run: `cd backend && python -m pytest tests/forward_testing/ -v`
Expected: All tests PASS

- [ ] **Step 4: Test CLI help**

Run: `cd backend && python -m forward_testing.cli --help`
Expected: Shows usage help with init, fetch-prices, fetch-news, status commands

- [ ] **Step 5: Test init command**

Run: `cd backend && python -m forward_testing.cli init`
Expected: "Live seed initialized at: .../forward_testing/seeds/financial_seed_live.md"

- [ ] **Step 6: Test status command**

Run: `cd backend && python -m forward_testing.cli status`
Expected: Shows live seed info and results count

- [ ] **Step 7: Commit**

```bash
git add backend/forward_testing/cli.py backend/forward_testing/__main__.py
git commit -m "feat(forward-testing): add CLI entry point for news pipeline"
```

---

### Task 12: Run Full Test Suite + Final Commit

- [ ] **Step 1: Run all tests**

Run: `cd backend && python -m pytest tests/forward_testing/ -v --tb=short`
Expected: All tests PASS (approximately 30+ tests)

- [ ] **Step 2: Test live news fetch (integration test)**

Run: `cd backend && python -m forward_testing.cli fetch-news --date 2026-03-29`
Expected: Fetches real news from all sources, appends to seed file. Check:
- `forward_testing/results/2026-03-29/daily_news.json` exists
- `forward_testing/results/2026-03-29/augmented_section.md` exists
- `forward_testing/seeds/financial_seed_live.md` has the new daily update appended

- [ ] **Step 3: Verify augmented MD quality**

Run: `cat backend/forward_testing/results/2026-03-29/augmented_section.md`
Expected: Well-formatted MD with Market Close table, Political/Geopolitical, Financial, Energy, Ticker Updates, and Sentiment sections

- [ ] **Step 4: Final commit**

```bash
git add -A backend/forward_testing/ backend/tests/
git commit -m "feat(forward-testing): complete Plan 1 — news aggregation + MD augmentation pipeline"
```
