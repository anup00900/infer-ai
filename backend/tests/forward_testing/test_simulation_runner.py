import pytest
from unittest.mock import patch, MagicMock
from forward_testing.runner.simulation_runner import SimulationRunner, SimulationRunnerError


def test_check_health_success():
    runner = SimulationRunner()
    with patch("forward_testing.runner.simulation_runner.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        assert runner.check_health() is True


def test_check_health_failure():
    runner = SimulationRunner()
    with patch("forward_testing.runner.simulation_runner.requests.get") as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        assert runner.check_health() is False


def test_generate_ontology():
    runner = SimulationRunner()
    with patch("forward_testing.runner.simulation_runner.requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True, "data": {"project_id": "proj_123"}}
        )
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test content")
            temp_path = f.name
        try:
            result = runner._generate_ontology(temp_path, "test requirement", "test")
            assert result["project_id"] == "proj_123"
        finally:
            os.unlink(temp_path)


def test_generate_ontology_failure():
    runner = SimulationRunner()
    with patch("forward_testing.runner.simulation_runner.requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": False, "error": "Bad input"}
        )
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test")
            temp_path = f.name
        try:
            with pytest.raises(SimulationRunnerError, match="Bad input"):
                runner._generate_ontology(temp_path, "test", "test")
        finally:
            os.unlink(temp_path)
