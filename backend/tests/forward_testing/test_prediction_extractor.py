import json
import os
import pytest
from forward_testing.runner.prediction_extractor import extract_predictions, _regex_extraction


SAMPLE_REPORT = """# Simulated Market Futures: S&P 500 Analysis

The simulation suggests the S&P 500 could trade between 6,400 and 6,700 over the next period.

## Key Findings

Oil prices remain elevated at $100-110/bbl. Gold continues its rally.

The bullish camp argues tech earnings will drive markets higher. The bearish camp warns about inflation from oil prices.

Bullish agents: 45%. Bearish agents: 35%. Neutral: 20%.

### NVDA Outlook
NVIDIA remains the consensus top pick with strong AI demand. Price target range $850-950.

### AAPL Outlook
Apple faces headwinds from supply chain issues. Mixed sentiment.
"""


def test_regex_extraction():
    result = _regex_extraction(SAMPLE_REPORT, "t1", "2026-03-29", "2026-03-30", ["NVDA", "AAPL"])
    assert result["date_generated"] == "2026-03-29"
    assert result["horizon"] == "t1"
    assert result["target_date"] == "2026-03-30"
    assert result["extraction_method"] == "regex_fallback"
    assert len(result["market_outlook"]["sp500"]["scenarios"]) >= 2
    assert len(result["ticker_outlook"]) == 2


def test_extract_predictions_saves_file(tmp_path):
    output = str(tmp_path / "prediction.json")
    result = extract_predictions(SAMPLE_REPORT, "t1", "2026-03-29", "2026-03-30", ["NVDA"], output)
    assert os.path.exists(output)
    with open(output) as f:
        saved = json.load(f)
    assert saved["horizon"] == "t1"
    assert saved["date_generated"] == "2026-03-29"


def test_regex_finds_sp500_range():
    result = _regex_extraction(SAMPLE_REPORT, "t1", "2026-03-29", "2026-03-30", ["NVDA"])
    scenarios = result["market_outlook"]["sp500"]["scenarios"]
    all_ranges = [s["range"] for s in scenarios]
    # Should have found 6400 and 6700 from the report
    flat = [v for r in all_ranges for v in r]
    assert any(6300 < v < 6800 for v in flat)


def test_regex_finds_oil():
    result = _regex_extraction(SAMPLE_REPORT, "t1", "2026-03-29", "2026-03-30", ["NVDA"])
    oil = result["macro_outlook"]["oil_brent"]["scenarios"]
    assert len(oil) >= 1


def test_regex_sentiment():
    result = _regex_extraction(SAMPLE_REPORT, "t1", "2026-03-29", "2026-03-30", ["NVDA"])
    bull = result["agent_debate_summary"]["bull_camp"]["percentage"]
    assert 0 < bull < 1
