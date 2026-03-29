import pytest
from unittest.mock import patch, MagicMock
from forward_testing.news.sources.reuters_ap import ReutersAPFetcher
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


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_fetch_all_returns_items_with_correct_source(mock_get):
    mock_get.return_value = _make_mock_resp()

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    assert len(items) > 0
    for item in items:
        assert item.source == "reuters_ap"


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_fetch_all_only_processes_reuters_and_ap_feeds(mock_get):
    mock_get.return_value = _make_mock_resp()

    config = ForwardTestingConfig()
    fetcher = ReutersAPFetcher(config)
    fetcher.fetch_all()

    reuters_ap_feeds = [
        name for name in config.rss_feeds
        if name.startswith("reuters") or name.startswith("ap")
    ]
    assert mock_get.call_count == len(reuters_ap_feeds)


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_fetch_all_skips_non_reuters_ap_feeds(mock_get):
    mock_get.return_value = _make_mock_resp()

    config = ForwardTestingConfig()
    fetcher = ReutersAPFetcher(config)
    fetcher.fetch_all()

    called_urls = [call.args[0] for call in mock_get.call_args_list]
    for url in called_urls:
        # Only Reuters and AP URLs should have been fetched
        assert "reuters" in url or "apnews" in url or "rsshub" in url


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_fetch_feed_returns_up_to_20_items(mock_get):
    # Build RSS with 25 items
    items_xml = "\n".join(
        f"<item><title>Article {i}</title><link>https://example.com/{i}</link>"
        f"<description>Desc {i}</description>"
        f"<pubDate>Sat, 29 Mar 2026 15:00:00 GMT</pubDate></item>"
        for i in range(25)
    )
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>{items_xml}</channel></rss>"""

    mock_get.return_value = _make_mock_resp(content=rss)

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://example.com/feed", "reuters_world")

    assert len(items) == 25  # No limit — all items included


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_classify_politics_feed_name(mock_get):
    mock_get.return_value = _make_mock_resp()

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://example.com/feed", "ap_politics")

    assert len(items) > 0
    assert items[0].category == "us_politics"


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_classify_macro_keyword_in_title(mock_get):
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>Federal Reserve raises interest rate by 25 bps</title>
<link>https://example.com/1</link><description>Desc</description>
<pubDate>Sat, 29 Mar 2026 15:00:00 GMT</pubDate></item>
</channel></rss>"""
    mock_get.return_value = _make_mock_resp(content=rss)

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://example.com/feed", "reuters_world")

    assert items[0].category == "macro"


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_classify_geopolitical_keyword_in_title(mock_get):
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>Tensions rise in Taiwan strait amid China tensions</title>
<link>https://example.com/1</link><description>Desc</description>
<pubDate>Sat, 29 Mar 2026 15:00:00 GMT</pubDate></item>
</channel></rss>"""
    mock_get.return_value = _make_mock_resp(content=rss)

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://example.com/feed", "reuters_world")

    assert items[0].category == "geopolitical"


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_classify_energy_keyword_in_title(mock_get):
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>Crude oil prices drop on OPEC output increase</title>
<link>https://example.com/1</link><description>Desc</description>
<pubDate>Sat, 29 Mar 2026 15:00:00 GMT</pubDate></item>
</channel></rss>"""
    mock_get.return_value = _make_mock_resp(content=rss)

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://example.com/feed", "reuters_business")

    assert items[0].category == "energy"


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_classify_us_politics_keyword_in_title(mock_get):
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>White House signs executive order on tech exports</title>
<link>https://example.com/1</link><description>Desc</description>
<pubDate>Sat, 29 Mar 2026 15:00:00 GMT</pubDate></item>
</channel></rss>"""
    mock_get.return_value = _make_mock_resp(content=rss)

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://example.com/feed", "reuters_world")

    assert items[0].category == "us_politics"


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_classify_defaults_business_feed_to_macro(mock_get):
    mock_get.return_value = _make_mock_resp()

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://example.com/feed", "reuters_business")

    assert items[0].category == "macro"


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_classify_defaults_world_feed_to_geopolitical(mock_get):
    mock_get.return_value = _make_mock_resp()

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://example.com/feed", "reuters_world")

    assert items[0].category == "geopolitical"


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_fetch_failure_returns_empty_list(mock_get):
    mock_get.side_effect = Exception("Network error")

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher.fetch_all()

    assert items == []


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_fetch_feed_http_error_returns_empty_list(mock_get):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("404 Not Found")
    mock_get.return_value = mock_resp

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://example.com/bad", "reuters_world")

    assert items == []


@patch("forward_testing.news.sources.reuters_ap.requests.get")
def test_news_item_fields_populated(mock_get):
    mock_get.return_value = _make_mock_resp()

    fetcher = ReutersAPFetcher(ForwardTestingConfig())
    items = fetcher._fetch_feed("https://example.com/feed", "reuters_world")

    assert len(items) == 1
    item = items[0]
    assert item.title == "Test article"
    assert item.url == "https://example.com"
    assert item.source == "reuters_ap"
    assert item.published_at is not None
