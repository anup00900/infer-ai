"""Computes accuracy scorecards for matured predictions."""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def score_prediction(prediction_path: str, actuals_path: str, output_path: str) -> dict:
    """Score a prediction against actual market data.

    Args:
        prediction_path: Path to prediction.json
        actuals_path: Path to actuals.json
        output_path: Where to save scorecard.json
    """
    with open(prediction_path) as f:
        prediction = json.load(f)
    with open(actuals_path) as f:
        actuals = json.load(f)

    scorecard = {
        "prediction_date": prediction.get("date_generated"),
        "horizon": prediction.get("horizon"),
        "target_date": prediction.get("target_date"),
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }

    # Score S&P 500 — handle both LLM format (sp500_scenarios dict) and old format (market_outlook.sp500.scenarios list)
    sp500_actual = actuals.get("market", {}).get("sp500", {}).get("close")
    sp500_actual_change = actuals.get("market", {}).get("sp500", {}).get("change_pct", 0)
    if sp500_actual:
        sp_scenarios_raw = prediction.get("sp500_scenarios") or prediction.get("market_outlook", {}).get("sp500", {}).get("scenarios", [])
        if isinstance(sp_scenarios_raw, dict):
            # LLM format: {"bull": {"probability": 0.2, "narrative": "..."}, ...}
            bull_prob = sp_scenarios_raw.get("bull", {}).get("probability", 0) or 0
            bear_prob = sp_scenarios_raw.get("bear", {}).get("probability", 0) or 0
            predicted_direction = "up" if bull_prob > bear_prob else "down"
            actual_direction = "up" if sp500_actual_change > 0 else "down"
            scorecard["market_score"] = {
                "sp500_actual": sp500_actual,
                "sp500_change_pct": sp500_actual_change,
                "predicted_direction": predicted_direction,
                "direction_correct": predicted_direction == actual_direction,
                "bull_probability": bull_prob,
                "base_probability": sp_scenarios_raw.get("base", {}).get("probability", 0) or 0,
                "bear_probability": bear_prob,
            }
        elif isinstance(sp_scenarios_raw, list):
            scorecard["market_score"] = _score_scenarios(sp_scenarios_raw, sp500_actual, "sp500")

    # Score tickers — handle both LLM format (dict of tickers) and old format (list of dicts)
    ticker_scores = []
    ticker_outlook = prediction.get("ticker_outlook", {})
    if isinstance(ticker_outlook, dict):
        # LLM format: {"NVDA": {"bull_probability": 0.3, "bear_probability": 0.25, ...}, ...}
        for ticker, pred_data in ticker_outlook.items():
            if not isinstance(pred_data, dict):
                continue
            actual = actuals.get("tickers", {}).get(ticker, {})
            if actual:
                bull_p = pred_data.get("bull_probability", 0) or 0
                bear_p = pred_data.get("bear_probability", 0) or 0
                predicted_direction = "up" if bull_p >= bear_p else "down"
                actual_change = actual.get("change_pct", 0)
                actual_direction = "up" if actual_change > 0 else "down"
                ticker_scores.append({
                    "ticker": ticker,
                    "predicted_direction": predicted_direction,
                    "bull_probability": bull_p,
                    "bear_probability": bear_p,
                    "actual_change_pct": actual_change,
                    "direction_correct": predicted_direction == actual_direction,
                })
    elif isinstance(ticker_outlook, list):
        for ticker_pred in ticker_outlook:
            ticker = ticker_pred.get("ticker")
            actual = actuals.get("tickers", {}).get(ticker, {})
            if actual:
                actual_change = actual.get("change_pct", 0)
                scenarios = ticker_pred.get("scenarios", [])
                if scenarios:
                    top_scenario = max(scenarios, key=lambda s: s.get("probability", 0))
                    predicted_direction = "up" if top_scenario["label"] in ("outperform", "bull") else "down"
                    actual_direction = "up" if actual_change > 0 else "down"
                    ticker_scores.append({
                        "ticker": ticker,
                        "predicted_direction": predicted_direction,
                        "predicted_probability": top_scenario.get("probability", 0),
                        "actual_change_pct": actual_change,
                        "direction_correct": predicted_direction == actual_direction,
                    })
    scorecard["ticker_scores"] = ticker_scores

    # Score macro
    macro_scores = {}
    macro_mapping = {
        "oil_brent": "brent_crude",
        "gold": "gold",
        "treasury_10y": "treasury_10y",
    }
    for pred_key, actual_key in macro_mapping.items():
        actual_val = actuals.get("market", {}).get(actual_key, {}).get("close")
        pred_scenarios = prediction.get("macro_outlook", {}).get(pred_key, {}).get("scenarios", [])
        if actual_val and pred_scenarios:
            macro_scores[pred_key] = _score_scenarios(pred_scenarios, actual_val, pred_key)
    scorecard["macro_scores"] = macro_scores

    # Compute summary stats
    ticker_correct = sum(1 for t in ticker_scores if t.get("direction_correct"))
    ticker_total = len(ticker_scores) or 1
    scorecard["summary"] = {
        "ticker_direction_accuracy": round(ticker_correct / ticker_total, 3),
        "sp500_scenario_hit": scorecard.get("market_score", {}).get("scenario_hit"),
        "sp500_highest_prob_correct": scorecard.get("market_score", {}).get("highest_prob_correct"),
    }

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(scorecard, f, indent=2)

    logger.info(f"Scorecard saved to {output_path}")
    return scorecard


