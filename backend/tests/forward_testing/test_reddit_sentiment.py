import pytest
from unittest.mock import patch, MagicMock
from forward_testing.news.sources.reddit_sentiment import RedditSentimentFetcher
from forward_testing.config import ForwardTestingConfig


SAMPLE_REDDIT_RESPONSE = {
    "data": {
        "children": [
            {"data": {
                "title": "NVDA earnings were insane. $78B guidance is unreal",
                "selftext": "Just read through the Q4 report...",
                "url": "https://reddit.com/r/wallstreetbets/comments/abc123",
                "created_utc": 1743260400,
                "subreddit": "wallstreetbets",
                "score": 1500, "num_comments": 342, "ups": 1500,
            }},
            {"data": {
                "title": "Oil at $100+ is going to wreck consumer spending",
                "selftext": "Gas prices are already at $3.94...",
                "url": "https://reddit.com/r/wallstreetbets/comments/def456",
                "created_utc": 1743250000,
                "subreddit": "wallstreetbets",
                "score": 890, "num_comments": 210, "ups": 890,
            }},
        ]
    }
}


@patch("forward_testing.news.sources.reddit_sentiment.requests.get")
def test_fetch_subreddit_returns_items(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_REDDIT_RESPONSE
    mock_get.return_value = mock_resp

    fetcher = RedditSentimentFetcher(ForwardTestingConfig())
    items = fetcher.fetch_subreddit("wallstreetbets")

    assert len(items) == 2
    assert all(item.source == "reddit" for item in items)
    assert all(item.category == "sentiment" for item in items)


@patch("forward_testing.news.sources.reddit_sentiment.requests.get")
def test_fetch_all_calls_all_subreddits(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_REDDIT_RESPONSE
    mock_get.return_value = mock_resp

    config = ForwardTestingConfig()
    fetcher = RedditSentimentFetcher(config)
    fetcher.fetch_all()

    assert mock_get.call_count >= len(config.reddit_subreddits)
    assert mock_get.call_count >= 6


@patch("forward_testing.news.sources.reddit_sentiment.requests.get")
def test_first_item_ticker_is_nvda(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_REDDIT_RESPONSE
    mock_get.return_value = mock_resp

    fetcher = RedditSentimentFetcher(ForwardTestingConfig())
    items = fetcher.fetch_subreddit("wallstreetbets")

    assert len(items) > 0
    assert items[0].ticker == "NVDA"


@patch("forward_testing.news.sources.reddit_sentiment.requests.get")
def test_fetch_subreddit_failure_returns_empty_list(mock_get):
    mock_get.side_effect = Exception("Network error")

    fetcher = RedditSentimentFetcher(ForwardTestingConfig())
    items = fetcher.fetch_subreddit("wallstreetbets")

    assert items == []


@patch("forward_testing.news.sources.reddit_sentiment.requests.get")
def test_score_filter_excludes_low_score_posts(mock_get):
    low_score_response = {
        "data": {
            "children": [
                {"data": {
                    "title": "AAPL stock thoughts",
                    "selftext": "Low engagement post",
                    "url": "https://reddit.com/r/stocks/comments/xyz",
                    "created_utc": 1743260400,
                    "subreddit": "stocks",
                    "score": 10, "num_comments": 2, "ups": 10,
                }},
            ]
        }
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = low_score_response
    mock_get.return_value = mock_resp

    fetcher = RedditSentimentFetcher(ForwardTestingConfig())
    items = fetcher.fetch_subreddit("stocks")

    assert items == []


@patch("forward_testing.news.sources.reddit_sentiment.requests.get")
def test_raw_data_contains_expected_fields(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_REDDIT_RESPONSE
    mock_get.return_value = mock_resp

    fetcher = RedditSentimentFetcher(ForwardTestingConfig())
    items = fetcher.fetch_subreddit("wallstreetbets")

    assert len(items) > 0
    raw = items[0].raw_data
    assert "subreddit" in raw
    assert "score" in raw
    assert "num_comments" in raw
    assert raw["score"] == 1500
    assert raw["num_comments"] == 342
