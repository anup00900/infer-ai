import json
import os
import pytest
from forward_testing.scorer.scorecard import score_prediction, _score_scenarios, compute_rolling_scorecard


@pytest.fixture
def sample_data(tmp_path):
    prediction = {
        "date_generated": "2026-03-29",
        "horizon": "t1",
        "target_date": "2026-03-30",
        "market_outlook": {
            "sp500": {
                "scenarios": [
                    {"label": "bull", "probability": 0.25, "range": [6600, 6700]},
                    {"label": "base", "probability": 0.50, "range": [6500, 6600]},
                    {"label": "bear", "probability": 0.20, "range": [6400, 6500]},
                    {"label": "tail", "probability": 0.05, "range": [6200, 6400]},
                ]
            }
        },
        "macro_outlook": {
            "oil_brent": {"scenarios": [
                {"label": "stable", "probability": 0.5, "range": [98, 108]},
                {"label": "spike", "probability": 0.3, "range": [108, 125]},
            ]},
            "gold": {"scenarios": [{"label": "hold", "probability": 0.5, "range": [4200, 4400]}]},
        },
        "ticker_outlook": [
            {"ticker": "NVDA", "scenarios": [
                {"label": "outperform", "probability": 0.5, "narrative": "..."},
                {"label": "underperform", "probability": 0.3, "narrative": "..."},
            ]},
            {"ticker": "AAPL", "scenarios": [
                {"label": "outperform", "probability": 0.3, "narrative": "..."},
                {"label": "underperform", "probability": 0.5, "narrative": "..."},
            ]},
        ],
    }
    actuals = {
        "date": "2026-03-30",
        "market": {
            "sp500": {"close": 6550, "change_pct": -0.5},
            "brent_crude": {"close": 103.5, "change_pct": 1.2},
            "gold": {"close": 4280, "change_pct": 0.5},
        },
        "tickers": {
            "NVDA": {"close": 895, "change_pct": 1.5},
            "AAPL": {"close": 238, "change_pct": -1.2},
        },
    }
    pred_path = str(tmp_path / "prediction.json")
    act_path = str(tmp_path / "actuals.json")
    with open(pred_path, "w") as f:
        json.dump(prediction, f)
    with open(act_path, "w") as f:
        json.dump(actuals, f)
    return pred_path, act_path, tmp_path


def test_score_prediction(sample_data):
    pred_path, act_path, tmp_path = sample_data
    out_path = str(tmp_path / "scorecard.json")
    result = score_prediction(pred_path, act_path, out_path)
    assert result["prediction_date"] == "2026-03-29"
    assert result["horizon"] == "t1"
    assert os.path.exists(out_path)


def test_sp500_scenario_hit(sample_data):
    pred_path, act_path, tmp_path = sample_data
    out_path = str(tmp_path / "scorecard.json")
    result = score_prediction(pred_path, act_path, out_path)
    # 6550 falls in base range [6500, 6600]
    assert result["market_score"]["scenario_hit"] == "base"
    assert result["market_score"]["highest_prob_correct"] is True


def test_ticker_direction(sample_data):
    pred_path, act_path, tmp_path = sample_data
    out_path = str(tmp_path / "scorecard.json")
    result = score_prediction(pred_path, act_path, out_path)
    nvda = next(t for t in result["ticker_scores"] if t["ticker"] == "NVDA")
    assert nvda["direction_correct"] is True  # predicted outperform (up), actual +1.5%
    aapl = next(t for t in result["ticker_scores"] if t["ticker"] == "AAPL")
    assert aapl["direction_correct"] is True  # predicted underperform (down), actual -1.2%


def test_score_scenarios():
    scenarios = [
        {"label": "low", "probability": 0.3, "range": [90, 100]},
        {"label": "mid", "probability": 0.5, "range": [100, 110]},
        {"label": "high", "probability": 0.2, "range": [110, 120]},
    ]
    result = _score_scenarios(scenarios, 105, "test")
    assert result["scenario_hit"] == "mid"
    assert result["highest_prob_correct"] is True


def test_rolling_scorecard_empty(tmp_path):
    results_dir = str(tmp_path / "results")
    os.makedirs(results_dir)
    out_path = str(tmp_path / "rolling.json")
    result = compute_rolling_scorecard(results_dir, out_path)
    assert result["total_predictions"] == 0
