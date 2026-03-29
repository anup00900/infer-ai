"""Drives the Infer simulation pipeline via REST API calls."""
import json
import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_API_BASE = "http://localhost:5001"


class SimulationRunnerError(Exception):
    pass


class SimulationRunner:
    """Calls Infer backend APIs to run a full simulation pipeline."""

    def __init__(self, api_base: str = DEFAULT_API_BASE, timeout: int = 300):
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout  # per-request timeout
        self.poll_interval = 15  # seconds between status polls
        self.max_poll_time = 14400  # 4 hours max for any single phase

    def check_health(self) -> bool:
        """Check if the backend is running."""
        try:
            resp = requests.get(f"{self.api_base}/health", timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def run_full_pipeline(
        self,
        md_file_path: str,
        simulation_requirement: str,
        output_dir: str,
        max_rounds: int = 5,
        project_name: str = "forward_test",
    ) -> dict:
        """Run the complete pipeline: ontology → graph → sim → report → download.

        Returns dict with project_id, graph_id, simulation_id, report_id, report_path.
        """
        result = {}

        # Phase 1: Generate ontology
        logger.info("Phase 1/6: Generating ontology...")
        onto_data = self._generate_ontology(md_file_path, simulation_requirement, project_name)
        project_id = onto_data["project_id"]
        result["project_id"] = project_id
        logger.info(f"  Ontology generated. Project: {project_id}")

        # Phase 2: Build graph
        logger.info("Phase 2/6: Building knowledge graph...")
        build_data = self._build_graph(project_id)
        task_id = build_data["task_id"]
        self._poll_task(task_id, "Graph build")
        # Get graph_id from project
        project_data = self._get_project(project_id)
        graph_id = project_data.get("graph_id")
        result["graph_id"] = graph_id
        logger.info(f"  Graph built. Graph: {graph_id}")

        # Phase 3: Create simulation
        logger.info("Phase 3/6: Creating simulation...")
        sim_data = self._create_simulation(project_id, graph_id)
        simulation_id = sim_data["simulation_id"]
        result["simulation_id"] = simulation_id
        logger.info(f"  Simulation created: {simulation_id}")

        # Phase 4: Prepare simulation (generate agent personas + config)
        logger.info("Phase 4/6: Preparing simulation (generating agents)...")
        prep_data = self._prepare_simulation(simulation_id)
        prep_task_id = prep_data.get("task_id")
        if prep_task_id:
            self._poll_task(prep_task_id, "Simulation preparation")
        logger.info("  Simulation prepared.")

        # Phase 5: Start simulation
        logger.info(f"Phase 5/6: Running simulation ({max_rounds} rounds)...")
        self._start_simulation(simulation_id, max_rounds=max_rounds)
        self._poll_simulation(simulation_id)
        logger.info("  Simulation completed.")

        # Phase 6: Generate and download report
        logger.info("Phase 6/6: Generating report...")
        report_data = self._generate_report(simulation_id)
        report_id = report_data.get("report_id")
        report_task_id = report_data.get("task_id")
        if report_task_id:
            self._poll_report(report_task_id, simulation_id)
        result["report_id"] = report_id

        # Download report
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, "report.md")
        self._download_report(report_id, report_path)
        result["report_path"] = report_path
        logger.info(f"  Report saved to {report_path}")

        return result

    # ---- API calls ----

    def _generate_ontology(self, md_file_path: str, simulation_requirement: str, project_name: str) -> dict:
        with open(md_file_path, "rb") as f:
            files = {"files": (os.path.basename(md_file_path), f, "text/markdown")}
            data = {
                "simulation_requirement": simulation_requirement,
                "project_name": project_name,
            }
            resp = requests.post(
                f"{self.api_base}/api/graph/ontology/generate",
                files=files, data=data, timeout=self.timeout
            )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise SimulationRunnerError(f"Ontology generation failed: {body.get('error')}")
        return body["data"]

    def _build_graph(self, project_id: str) -> dict:
        resp = requests.post(
            f"{self.api_base}/api/graph/build",
            json={"project_id": project_id},
            timeout=self.timeout
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise SimulationRunnerError(f"Graph build failed: {body.get('error')}")
        return body["data"]

    def _get_project(self, project_id: str) -> dict:
        resp = requests.get(
            f"{self.api_base}/api/graph/project/{project_id}",
            timeout=self.timeout
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise SimulationRunnerError(f"Get project failed: {body.get('error')}")
        return body["data"]

    def _create_simulation(self, project_id: str, graph_id: str) -> dict:
        resp = requests.post(
            f"{self.api_base}/api/simulation/create",
            json={"project_id": project_id, "graph_id": graph_id,
                  "enable_twitter": True, "enable_reddit": True},
            timeout=self.timeout
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise SimulationRunnerError(f"Simulation create failed: {body.get('error')}")
        return body["data"]

    def _prepare_simulation(self, simulation_id: str) -> dict:
        resp = requests.post(
            f"{self.api_base}/api/simulation/prepare",
            json={"simulation_id": simulation_id},
            timeout=self.timeout
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise SimulationRunnerError(f"Simulation prepare failed: {body.get('error')}")
        return body["data"]

    def _start_simulation(self, simulation_id: str, max_rounds: int = 5) -> dict:
        resp = requests.post(
            f"{self.api_base}/api/simulation/start",
            json={
                "simulation_id": simulation_id,
                "platform": "parallel",
                "max_rounds": max_rounds,
                "enable_graph_memory_update": True,
            },
            timeout=self.timeout
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise SimulationRunnerError(f"Simulation start failed: {body.get('error')}")
        return body["data"]

    def _generate_report(self, simulation_id: str) -> dict:
        resp = requests.post(
            f"{self.api_base}/api/report/generate",
            json={"simulation_id": simulation_id},
            timeout=self.timeout
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success"):
            raise SimulationRunnerError(f"Report generation failed: {body.get('error')}")
        return body["data"]

    def _download_report(self, report_id: str, save_path: str):
        resp = requests.get(
            f"{self.api_base}/api/report/{report_id}/download",
            timeout=self.timeout
        )
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(resp.content)

    # ---- Polling ----

    def _poll_task(self, task_id: str, label: str):
        """Poll /api/graph/task/{task_id} until completed or failed."""
        start = time.time()
        while time.time() - start < self.max_poll_time:
            try:
                resp = requests.get(
                    f"{self.api_base}/api/graph/task/{task_id}",
                    timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})
                status = data.get("status", "unknown")
                progress = data.get("progress", 0)
                logger.info(f"  [{label}] status={status} progress={progress}%")

                if status == "completed":
                    return data
                if status == "failed":
                    raise SimulationRunnerError(f"{label} failed: {data.get('error', 'unknown')}")
            except requests.RequestException as e:
                logger.warning(f"  [{label}] poll error: {e}")

            time.sleep(self.poll_interval)

        raise SimulationRunnerError(f"{label} timed out after {self.max_poll_time}s")

    def _poll_simulation(self, simulation_id: str):
        """Poll /api/simulation/{id}/run-status until completed."""
        start = time.time()
        while time.time() - start < self.max_poll_time:
            try:
                resp = requests.get(
                    f"{self.api_base}/api/simulation/{simulation_id}/run-status",
                    timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})
                status = data.get("runner_status", "unknown")
                progress = data.get("progress_percent", 0)
                actions = data.get("total_actions_count", 0)
                logger.info(f"  [Simulation] status={status} progress={progress:.1f}% actions={actions}")

                if status in ("completed", "stopped", "idle"):
                    return data
                if status == "failed":
                    raise SimulationRunnerError(f"Simulation failed")
            except requests.RequestException as e:
                logger.warning(f"  [Simulation] poll error: {e}")

            time.sleep(self.poll_interval)

        raise SimulationRunnerError(f"Simulation timed out after {self.max_poll_time}s")

    def _poll_report(self, task_id: str, simulation_id: str):
        """Poll report generation status."""
        start = time.time()
        while time.time() - start < self.max_poll_time:
            try:
                resp = requests.post(
                    f"{self.api_base}/api/report/generate/status",
                    json={"task_id": task_id, "simulation_id": simulation_id},
                    timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})
                status = data.get("status", "unknown")
                progress = data.get("progress", 0)
                logger.info(f"  [Report] status={status} progress={progress}%")

                if status == "completed" or data.get("already_completed"):
                    return data
                if status == "failed":
                    raise SimulationRunnerError(f"Report generation failed: {data.get('error')}")
            except requests.RequestException as e:
                logger.warning(f"  [Report] poll error: {e}")

            time.sleep(self.poll_interval)

        raise SimulationRunnerError(f"Report generation timed out after {self.max_poll_time}s")
