import os
import pytest
from forward_testing.automation.launchd_setup import _generate_plist, JOBS, list_cron


def test_generate_plist_valid_xml():
    job_config = JOBS["fetch-prices"]
    plist = _generate_plist("fetch-prices", job_config, "/usr/bin/python3", "/tmp/project")
    assert "<?xml version" in plist
    assert "com.infer.forward-testing.fetch-prices" in plist
    assert "<integer>18</integer>" in plist
    assert "<integer>0</integer>" in plist
    assert "/usr/bin/python3" in plist


def test_generate_plist_news_schedule():
    job_config = JOBS["fetch-news"]
    plist = _generate_plist("fetch-news", job_config, "/usr/bin/python3", "/tmp/project")
    assert "<integer>23</integer>" in plist
    assert "forward_testing.cli" in plist


def test_generate_plist_simulations_schedule():
    job_config = JOBS["run-simulations"]
    plist = _generate_plist("run-simulations", job_config, "/usr/bin/python3", "/tmp/project")
    assert "<integer>23</integer>" in plist
    assert "<integer>30</integer>" in plist


def test_all_three_jobs_defined():
    assert "fetch-prices" in JOBS
    assert "fetch-news" in JOBS
    assert "run-simulations" in JOBS
    assert len(JOBS) == 3


def test_list_cron_returns_list():
    result = list_cron()
    assert isinstance(result, list)
    assert len(result) == 3
    names = [r["name"] for r in result]
    assert "fetch-prices" in names
    assert "fetch-news" in names
    assert "run-simulations" in names
