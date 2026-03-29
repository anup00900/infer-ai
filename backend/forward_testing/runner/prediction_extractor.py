"""Extracts structured predictions from simulation report markdown."""
import json
import logging
import os
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def extract_predictions(
    report_md: str,
    horizon: str,
    run_date: str,
    target_date: str,
    tickers: list[str],
    output_path: str,
) -> dict:
    """Extract structured predictions from a simulation report.

    Uses LLM to parse the report into structured JSON. Falls back to
    regex-based extraction if LLM is unavailable.

    Args:
        report_md: The full markdown report content
        horizon: "t1", "t3", or "t7"
        run_date: YYYY-MM-DD
        target_date: YYYY-MM-DD
        tickers: List of ticker symbols
        output_path: Where to save prediction.json

    Returns:
        The prediction dict
    """
    prediction = _try_llm_extraction(report_md, horizon, run_date, target_date, tickers)
    if not prediction:
        prediction = _regex_extraction(report_md, horizon, run_date, target_date, tickers)

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(prediction, f, indent=2, ensure_ascii=False)

    logger.info(f"Prediction saved to {output_path}")
    return prediction


def _try_llm_extraction(
    report_md: str, horizon: str, run_date: str, target_date: str, tickers: list[str]
) -> Optional[dict]:
    """Try to use Azure OpenAI to extract structured predictions."""
    try:
        from openai import AzureOpenAI
        from dotenv import load_dotenv
        # Load .env from project root
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "..", ".env")
        load_dotenv(env_path)
        load_dotenv()  # Also try CWD

        client = AzureOpenAI(
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        )

        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

        tickers_str = ", ".join(tickers)
        extraction_prompt = f"""Extract predictions from this simulation report as JSON.

Run date: {run_date} | Target: {target_date} | Horizon: {horizon.upper()}
Tickers: {tickers_str}

Return ONLY a JSON object (no markdown, no explanation) with these keys:
- "sp500_scenarios": object with "bull", "base", "bear", "tail" keys, each having "probability" (decimal 0-1), "narrative" (string)
- "oil_outlook": string describing oil price direction and reasoning
- "gold_outlook": string describing gold direction
- "vix_outlook": string describing volatility outlook
- "ticker_outlook": object where each key is a ticker symbol, value has "bull_probability" (decimal), "bear_probability" (decimal), "sentiment" (string), "key_driver" (string)
- "dominant_narrative": string describing the main market story
- "narrative_shift": string describing how the narrative might change
- "bull_argument": string — strongest bull case
- "bear_argument": string — strongest bear case
- "wildcards": array of strings — events that could change everything
- "agent_consensus": decimal 0-1, how much agents agree (0=divided, 1=unanimous)

Use decimal probabilities (0.25 not "25%"). Extract real values from the report, not placeholders.

REPORT:
{report_md[:15000]}"""

        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0.1,
            max_tokens=4096,
        )

        content = response.choices[0].message.content
        # Extract JSON from response (may be wrapped in ```json ... ```)
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        # Try to find JSON object in response
        if not content.strip().startswith("{"):
            obj_match = re.search(r'\{.*\}', content, re.DOTALL)
            if obj_match:
                content = obj_match.group(0)

        prediction = json.loads(content)
        prediction["date_generated"] = run_date
        prediction["horizon"] = horizon
        prediction["target_date"] = target_date
        prediction["extraction_method"] = "llm"
        return prediction

    except Exception as e:
        logger.warning(f"LLM extraction failed, falling back to regex: {e}")
        return None


def _regex_extraction(
    report_md: str, horizon: str, run_date: str, target_date: str, tickers: list[str]
) -> dict:
    """Fallback: extract basic predictions using regex patterns."""

    # Try to find S&P 500 numbers
    sp_numbers = re.findall(r'S&P\s*500[^0-9]*?(\d[,\d]+)', report_md)
    sp_values = [float(n.replace(",", "")) for n in sp_numbers if float(n.replace(",", "")) > 4000]

    sp_low = min(sp_values) if sp_values else 6300
    sp_high = max(sp_values) if sp_values else 6700
    sp_mid = (sp_low + sp_high) / 2

    # Try to find oil numbers
    oil_numbers = re.findall(r'\$(\d+(?:\.\d+)?)/bbl', report_md)
    oil_values = [float(n) for n in oil_numbers if 50 < float(n) < 200]

    # Try to find sentiment words
    bullish_count = len(re.findall(r'\bbullish\b', report_md, re.I))
    bearish_count = len(re.findall(r'\bbearish\b', report_md, re.I))
    total_sentiment = bullish_count + bearish_count or 1
    bull_pct = bullish_count / total_sentiment

    prediction = {
        "date_generated": run_date,
        "horizon": horizon,
        "target_date": target_date,
        "extraction_method": "regex_fallback",
        "market_outlook": {
            "sp500": {
                "scenarios": [
                    {"label": "bull", "probability": 0.25, "range": [sp_mid, sp_high], "narrative": "Extracted from report ranges"},
                    {"label": "base", "probability": 0.50, "range": [sp_low, sp_mid], "narrative": "Mid-range estimate"},
                    {"label": "bear", "probability": 0.20, "range": [sp_low * 0.97, sp_low], "narrative": "Downside estimate"},
                    {"label": "tail_risk", "probability": 0.05, "range": [sp_low * 0.93, sp_low * 0.97], "narrative": "Tail risk"},
                ],
                "key_uncertainties": ["Extracted via regex fallback — limited accuracy"]
            }
        },
        "macro_outlook": {
            "oil_brent": {
                "scenarios": [
                    {"label": "stable", "probability": 0.5, "range": [min(oil_values, default=95), max(oil_values, default=110)], "narrative": "From report ranges"}
                ]
            }
        },
        "ticker_outlook": [
            {"ticker": t, "scenarios": [
                {"label": "outperform", "probability": bull_pct, "narrative": "Sentiment-based"},
                {"label": "underperform", "probability": 1 - bull_pct, "narrative": "Sentiment-based"},
            ]} for t in tickers
        ],
        "narrative_prediction": {
            "current_dominant_narrative": report_md[:1000] if report_md else "No report content",
            "predicted_narrative_shift": {"most_likely": {"probability": 0.5, "narrative": "See full report", "trigger": "See full report"}},
            "wildcards": []
        },
        "agent_debate_summary": {
            "total_agents": 0,
            "consensus_level": 0.5,
            "bull_camp": {"percentage": bull_pct, "core_argument": "See report"},
            "bear_camp": {"percentage": 1 - bull_pct, "core_argument": "See report"},
        },
        "report_length_chars": len(report_md) if report_md else 0,
    }

    return prediction
