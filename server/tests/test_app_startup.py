"""
Tests for FastAPI app startup, lifespan model loading, and /api/health endpoint.

Covers:
- Model artifact loaded at startup when file exists
- Graceful degradation when artifact file is absent
- /api/health response structure per D-16
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def mock_artifact_dict():
    """Return a minimal artifact dict suitable for FastAPI app.state."""
    return {
        "model": MagicMock(),
        "calibrator": MagicMock(),
        "feature_columns": ["stat_type", "pts_avg_L5"],
        "categorical_features": ["stat_type"],
        "metrics": {"calibration_method": "isotonic"},
        "metadata": {"version": "2.0"},
    }


@pytest.fixture
def client_with_artifact(tmp_path):
    """TestClient where MODEL_ARTIFACT_PATH exists and load_artifact succeeds."""
    artifact_path = tmp_path / "model.joblib"
    artifact_path.write_bytes(b"fake artifact")

    with patch("server.core.config.MODEL_ARTIFACT_PATH", str(artifact_path)):
        with patch("server.pipeline.artifact.MODEL_ARTIFACT_PATH", str(artifact_path)):
            with patch("server.pipeline.artifact.load_artifact", return_value=mock_artifact_dict()):
                with patch("server.pipeline.train_config.MODEL_ARTIFACT_PATH", str(artifact_path)):
                    from server.app import app

                    with TestClient(app) as client:
                        yield client


@pytest.fixture
def client_no_artifact(tmp_path):
    """TestClient where MODEL_ARTIFACT_PATH does not exist."""
    nonexistent = tmp_path / "does_not_exist.joblib"

    with patch("server.core.config.MODEL_ARTIFACT_PATH", str(nonexistent)):
        with patch("server.pipeline.artifact.MODEL_ARTIFACT_PATH", str(nonexistent)):
            with patch("server.pipeline.train_config.MODEL_ARTIFACT_PATH", str(nonexistent)):
                with patch("os.path.exists", return_value=False):
                    from server.app import app

                    with TestClient(app) as client:
                        yield client


@pytest.fixture
def client_artifact_load_error(tmp_path):
    """TestClient where load_artifact raises an exception."""
    bad_path = tmp_path / "bad_artifact.joblib"
    bad_path.write_bytes(b"corrupt")

    def raise_error(*args, **kwargs):
        raise OSError("Cannot load model")

    with patch("server.core.config.MODEL_ARTIFACT_PATH", str(bad_path)):
        with patch("server.pipeline.artifact.MODEL_ARTIFACT_PATH", str(bad_path)):
            with patch("server.pipeline.train_config.MODEL_ARTIFACT_PATH", str(bad_path)):
                with patch("os.path.exists", return_value=False):
                    with patch("server.pipeline.artifact.load_artifact", side_effect=raise_error):
                        from server.app import app

                        with TestClient(app) as client:
                            yield client


class TestHealthEndpoint:
    """Tests for /api/health endpoint per D-16."""

    def test_health_returns_correct_structure(self, client_with_artifact):
        """Health endpoint returns status, service, version, model_loaded."""
        response = client_with_artifact.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "HoopProphet API"
        assert data["version"] == "2.0.0"
        assert "model_loaded" in data

    def test_health_model_loaded_true_when_artifact_present(self, client_with_artifact):
        """model_loaded is True when artifact file exists and loads successfully."""
        response = client_with_artifact.get("/api/health")
        assert response.json()["model_loaded"] is True

    def test_health_model_loaded_false_when_artifact_absent(self, client_no_artifact):
        """model_loaded is False when artifact file doesn't exist."""
        response = client_no_artifact.get("/api/health")
        assert response.json()["model_loaded"] is False

    def test_health_model_loaded_false_when_load_fails(self, client_artifact_load_error):
        """model_loaded is False when artifact load raises an exception."""
        response = client_artifact_load_error.get("/api/health")
        assert response.json()["model_loaded"] is False


class TestLifespan:
    """Tests for lifespan model loading behavior."""

    def test_artifact_loaded_into_app_state_when_present(self, client_with_artifact):
        """app.state.model_artifact is set when artifact file exists."""
        response = client_with_artifact.get("/api/health")
        assert response.json()["model_loaded"] is True

    def test_app_state_none_when_artifact_absent(self, client_no_artifact):
        """app.state.model_artifact is None when artifact file is absent."""
        response = client_no_artifact.get("/api/health")
        assert response.json()["model_loaded"] is False

    def test_health_still_serves_when_artifact_load_fails(self, client_artifact_load_error):
        """API still responds even when artifact loading fails (graceful degradation)."""
        response = client_artifact_load_error.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
