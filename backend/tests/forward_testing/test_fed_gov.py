import pytest
from unittest.mock import patch, MagicMock
from forward_testing.news.sources.fed_gov import FedGovFetcher
from forward_testing.config import ForwardTestingConfig


SAMPLE_RSS_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>Test article</title><link>https://example.com</link>
<description>Description</description><pubDate>Sat, 29 Mar 2026 15:00:00 GMT</pubDate></item>
</channel></rss>"""


def _make_mock_resp(content=SAMPLE_RSS_RESPONSE, status_code=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.content = content.encode()
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@patch("forward_testing.news.sources.fed_gov.requests.get")
def test_fetch_all_returns_items_with_correct_source(mock_get):
    mock_get.return_value = _make_mock_resp()

    fetcher = FedGovFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    assert len(items) > 0
    for item in items:
        assert item.source == "fed_gov"


@patch("forward_testing.news.sources.fed_gov.requests.get")
def test_fetch_all_items_have_macro_category(mock_get):
    mock_get.return_value = _make_mock_resp()

    fetcher = FedGovFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    assert len(items) > 0
    for item in items:
        assert item.category == "macro"


@patch("forward_testing.news.sources.fed_gov.requests.get")
def test_fetch_all_only_processes_fed_feeds(mock_get):
    mock_get.return_value = _make_mock_resp()

    config = ForwardTestingConfig()
    fetcher = FedGovFetcher(config)
    fetcher.fetch_all()

    fed_feeds = [name for name in config.rss_feeds if name.startswith("fed")]
    assert mock_get.call_count == len(fed_feeds)


@patch("forward_testing.news.sources.fed_gov.requests.get")
def test_fetch_all_skips_non_fed_feeds(mock_get):
    mock_get.return_value = _make_mock_resp()

    config = ForwardTestingConfig()
    fetcher = FedGovFetcher(config)
    fetcher.fetch_all()

    called_urls = [call.args[0] for call in mock_get.call_args_list]
    for url in called_urls:
        assert "federalreserve" in url


@patch("forward_testing.news.sources.fed_gov.requests.get")
def test_fetch_feed_returns_up_to_20_items(mock_get):
    items_xml = "\n".join(
        f"<item><title>Fed Article {i}</title><link>https://federalreserve.gov/{i}</link>"
        f"<description>Desc {i}</description>"
        f"<pubDate>Sat, 29 Mar 2026 15:00:00 GMT</pubDate></item>"
        for i in range(25)
    )
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Federal Reserve</title>{items_xml}</channel></rss>"""

    mock_get.return_value = _make_mock_resp(content=rss)

    fetcher = FedGovFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://federalreserve.gov/feeds/press_all.xml", "fed_press")

    assert len(items) == 25  # No limit — all items included


@patch("forward_testing.news.sources.fed_gov.requests.get")
def test_fetch_failure_returns_empty_list(mock_get):
    mock_get.side_effect = Exception("Network error")

    fetcher = FedGovFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    assert items == []


@patch("forward_testing.news.sources.fed_gov.requests.get")
def test_fetch_feed_http_error_returns_empty_list(mock_get):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("503 Service Unavailable")
    mock_get.return_value = mock_resp

    fetcher = FedGovFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://federalreserve.gov/feeds/press_all.xml", "fed_press")

    assert items == []


@patch("forward_testing.news.sources.fed_gov.requests.get")
def test_news_item_fields_populated(mock_get):
    mock_get.return_value = _make_mock_resp()

    fetcher = FedGovFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://federalreserve.gov/feeds/press_all.xml", "fed_press")

    assert len(items) == 1
    item = items[0]
    assert item.title == "Test article"
    assert item.url == "https://example.com"
    assert item.source == "fed_gov"
    assert item.category == "macro"
    assert item.published_at is not None


@patch("forward_testing.news.sources.fed_gov.requests.get")
def test_fetch_all_returns_items_from_all_fed_feeds(mock_get):
    mock_get.return_value = _make_mock_resp()

    config = ForwardTestingConfig()
    fed_feed_count = sum(1 for name in config.rss_feeds if name.startswith("fed"))
    fetcher = FedGovFetcher(config)
    items = fetcher.fetch_all()

    # Each fed feed returns 1 item from sample RSS
    assert len(items) == fed_feed_count


@patch("forward_testing.news.sources.fed_gov.requests.get")
def test_fetch_feed_no_entries_returns_empty(mock_get):
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Empty Feed</title></channel></rss>"""
    mock_get.return_value = _make_mock_resp(content=rss)

    fetcher = FedGovFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://federalreserve.gov/feeds/speeches.xml", "fed_speeches")

    assert items == []
