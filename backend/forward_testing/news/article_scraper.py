"""Scrapes full article text from news URLs."""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from forward_testing.news.models import NewsItem

logger = logging.getLogger(__name__)


def _scrape_single(item: NewsItem) -> NewsItem:
    """Scrape full article text for a single NewsItem."""
    if not item.url or item.full_text:
        return item

    # Try newspaper4k first
    try:
        from newspaper import Article
        article = Article(item.url)
        article.download()
        article.parse()
        if article.text and len(article.text) > 100:
            item.full_text = article.text
            if item.summary == item.title:
                item.summary = article.text[:500]
            return item
    except Exception:
        pass

    # Fallback: requests + BeautifulSoup
    try:
        import requests
        from bs4 import BeautifulSoup
        resp = requests.get(item.url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # Remove scripts, styles, nav, footer
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            # Try article tag first, then main, then body
            content = soup.find("article") or soup.find("main") or soup.find("body")
            if content:
                text = content.get_text(separator="\n", strip=True)
                # Clean up excessive whitespace
                lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 20]
                text = "\n\n".join(lines)
                if len(text) > 100:
                    item.full_text = text[:5000]
                    if item.summary == item.title:
                        item.summary = text[:500]
    except Exception as e:
        logger.debug(f"Scrape failed for {item.url}: {e}")

    return item


def enrich_with_full_text(items: List[NewsItem], max_workers: int = 10, max_articles: int = 100) -> List[NewsItem]:
    """Scrape full article text for the most important news items.

    Prioritizes items by category importance and limits to max_articles
    to avoid excessive scraping time.

    Args:
        items: List of NewsItem to enrich
        max_workers: Concurrent scraping threads
        max_articles: Max articles to scrape (to control time)
    """
    # Priority order for scraping
    priority = {
        "geopolitical": 0,
        "us_politics": 1,
        "macro": 2,
        "energy": 3,
        "ticker": 4,
        "ai_policy": 5,
        "global_markets": 6,
        "sentiment": 7,
    }

    # Sort by priority, take top N
    sorted_items = sorted(items, key=lambda x: priority.get(x.category, 99))
    to_scrape = sorted_items[:max_articles]
    rest = sorted_items[max_articles:]

    scraped_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_scrape_single, item): item for item in to_scrape}
        results = []
        for future in as_completed(futures):
            item = future.result()
            if item.full_text:
                scraped_count += 1
            results.append(item)

    logger.info(f"Article scraper: {scraped_count}/{len(to_scrape)} articles scraped successfully")
    return results + rest