def _score_scenarios(scenarios: list, actual_value: float, label: str) -> dict:
    """Check which scenario range contains the actual value."""
    hit_scenario = None
    highest_prob_scenario = None
    highest_prob = 0

    for s in scenarios:
        prob = s.get("probability", 0)
        if prob > highest_prob:
            highest_prob = prob
            highest_prob_scenario = s.get("label")

        range_vals = s.get("range", [])
        if len(range_vals) == 2:
            low, high = range_vals
            if low <= actual_value <= high:
                hit_scenario = s.get("label")

    return {
        "actual_value": actual_value,
        "scenario_hit": hit_scenario,
        "scenario_hit_probability": next(
            (s["probability"] for s in scenarios if s.get("label") == hit_scenario), None
        ),
        "highest_prob_scenario": highest_prob_scenario,
        "highest_prob_correct": hit_scenario == highest_prob_scenario if hit_scenario else None,
    }


def compute_rolling_scorecard(results_dir: str, output_path: str) -> dict:
    """Aggregate all individual scorecards into a rolling scorecard."""
    all_scorecards = []

    for day_dir in sorted(os.listdir(results_dir)):
        day_path = os.path.join(results_dir, day_dir)
        if not os.path.isdir(day_path) or not day_dir.startswith("20"):
            continue

        for horizon in ["t1", "t3", "t7"]:
            scorecard_path = os.path.join(day_path, f"simulation_{horizon}", "scorecard.json")
            if os.path.exists(scorecard_path):
                with open(scorecard_path) as f:
                    sc = json.load(f)
                    sc["_day"] = day_dir
                    all_scorecards.append(sc)

    if not all_scorecards:
        rolling = {"as_of": datetime.now(timezone.utc).isoformat(), "total_predictions": 0, "message": "No scored predictions yet"}
        with open(output_path, "w") as f:
            json.dump(rolling, f, indent=2)
        return rolling

    # Aggregate by horizon
    rolling = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "total_predictions": len(all_scorecards),
    }

    for horizon in ["t1", "t3", "t7"]:
        horizon_cards = [sc for sc in all_scorecards if sc.get("horizon") == horizon]
        if not horizon_cards:
            continue

        direction_hits = sum(
            sc.get("summary", {}).get("ticker_direction_accuracy", 0)
            for sc in horizon_cards
        )
        sp_hits = sum(
            1 for sc in horizon_cards
            if sc.get("summary", {}).get("sp500_highest_prob_correct") is True
        )

        rolling[f"{horizon}_accuracy"] = {
            "count": len(horizon_cards),
            "avg_ticker_direction_accuracy": round(direction_hits / len(horizon_cards), 3),
            "sp500_highest_prob_correct_rate": round(sp_hits / len(horizon_cards), 3),
        }

    with open(output_path, "w") as f:
        json.dump(rolling, f, indent=2)

    logger.info(f"Rolling scorecard saved to {output_path} ({len(all_scorecards)} predictions)")
    return rolling
