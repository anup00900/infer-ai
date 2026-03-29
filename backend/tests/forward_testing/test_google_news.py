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

    assert mock_get.call_count > 11
    assert len(items) > 0


@patch("forward_testing.news.sources.google_news.requests.get")
def test_fetch_handles_failure_gracefully(mock_get):
    mock_get.side_effect = Exception("Network error")

    fetcher = GoogleNewsFetcher(ForwardTestingConfig())
    items = fetcher.fetch_ticker("NVDA")

    assert items == []
