"""Generates simulation requirement prompts for T+1, T+3, T+7 horizons."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _add_trading_days(start: datetime, trading_days: int) -> datetime:
    """Add N trading days (skip weekends) to a date."""
    current = start
    added = 0
    while added < trading_days:
        current += timedelta(days=1)
        # Monday=0 ... Friday=4, Saturday=5, Sunday=6
        if current.weekday() < 5:
            added += 1
    return current


class QuestionDesigner:
    """Reads the financial seed content and produces simulation prompts."""

    def __init__(self, tickers: list[str]):
        self.tickers = tickers

    def design(self, horizon: str, run_date: str, md_content: str) -> str:
        """Generate a simulation_requirement prompt for the given horizon.

        Args:
            horizon: "t1", "t3", or "t7"
            run_date: YYYY-MM-DD string for the prediction run date
            md_content: The windowed MD seed file content
        Returns:
            A simulation_requirement string to pass to /api/graph/ontology/generate
        """
        dt = datetime.strptime(run_date, "%Y-%m-%d")
        tickers_str = ", ".join(self.tickers)

        if horizon == "t1":
            target = _add_trading_days(dt, 1)
            return self._t1_prompt(run_date, target.strftime("%Y-%m-%d"), tickers_str)
        elif horizon == "t3":
            target = _add_trading_days(dt, 3)
            return self._t3_prompt(run_date, target.strftime("%Y-%m-%d"), tickers_str)
        elif horizon == "t7":
            target = _add_trading_days(dt, 7)
            return self._t7_prompt(run_date, target.strftime("%Y-%m-%d"), tickers_str)
        else:
            raise ValueError(f"Unknown horizon: {horizon}")

    def _t1_prompt(self, run_date: str, target_date: str, tickers: str) -> str:
        return f"""FORWARD TESTING PREDICTION — T+1 (Next Trading Day)
Run date: {run_date} | Target date: {target_date}
Tickers: {tickers}

You are simulating market participants reacting to the latest news and market conditions documented in the uploaded financial intelligence report. Your goal is to predict what happens on the NEXT TRADING DAY ({target_date}).

Simulate diverse agents — institutional investors, retail traders, hedge fund managers, macro strategists, energy analysts, political commentators, tech analysts, risk managers — debating on Twitter and Reddit.

Each agent should consider and debate:
1. S&P 500 direction and likely range for {target_date} — provide probability distributions across bull/base/bear/tail scenarios, NOT point predictions
2. Which of these tickers will move the most and why: {tickers}
3. The dominant narrative driving tomorrow's price action
4. Key risk events in the next 24 hours (earnings, Fed speeches, geopolitical deadlines, oil data)
5. Retail vs institutional sentiment divergence
6. Oil/gold/treasury yield direction and their second-order effects on equities
7. Political developments that could move markets overnight
8. Options market signals — unusual activity, put/call skews
9. Per-ticker sentiment distribution (strongly bullish to strongly bearish)
10. What is the most likely narrative shift from today to tomorrow?

IMPORTANT: Agents must debate and disagree. No consensus is fine — capture the full range of views. Provide probability-weighted scenarios with detailed narratives for each, not single-point predictions."""

    def _t3_prompt(self, run_date: str, target_date: str, tickers: str) -> str:
        return f"""FORWARD TESTING PREDICTION — T+3 (3 Trading Days Out)
Run date: {run_date} | Target date: {target_date}
Tickers: {tickers}

You are simulating market participants analyzing how current market dynamics evolve over the next 3 trading days through {target_date}. Use the uploaded financial intelligence report as your information base.

Simulate diverse agents — institutional investors, retail traders, hedge fund managers, macro strategists, energy analysts, political commentators, tech analysts, risk managers — debating on Twitter and Reddit.

Each agent should consider and debate:
1. Does today's dominant narrative strengthen or fade over 3 days?
2. S&P 500 trajectory — provide probability distributions across scenarios (bull/base/bear/tail) with ranges and detailed narratives for each
3. Sector rotation signals — where is money flowing and why?
4. Geopolitical escalation/de-escalation probability and impact
5. Which ticker has the highest asymmetric risk/reward setup?
6. Fed/political catalyst risk in the 3-day window
7. Oil price trajectory and its cascading effects on consumer spending, margins, and inflation expectations
8. Gold, treasury, and dollar index movements
9. Per-ticker probability-weighted outlook: {tickers}
10. Narrative prediction — what will be the dominant market story in 3 days?
11. Agent consensus level — how divided are market participants?
12. What wildcards could invalidate all scenarios?

IMPORTANT: Provide probability distributions, NOT point predictions. Agents must debate with conviction and disagree. Capture bull camp arguments, bear camp arguments, and neutral reasoning."""

    def _t7_prompt(self, run_date: str, target_date: str, tickers: str) -> str:
        return f"""FORWARD TESTING PREDICTION — T+7 (7 Trading Days Out)
Run date: {run_date} | Target date: {target_date}
Tickers: {tickers}

You are simulating market participants analyzing the broader market trajectory over the next 7 trading days through {target_date}. Use the uploaded financial intelligence report as your comprehensive information base.

Simulate diverse agents — institutional investors, retail traders, hedge fund managers, macro strategists, energy analysts, geopolitical experts, political commentators, tech analysts, risk managers, central bank watchers — debating on Twitter and Reddit.

Each agent should consider and debate:
1. Macro regime — are we shifting from the current state? Is the market repricing growth, inflation, or risk?
2. S&P 500 range and probability distribution across scenarios: bull (probability, range, narrative), base (probability, range, narrative), bear (probability, range, narrative), tail risk (probability, range, narrative)
3. Narrative prediction — what will be the DOMINANT market story 7 days from now? Predict narrative shifts.
4. Oil/gold/treasury yield/dollar direction with probability-weighted scenarios and second-order effects
5. Per-ticker outlook with catalyst calendar for the 7-day window: {tickers}
6. Political developments that could change the trajectory (Fed Chair nomination, Congressional action, diplomatic moves)
7. Sentiment cascade risk — what could trigger a sharp 3%+ move in either direction?
8. Earnings calendar impact — any major reports due in the window?
9. Agent debate summary — what are the strongest bull and bear arguments?
10. Consensus level — how aligned or divided are market participants?
11. What would it take for the tail risk scenario to materialize?
12. Probability-weighted prediction for each major asset class

IMPORTANT: This is a 7-day window — there is genuine uncertainty. Reflect that in wide scenario ranges and honest probability assessments. Agents must argue passionately for their views. No point predictions — only probability distributions with full narrative reasoning."""
