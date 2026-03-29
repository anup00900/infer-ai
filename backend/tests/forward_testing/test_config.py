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
