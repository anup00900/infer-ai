import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from forward_testing.news.sources.gdelt import GdeltFetcher
from forward_testing.config import ForwardTestingConfig


SAMPLE_GDELT_RESPONSE = {
    "articles": [
        {
            "title": "Iran closes Strait of Hormuz amid escalating tensions",
            "url": "https://example.com/iran-hormuz",
            "seendate": "20260329T140000Z",
            "domain": "example.com",
            "sourcecountry": "US",
        },
        {
            "title": "OPEC cuts oil production as prices fall",
            "url": "https://example.com/opec-cut",
            "seendate": "20260329T120000Z",
            "domain": "example.com",
            "sourcecountry": "UK",
        },
    ]
}


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_topic_returns_news_items(mock_get):
    """fetch_topic should return NewsItems with source='gdelt' and correct category."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_GDELT_RESPONSE
    mock_get.return_value = mock_resp

    fetcher = GdeltFetcher(ForwardTestingConfig())
    items = fetcher.fetch_topic("Iran Hormuz oil conflict", category="geopolitical")

    assert len(items) == 2
    assert items[0].source == "gdelt"
    assert items[0].category == "geopolitical"
    assert items[0].title == "Iran closes Strait of Hormuz amid escalating tensions"
    assert items[0].url == "https://example.com/iran-hormuz"
    assert isinstance(items[0].published_at, datetime)
    assert items[0].published_at.tzinfo == timezone.utc
    assert items[0].ticker is None


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_topic_correct_api_params(mock_get):
    """fetch_topic should call GDELT API with the correct parameters."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_GDELT_RESPONSE
    mock_get.return_value = mock_resp

    config = ForwardTestingConfig()
    fetcher = GdeltFetcher(config)
    fetcher.fetch_topic("China trade tariffs", category="geopolitical")

    mock_get.assert_called_once()
    call_kwargs = mock_get.call_args
    # First positional arg is the URL
    assert call_kwargs[0][0] == config.gdelt_base_url
    params = call_kwargs[1]["params"]
    assert params["query"] == "China trade tariffs"
    assert params["mode"] == "ArtList"
    assert params["maxrecords"] == 20
    assert params["timespan"] == "1d"
    assert params["format"] == "json"
    assert params["sort"] == "DateDesc"


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_all_calls_multiple_queries(mock_get):
    """fetch_all should issue one request per priority query across all categories."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_GDELT_RESPONSE
    mock_get.return_value = mock_resp

    fetcher = GdeltFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    # 5 geopolitical + 4 us_politics + 3 energy + 3 macro + 3 global_markets = 18 queries
    assert mock_get.call_count == 18
    assert len(items) == 18 * 2  # 2 articles per mocked response


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_topic_empty_response_returns_empty_list(mock_get):
    """fetch_topic should return an empty list when the API returns no articles."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"articles": []}
    mock_get.return_value = mock_resp

    fetcher = GdeltFetcher(ForwardTestingConfig())
    items = fetcher.fetch_topic("some query", category="macro")

    assert items == []


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_topic_missing_articles_key_returns_empty_list(mock_get):
    """fetch_topic should return an empty list when the response has no 'articles' key."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {}
    mock_get.return_value = mock_resp

    fetcher = GdeltFetcher(ForwardTestingConfig())
    items = fetcher.fetch_topic("some query", category="macro")

    assert items == []


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_topic_network_failure_returns_empty_list(mock_get):
    """fetch_topic should return an empty list on network or HTTP errors."""
    mock_get.side_effect = Exception("Network error")

    fetcher = GdeltFetcher(ForwardTestingConfig())
    items = fetcher.fetch_topic("Iran Hormuz oil conflict", category="geopolitical")

    assert items == []


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_topic_http_error_returns_empty_list(mock_get):
    """fetch_topic should return an empty list when the server returns an HTTP error."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("500 Server Error")
    mock_get.return_value = mock_resp

    fetcher = GdeltFetcher(ForwardTestingConfig())
    items = fetcher.fetch_topic("Russia Ukraine", category="geopolitical")

    assert items == []


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_topic_seendate_parsing(mock_get):
    """fetch_topic should correctly parse GDELT seendate format."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "articles": [
            {
                "title": "Test article",
                "url": "https://example.com/test",
                "seendate": "20260329T140000Z",
                "domain": "example.com",
                "sourcecountry": "US",
            }
        ]
    }
    mock_get.return_value = mock_resp

    fetcher = GdeltFetcher(ForwardTestingConfig())
    items = fetcher.fetch_topic("test query", category="macro")

    assert len(items) == 1
    assert items[0].published_at == datetime(2026, 3, 29, 14, 0, 0, tzinfo=timezone.utc)


@patch("forward_testing.news.sources.gdelt.requests.get")
def test_fetch_topic_stores_raw_data(mock_get):
    """fetch_topic should store the original article dict as raw_data."""
    article = {
        "title": "Test article",
        "url": "https://example.com/test",
        "seendate": "20260329T140000Z",
        "domain": "example.com",
        "sourcecountry": "US",
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"articles": [article]}
    mock_get.return_value = mock_resp

    fetcher = GdeltFetcher(ForwardTestingConfig())
    items = fetcher.fetch_topic("test query", category="energy")

    assert items[0].raw_data == article
