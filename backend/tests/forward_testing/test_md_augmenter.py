import os
import pytest
from forward_testing.augmenter.md_augmenter import MDAugmenter
from forward_testing.config import ForwardTestingConfig


@pytest.fixture
def tmp_env(tmp_path):
    seeds_dir = tmp_path / "seeds"
    seeds_dir.mkdir()
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    seed = seeds_dir / "financial_seed_live.md"
    seed.write_text(
        "# Financial Intelligence Report\n\n"
        "**Tickers covered:** NVDA · AAPL\n\n---\n\n"
        "## Section 1 — Macro Environment\n\nSome macro content.\n\n---\n\n"
        "## Section 2 — Ticker Deep Dives\n\n### NVDA\n\nNVDA content.\n"
    )

    config = ForwardTestingConfig()
    config.seeds_dir = str(seeds_dir)
    config.results_dir = str(results_dir)
    return config, str(seed)


def test_append_daily_section(tmp_env):
    config, seed_path = tmp_env
    augmenter = MDAugmenter(config)
    daily_md = "\n## Daily Update — March 29, 2026\n\nSome daily news.\n\n---\n"
    augmenter.append_daily(daily_md, "2026-03-29")
    content = open(os.path.join(config.seeds_dir, "financial_seed_live.md")).read()
    assert "Daily Update — March 29, 2026" in content


def test_append_saves_independent_copy(tmp_env):
    config, seed_path = tmp_env
    augmenter = MDAugmenter(config)
    daily_md = "\n## Daily Update — March 29, 2026\n\nSome news.\n\n---\n"
    augmenter.append_daily(daily_md, "2026-03-29")
    copy_path = os.path.join(config.results_dir, "2026-03-29", "augmented_section.md")
    assert os.path.exists(copy_path)
    assert "Daily Update" in open(copy_path).read()


def test_get_windowed_view(tmp_env):
    config, seed_path = tmp_env
    augmenter = MDAugmenter(config)
    for day in range(20, 30):
        daily_md = f"\n## Daily Update — March {day}, 2026\n\nNews for day {day}.\n\n---\n"
        augmenter.append_daily(daily_md, f"2026-03-{day}")
    windowed = augmenter.get_windowed_view(window_days=7)
    assert "Section 1 — Macro Environment" in windowed
    assert "Daily Update — March 29, 2026" in windowed
    assert "Daily Update — March 23, 2026" in windowed
    assert "Daily Update — March 20, 2026" not in windowed


def test_backup_created(tmp_env):
    config, seed_path = tmp_env
    augmenter = MDAugmenter(config)
    daily_md = "\n## Daily Update — March 29, 2026\n\nNews.\n\n---\n"
    augmenter.append_daily(daily_md, "2026-03-29")
    backup_dir = os.path.join(config.seeds_dir, "backups")
    assert os.path.exists(backup_dir)
    backups = os.listdir(backup_dir)
    assert len(backups) >= 1
