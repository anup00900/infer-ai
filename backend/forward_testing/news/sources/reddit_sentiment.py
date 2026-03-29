import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import requests

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.models import NewsItem

logger = logging.getLogger(__name__)

REDDIT_HOT_URL = "https://www.reddit.com/r/{subreddit}/hot.json?limit=25&t=day"
MIN_SCORE = 50


class RedditSentimentFetcher:
    def __init__(self, config: ForwardTestingConfig):
        self.config = config
        self.headers = {
            "User-Agent": "InferForwardTesting/1.0 (research bot)"
        }
        self.timeout = 15

    def fetch_subreddit(self, subreddit: str) -> List[NewsItem]:
        try:
            url = REDDIT_HOT_URL.format(subreddit=subreddit)
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            children = data.get("data", {}).get("children", [])
            items = []
            for child in children:
                post = child.get("data", {})
                score = post.get("score", 0)
                if score < MIN_SCORE:
                    continue
                title = post.get("title", "")
                body = post.get("selftext", "")
                url_post = post.get("url", "")
                created_utc = post.get("created_utc")
                num_comments = post.get("num_comments", 0)
                post_subreddit = post.get("subreddit", subreddit)

                published_at = (
                    datetime.fromtimestamp(created_utc, tz=timezone.utc)
                    if created_utc
                    else datetime.now(timezone.utc)
                )

                ticker = self._extract_ticker(title + " " + body)

                items.append(NewsItem(
                    title=title,
                    summary=body[:500] if body else title,
                    source="reddit",
                    category="sentiment",
                    url=url_post,
                    published_at=published_at,
                    ticker=ticker,
                    raw_data={
                        "subreddit": post_subreddit,
                        "score": score,
                        "num_comments": num_comments,
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
        logger.info(f"Reddit: fetched {len(all_items)} total items")
        return all_items

    def _extract_ticker(self, text: str) -> Optional[str]:
        upper_text = text.upper()
        for ticker in self.config.tickers:
            pattern = r'\b' + re.escape(ticker) + r'\b'
            if re.search(pattern, upper_text):
                return ticker
        return None
