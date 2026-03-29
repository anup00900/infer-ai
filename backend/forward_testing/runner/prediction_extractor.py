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
        load_dotenv()

        client = AzureOpenAI(
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        )

        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

        extraction_prompt = f"""You are a financial prediction extraction system. Extract structured predictions from this simulation report.

Horizon: {horizon.upper()} | Run date: {run_date} | Target date: {target_date}
Tickers: {', '.join(tickers)}

Return ONLY valid JSON with this exact structure:
{{
    "date_generated": "{run_date}",
    "horizon": "{horizon}",
    "target_date": "{target_date}",
    "market_outlook": {{
        "sp500": {{
            "scenarios": [
                {{"label": "bull", "probability": 0.25, "range": [low, high], "narrative": "..."}},
                {{"label": "base", "probability": 0.45, "range": [low, high], "narrative": "..."}},
                {{"label": "bear", "probability": 0.25, "range": [low, high], "narrative": "..."}},
                {{"label": "tail_risk", "probability": 0.05, "range": [low, high], "narrative": "..."}}
            ],
            "key_uncertainties": ["...", "..."]
        }},
        "vix": {{
            "scenarios": [
                {{"label": "compression", "probability": 0.3, "range": [low, high], "driver": "..."}},
                {{"label": "elevated", "probability": 0.45, "range": [low, high], "driver": "..."}},
                {{"label": "spike", "probability": 0.25, "range": [low, high], "driver": "..."}}
            ]
        }}
    }},
    "macro_outlook": {{
        "oil_brent": {{
            "scenarios": [
                {{"label": "decline", "probability": 0.2, "range": [low, high], "narrative": "..."}},
                {{"label": "stable", "probability": 0.5, "range": [low, high], "narrative": "..."}},
                {{"label": "escalation", "probability": 0.25, "range": [low, high], "narrative": "..."}},
                {{"label": "crisis", "probability": 0.05, "range": [low, high], "narrative": "..."}}
            ]
        }},
        "gold": {{
            "scenarios": [{{"label": "...", "probability": 0.0, "range": [low, high], "narrative": "..."}}]
        }},
        "treasury_10y": {{
            "scenarios": [{{"label": "...", "probability": 0.0, "range": [low, high], "narrative": "..."}}]
        }}
    }},
    "ticker_outlook": [
        {{
            "ticker": "NVDA",
            "scenarios": [
                {{"label": "outperform", "probability": 0.4, "narrative": "..."}},
                {{"label": "inline", "probability": 0.4, "narrative": "..."}},
                {{"label": "underperform", "probability": 0.2, "narrative": "..."}}
            ],
            "key_catalysts": ["...", "..."],
            "agent_sentiment_distribution": {{
                "strongly_bullish": 0.0, "bullish": 0.0, "neutral": 0.0,
                "bearish": 0.0, "strongly_bearish": 0.0
            }}
        }}
    ],
    "narrative_prediction": {{
        "current_dominant_narrative": "...",
        "predicted_narrative_shift": {{
            "most_likely": {{"probability": 0.0, "narrative": "...", "trigger": "..."}},
            "alternative_1": {{"probability": 0.0, "narrative": "...", "trigger": "..."}},
            "alternative_2": {{"probability": 0.0, "narrative": "...", "trigger": "..."}}
        }},
        "wildcards": ["...", "..."]
    }},
    "agent_debate_summary": {{
        "total_agents": 0,
        "consensus_level": 0.0,
        "bull_camp": {{"percentage": 0.0, "core_argument": "..."}},
        "bear_camp": {{"percentage": 0.0, "core_argument": "..."}},
        "neutral_camp": {{"percentage": 0.0, "core_argument": "..."}},
        "most_heated_debates": ["...", "..."]
    }}
}}

Extract ALL values from the report. For probabilities, infer from the language used (e.g., "most likely" = 0.4-0.6, "unlikely" = 0.1-0.2). For ranges, use specific numbers mentioned in the report.

REPORT:
{report_md}"""

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

        prediction = json.loads(content)
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
