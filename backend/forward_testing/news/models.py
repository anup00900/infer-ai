import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NewsItem:
    title: str
    summary: str
    source: str
    category: str
    url: str
    published_at: datetime
    ticker: Optional[str] = None
    raw_data: Optional[dict] = None
    full_text: Optional[str] = None  # Full article body when scraped

    def dedup_key(self) -> str:
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
