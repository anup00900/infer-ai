"""Creates and manages macOS launchd plist files for automated daily pipeline runs."""
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

PLIST_DIR = os.path.expanduser("~/Library/LaunchAgents")
PLIST_PREFIX = "com.infer.forward-testing"

# Three jobs:
# 1. fetch-prices at 6:00 PM (18:00) — market close data + score matured predictions
# 2. fetch-news at 11:00 PM (23:00) — aggregate all news sources
# 3. run-simulations at 11:30 PM (23:30) — run T+1, T+3, T+7 simulations

JOBS = {
    "fetch-prices": {
        "hour": 18,
        "minute": 0,
        "cli_command": "run-pipeline",
        "cli_args": ["--phase", "prices"],
        "label": f"{PLIST_PREFIX}.fetch-prices",
    },
    "fetch-news": {
        "hour": 23,
        "minute": 0,
        "cli_command": "run-pipeline",
        "cli_args": ["--phase", "news"],
        "label": f"{PLIST_PREFIX}.fetch-news",
    },
    "run-simulations": {
        "hour": 23,
        "minute": 30,
        "cli_command": "run-pipeline",
        "cli_args": ["--phase", "simulations"],
        "label": f"{PLIST_PREFIX}.run-simulations",
    },
}


def _generate_plist(job_name: str, job_config: dict, python_path: str, project_dir: str) -> str:
    """Generate a launchd plist XML string."""
    label = job_config["label"]
    hour = job_config["hour"]
    minute = job_config["minute"]
    cli_args = job_config["cli_args"]

    log_dir = os.path.join(project_dir, "backend", "forward_testing", "logs")
    os.makedirs(log_dir, exist_ok=True)

    args_xml = "\n".join(f"        <string>{a}</string>" for a in cli_args)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>forward_testing.cli</string>
        <string>{job_config['cli_command']}</string>
{args_xml}
    </array>

    <key>WorkingDirectory</key>
    <string>{os.path.join(project_dir, 'backend')}</string>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>{os.path.join(log_dir, f'{job_name}.stdout.log')}</string>

    <key>StandardErrorPath</key>
    <string>{os.path.join(log_dir, f'{job_name}.stderr.log')}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:{os.path.dirname(python_path)}</string>
        <key>PYTHONPATH</key>
        <string>{os.path.join(project_dir, 'backend')}</string>
    </dict>

    <key>RunAtLoad</key>
    <false/>

    <key>Nice</key>
    <integer>10</integer>
</dict>
</plist>"""


def install_cron(project_dir: str = None):
    """Install all launchd plist files and load them."""
    if project_dir is None:
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    python_path = sys.executable
    os.makedirs(PLIST_DIR, exist_ok=True)

    for job_name, job_config in JOBS.items():
        plist_content = _generate_plist(job_name, job_config, python_path, project_dir)
        plist_path = os.path.join(PLIST_DIR, f"{job_config['label']}.plist")

        # Unload if already loaded
        try:
            subprocess.run(["launchctl", "unload", plist_path],
                         capture_output=True, timeout=10)
        except Exception:
            pass

        # Write plist
        with open(plist_path, "w") as f:
            f.write(plist_content)

        # Load
        result = subprocess.run(
            ["launchctl", "load", plist_path],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            logger.info(f"  Installed and loaded: {job_name} (at {job_config['hour']:02d}:{job_config['minute']:02d})")
        else:
            logger.warning(f"  Failed to load {job_name}: {result.stderr}")

    logger.info(f"All {len(JOBS)} cron jobs installed.")
    logger.info("Schedule:")
    logger.info("  6:00 PM  — Fetch market close prices + score matured predictions")
    logger.info("  11:00 PM — Fetch news from all sources + augment seed file")
    logger.info("  11:30 PM — Run T+1, T+3, T+7 simulations")


def uninstall_cron():
    """Unload and remove all launchd plist files."""
    for job_name, job_config in JOBS.items():
        plist_path = os.path.join(PLIST_DIR, f"{job_config['label']}.plist")

        if os.path.exists(plist_path):
            try:
                subprocess.run(["launchctl", "unload", plist_path],
                             capture_output=True, timeout=10)
            except Exception:
                pass
            os.remove(plist_path)
            logger.info(f"  Removed: {job_name}")
        else:
            logger.info(f"  Not found: {job_name}")

    logger.info("All cron jobs removed.")


def list_cron() -> list:
    """List all installed forward-testing cron jobs."""
    installed = []
    for job_name, job_config in JOBS.items():
        plist_path = os.path.join(PLIST_DIR, f"{job_config['label']}.plist")
        status = "installed" if os.path.exists(plist_path) else "not installed"

        # Check if loaded
        if status == "installed":
            try:
                result = subprocess.run(
                    ["launchctl", "list", job_config["label"]],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    status = "active"
            except Exception:
                pass

        installed.append({
            "name": job_name,
            "label": job_config["label"],
            "schedule": f"{job_config['hour']:02d}:{job_config['minute']:02d}",
            "status": status,
        })

    return installed
