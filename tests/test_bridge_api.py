"""Unit tests for bridge API endpoints."""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bridge.server import app
from bridge.arm_manager import ArmManager


@pytest.fixture
def client():
    """Create test client with mock driver."""
    # Initialize manager with mock driver
    from bridge.server import manager
    import bridge.server as server_module

    # Create manager with mock config
    test_manager = ArmManager()
    test_manager.config = {'driver': {'type': 'mock'}}
    test_manager.driver = test_manager._create_driver()
    test_manager.safety = test_manager.safety
    test_manager.primitives.driver = test_manager.driver

    # Replace global manager
    server_module.manager = test_manager

    # Connect and enable
    test_manager.connect()
    test_manager.enable()

    return TestClient(app)


def test_root(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Baxter-Claw Bridge"
    assert data["version"] == "0.1.0"


def test_health(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "healthy" in data
    assert "connected" in data


def test_enable(client):
    """Test enable endpoint."""
    response = client.post("/enable")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_status(client):
    """Test status endpoint."""
    response = client.get("/status?arm=right")
    assert response.status_code == 200
    data = response.json()
    assert "connected" in data
    assert "enabled" in data
    assert "joint_angles" in data
    assert "endpoint_pose" in data


def test_pick_primitive(client):
    """Test pick primitive endpoint."""
    response = client.post(
        "/primitives/pick",
        json={
            "arm": "right",
            "position": [0.6, 0.2, 0.1],
            "approach_height": 0.1
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data


def test_place_primitive(client):
    """Test place primitive endpoint."""
    response = client.post(
        "/primitives/place",
        json={
            "arm": "right",
            "position": [0.5, -0.3, 0.15],
            "approach_height": 0.1
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_move_to_primitive(client):
    """Test move_to primitive endpoint."""
    response = client.post(
        "/primitives/move_to",
        json={
            "arm": "right",
            "position": [0.6, 0.0, 0.3],
            "orientation": None
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_home_primitive(client):
    """Test home primitive endpoint."""
    response = client.post(
        "/primitives/home",
        json={"arm": "right"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_invalid_position(client):
    """Test that invalid positions are rejected."""
    response = client.post(
        "/primitives/pick",
        json={
            "arm": "right",
            "position": [0.6, 0.2],  # Missing z coordinate
        }
    )
    assert response.status_code == 422  # Validation error


def test_gripper_control(client):
    """Test gripper control endpoint."""
    response = client.post(
        "/gripper",
        json={
            "arm": "right",
            "action": "open"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_emergency_stop(client):
    """Test emergency stop endpoint."""
    response = client.post("/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
