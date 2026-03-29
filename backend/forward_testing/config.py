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

    base_dir: str = field(default_factory=lambda: os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    results_dir: str = field(init=False)
    seeds_dir: str = field(init=False)

    def __post_init__(self):
        self.results_dir = os.path.join(self.base_dir, "forward_testing", "results")
        self.seeds_dir = os.path.join(self.base_dir, "forward_testing", "seeds")
