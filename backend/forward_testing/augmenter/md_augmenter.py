import os
import re
import shutil

LIVE_FILENAME = "financial_seed_live.md"

# Max size for windowed view sent to simulation (chars)
# Full articles stay in the live seed, but simulation gets condensed version
MAX_WINDOWED_SIZE = 150_000  # ~150KB = ~300 chunks, manageable for graph builder


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
        """Return base + last N daily updates, condensed for simulation input.

        Full articles stay in the live seed file. The windowed view sent to
        the simulation trims blockquoted article text to keep the total size
        manageable for the graph builder (~300 chunks instead of ~9000).
        """
        content = self.get_full_content()
        parts = content.split("\n## Daily Update")
        base_content = parts[0]
        daily_updates = ["\n## Daily Update" + p for p in parts[1:]]
        windowed_updates = daily_updates[-window_days:]

        # Condense: trim blockquoted full article text (lines starting with "  > ")
        # Keep first 2 lines of each blockquote, skip the rest
        condensed_updates = []
        for update in windowed_updates:
            condensed_updates.append(self._condense_update(update))

        result = base_content + "".join(condensed_updates)

        # Safety cap
        if len(result) > MAX_WINDOWED_SIZE:
            result = result[:MAX_WINDOWED_SIZE]

        return result

    def get_full_content(self) -> str:
        with open(self.live_path, "r", encoding="utf-8") as f:
            return f.read()

    def _condense_update(self, update: str) -> str:
        """Keep headlines and tables, trim blockquoted article bodies."""
        lines = update.split("\n")
        condensed = []
        in_blockquote = False
        quote_lines = 0

        for line in lines:
            if line.strip().startswith("> "):
                if not in_blockquote:
                    in_blockquote = True
                    quote_lines = 0
                quote_lines += 1
                # Keep first 3 lines of each blockquote (enough context)
                if quote_lines <= 3:
                    condensed.append(line)
            else:
                in_blockquote = False
                quote_lines = 0
                condensed.append(line)

        return "\n".join(condensed)

    def _backup(self, date_str: str) -> None:
        backup_dir = os.path.join(self.config.seeds_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"seed_before_{date_str}.md")
        shutil.copy2(self.live_path, backup_path)
