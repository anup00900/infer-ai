import json
import os
import pytest
from unittest.mock import patch, MagicMock
from forward_testing.pipeline import Pipeline
from forward_testing.config import ForwardTestingConfig


@pytest.fixture
def pipeline_env(tmp_path):
    config = ForwardTestingConfig()
    config.results_dir = str(tmp_path / "results")
    config.seeds_dir = str(tmp_path / "seeds")
    os.makedirs(config.results_dir)
    os.makedirs(config.seeds_dir)
    # Create a dummy live seed
    live = os.path.join(config.seeds_dir, "financial_seed_live.md")
    with open(live, "w") as f:
        f.write("# Test seed\n\n## Section 1\n\nContent.\n")
    return config


def test_checkpoint_save_load(pipeline_env):
    pipe = Pipeline(pipeline_env)
    day_dir = os.path.join(pipeline_env.results_dir, "2026-03-29")
    os.makedirs(day_dir)
    pipe._save_checkpoint(day_dir, "fetch_news", "completed")
    cp = pipe._load_checkpoint(day_dir)
    assert cp["fetch_news"] == "completed"


def test_checkpoint_resume(pipeline_env):
    pipe = Pipeline(pipeline_env)
    day_dir = os.path.join(pipeline_env.results_dir, "2026-03-29")
    os.makedirs(day_dir)
    pipe._save_checkpoint(day_dir, "fetch_prices", "completed")
    pipe._save_checkpoint(day_dir, "fetch_news", "completed")
    cp = pipe._load_checkpoint(day_dir)
    assert cp["fetch_prices"] == "completed"
    assert cp["fetch_news"] == "completed"


def test_empty_checkpoint(pipeline_env):
    pipe = Pipeline(pipeline_env)
    day_dir = os.path.join(pipeline_env.results_dir, "2026-03-29")
    os.makedirs(day_dir)
    cp = pipe._load_checkpoint(day_dir)
    assert cp == {}
