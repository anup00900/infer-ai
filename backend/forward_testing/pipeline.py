"""Master orchestrator for the daily forward-testing pipeline."""
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

from forward_testing.config import ForwardTestingConfig
from forward_testing.news.aggregator import NewsAggregator
from forward_testing.news.formatter import MDFormatter
from forward_testing.augmenter.md_augmenter import MDAugmenter
from forward_testing.runner.question_designer import QuestionDesigner
from forward_testing.runner.simulation_runner import SimulationRunner, SimulationRunnerError
from forward_testing.runner.prediction_extractor import extract_predictions
from forward_testing.scorer.actuals_fetcher import fetch_actuals
from forward_testing.scorer.scorecard import score_prediction, compute_rolling_scorecard

logger = logging.getLogger(__name__)

HORIZONS = ["t1", "t3", "t7"]
HORIZON_DAYS = {"t1": 1, "t3": 3, "t7": 7}


class Pipeline:
    """Orchestrates the complete daily forward-testing pipeline."""

    def __init__(self, config: ForwardTestingConfig = None):
        self.config = config or ForwardTestingConfig()
        self.api_base = os.environ.get("INFER_API_BASE", "http://localhost:5001")

    def run_daily(self, date_str: str = None):
        """Run the complete daily pipeline for a given date."""
        date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_dir = os.path.join(self.config.results_dir, date_str)
        os.makedirs(day_dir, exist_ok=True)

        checkpoint = self._load_checkpoint(day_dir)
        logger.info(f"=== Forward Testing Pipeline: {date_str} ===")

        # Phase 1: Fetch prices (for actuals + scoring)
        if not checkpoint.get("fetch_prices"):
            try:
                logger.info("Phase 1: Fetching market prices...")
                actuals = fetch_actuals(date_str, self.config.tickers, day_dir)
                self._save_checkpoint(day_dir, "fetch_prices", "completed")
                logger.info(f"  Prices saved: {len(actuals.get('tickers', {}))} tickers")
            except Exception as e:
                logger.error(f"  Price fetch failed: {e}")
                self._save_checkpoint(day_dir, "fetch_prices", "failed")

        # Phase 2: Fetch news + augment MD
        if not checkpoint.get("fetch_news"):
            try:
                logger.info("Phase 2: Fetching news and augmenting seed file...")
                self._run_news_pipeline(date_str, day_dir)
                self._save_checkpoint(day_dir, "fetch_news", "completed")
            except Exception as e:
                logger.error(f"  News fetch failed: {e}")
                self._save_checkpoint(day_dir, "fetch_news", "failed")

        # Phase 3: Score any matured predictions
        self._score_matured_predictions(date_str, day_dir)

        # Phase 4: Run simulations for T+1, T+3, T+7
        self._ensure_backend_running()

        for horizon in HORIZONS:
            phase_key = f"simulation_{horizon}"
            if checkpoint.get(phase_key):
                logger.info(f"  Skipping {horizon} (already completed)")
                continue

            try:
                logger.info(f"Phase 4: Running {horizon.upper()} simulation...")
                self._run_simulation(date_str, horizon, day_dir)
                self._save_checkpoint(day_dir, phase_key, "completed")
            except Exception as e:
                logger.error(f"  {horizon.upper()} simulation failed: {e}")
                self._save_checkpoint(day_dir, phase_key, "failed")

        # Phase 5: Compute rolling scorecard
        try:
            rolling_path = os.path.join(self.config.results_dir, "rolling_scorecard.json")
            compute_rolling_scorecard(self.config.results_dir, rolling_path)
        except Exception as e:
            logger.warning(f"Rolling scorecard failed: {e}")

        logger.info(f"=== Pipeline complete for {date_str} ===")

    def run_news_only(self, date_str: str = None):
        """Run only the news fetch + augment phase."""
        date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_dir = os.path.join(self.config.results_dir, date_str)
        os.makedirs(day_dir, exist_ok=True)
        self._run_news_pipeline(date_str, day_dir)

    def run_prices_only(self, date_str: str = None):
        """Run only the price fetch phase."""
        date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_dir = os.path.join(self.config.results_dir, date_str)
        os.makedirs(day_dir, exist_ok=True)
        fetch_actuals(date_str, self.config.tickers, day_dir)

    def run_simulations_only(self, date_str: str = None):
        """Run only the simulation phase (assumes news already fetched)."""
        date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_dir = os.path.join(self.config.results_dir, date_str)
        os.makedirs(day_dir, exist_ok=True)

        self._ensure_backend_running()

        for horizon in HORIZONS:
            checkpoint = self._load_checkpoint(day_dir)
            phase_key = f"simulation_{horizon}"
            if checkpoint.get(phase_key):
                logger.info(f"  Skipping {horizon} (already completed)")
                continue
            try:
                self._run_simulation(date_str, horizon, day_dir)
                self._save_checkpoint(day_dir, phase_key, "completed")
            except Exception as e:
                logger.error(f"  {horizon.upper()} simulation failed: {e}")
                self._save_checkpoint(day_dir, phase_key, "failed")

    # ---- Internal ----

    def _run_news_pipeline(self, date_str: str, day_dir: str):
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        date_label = dt.strftime("%B %d, %Y")

        augmenter = MDAugmenter(self.config)
        if not os.path.exists(augmenter.live_path):
            # Auto-init from original seed
            original = os.path.join(self.config.base_dir, "..", "demo", "financial_seed_mar25_2026-2.md")
            if os.path.exists(original):
                augmenter.initialize_from_original(original)
            else:
                raise FileNotFoundError("Live seed not initialized and original not found")

        aggregator = NewsAggregator(self.config)
        result = aggregator.fetch_all()
        aggregator.save_raw(result, date_str)

        formatter = MDFormatter(self.config)
        daily_md = formatter.format(result, date_label)
        augmenter.append_daily(daily_md, date_str)

        logger.info(f"  News pipeline done: {len(result.news_items)} items from {len(result.source_counts)} sources")

    def _run_simulation(self, date_str: str, horizon: str, day_dir: str):
        sim_dir = os.path.join(day_dir, f"simulation_{horizon}")
        os.makedirs(sim_dir, exist_ok=True)

        # Get windowed MD content
        augmenter = MDAugmenter(self.config)
        md_content = augmenter.get_windowed_view(window_days=7)

        # Save windowed view for this run
        windowed_path = os.path.join(sim_dir, "windowed_seed.md")
        with open(windowed_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Design question
        designer = QuestionDesigner(self.config.tickers)
        sim_requirement = designer.design(horizon, date_str, md_content)

        # Save the simulation requirement
        with open(os.path.join(sim_dir, "simulation_requirement.txt"), "w") as f:
            f.write(sim_requirement)

        # Calculate target date
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        target_dt = dt + timedelta(days=HORIZON_DAYS[horizon])
        target_date = target_dt.strftime("%Y-%m-%d")

        # Run simulation via API
        runner = SimulationRunner(api_base=self.api_base)
        result = runner.run_full_pipeline(
            md_file_path=windowed_path,
            simulation_requirement=sim_requirement,
            output_dir=sim_dir,
            max_rounds=5,
            project_name=f"forward_test_{date_str}_{horizon}",
        )

        # Save run metadata
        with open(os.path.join(sim_dir, "run_meta.json"), "w") as f:
            json.dump({
                "date": date_str,
                "horizon": horizon,
                "target_date": target_date,
                **result,
            }, f, indent=2)

        # Extract predictions from report
        report_path = result.get("report_path", os.path.join(sim_dir, "report.md"))
        if os.path.exists(report_path):
            with open(report_path, "r") as f:
                report_md = f.read()
            extract_predictions(
                report_md=report_md,
                horizon=horizon,
                run_date=date_str,
                target_date=target_date,
                tickers=self.config.tickers,
                output_path=os.path.join(sim_dir, "prediction.json"),
            )

        logger.info(f"  {horizon.upper()} simulation complete. Results in {sim_dir}")

    def _score_matured_predictions(self, today_str: str, today_dir: str):
        """Check for predictions that matured today and score them."""
        today_dt = datetime.strptime(today_str, "%Y-%m-%d")
        actuals_path = os.path.join(today_dir, "actuals.json")

        if not os.path.exists(actuals_path):
            return

        # Check all past dates for predictions targeting today
        for day_name in sorted(os.listdir(self.config.results_dir)):
            day_path = os.path.join(self.config.results_dir, day_name)
            if not os.path.isdir(day_path) or not day_name.startswith("20"):
                continue

            for horizon in HORIZONS:
                sim_dir = os.path.join(day_path, f"simulation_{horizon}")
                pred_path = os.path.join(sim_dir, "prediction.json")
                scorecard_path = os.path.join(sim_dir, "scorecard.json")

                if not os.path.exists(pred_path) or os.path.exists(scorecard_path):
                    continue

                try:
                    with open(pred_path) as f:
                        pred = json.load(f)

                    target_date = pred.get("target_date")
                    if target_date == today_str:
                        logger.info(f"  Scoring matured prediction: {day_name}/{horizon} -> {target_date}")
                        score_prediction(pred_path, actuals_path, scorecard_path)
                except Exception as e:
                    logger.warning(f"  Failed to score {day_name}/{horizon}: {e}")

    def _ensure_backend_running(self):
        """Check if Infer backend is running, start it if not."""
        runner = SimulationRunner(api_base=self.api_base)
        if runner.check_health():
            logger.info("  Backend is running.")
            return

        logger.info("  Backend not running. Starting...")
        backend_dir = os.path.join(self.config.base_dir)
        run_py = os.path.join(backend_dir, "run.py")

        if not os.path.exists(run_py):
            raise FileNotFoundError(f"Backend run.py not found at {run_py}")

        # Start backend in background
        subprocess.Popen(
            [sys.executable, run_py],
            cwd=backend_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for it to become healthy
        for _ in range(12):  # 60 seconds max
            time.sleep(5)
            if runner.check_health():
                logger.info("  Backend started successfully.")
                return

        raise RuntimeError("Backend failed to start within 60 seconds")

    def _load_checkpoint(self, day_dir: str) -> dict:
        path = os.path.join(day_dir, "checkpoint.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}

    def _save_checkpoint(self, day_dir: str, phase: str, status: str):
        path = os.path.join(day_dir, "checkpoint.json")
        checkpoint = self._load_checkpoint(day_dir)
        checkpoint[phase] = status
        checkpoint["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w") as f:
            json.dump(checkpoint, f, indent=2)
