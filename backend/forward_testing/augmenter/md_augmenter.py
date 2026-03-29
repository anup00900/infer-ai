import os
import shutil

LIVE_FILENAME = "financial_seed_live.md"


class MDAugmenter:
    def __init__(self, config):
        self.config = config
        self.live_path = os.path.join(config.seeds_dir, LIVE_FILENAME)
        os.makedirs(config.seeds_dir, exist_ok=True)

    def initialize_from_original(self, original_path: str) -> str:
        if not os.path.exists(self.live_path):
            shutil.copy2(original_path, self.live_path)
        return self.live_path

    def append_daily(self, daily_md: str, date_str: str) -> None:
        self._backup(date_str)

        with open(self.live_path, "a", encoding="utf-8") as f:
            f.write(daily_md)

        results_date_dir = os.path.join(self.config.results_dir, date_str)
        os.makedirs(results_date_dir, exist_ok=True)
        copy_path = os.path.join(results_date_dir, "augmented_section.md")
        with open(copy_path, "w", encoding="utf-8") as f:
            f.write(daily_md)

    def get_windowed_view(self, window_days: int = 7) -> str:
        content = self.get_full_content()
        parts = content.split("\n## Daily Update")
        base_content = parts[0]
        daily_updates = ["\n## Daily Update" + p for p in parts[1:]]
        windowed_updates = daily_updates[-window_days:]
        return base_content + "".join(windowed_updates)

    def get_full_content(self) -> str:
        with open(self.live_path, "r", encoding="utf-8") as f:
            return f.read()

    def _backup(self, date_str: str) -> None:
        backup_dir = os.path.join(self.config.seeds_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"seed_before_{date_str}.md")
        shutil.copy2(self.live_path, backup_path)
