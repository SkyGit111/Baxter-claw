"""Unit tests for mock driver."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bridge.drivers.mock_driver import MockDriver


@pytest.fixture
def driver():
    """Create mock driver instance."""
    return MockDriver()


def test_connect(driver):
    """Test connection."""
    assert driver.connect() is True
    assert driver._connected is True


def test_enable(driver):
    """Test enabling robot."""
    driver.connect()
    assert driver.enable() is True
    assert driver.is_enabled() is True


def test_enable_without_connect(driver):
    """Test that enable fails without connection."""
    assert driver.enable() is False


def test_disable(driver):
    """Test disabling robot."""
    driver.connect()
    driver.enable()
    assert driver.disable() is True
    assert driver.is_enabled() is False


def test_move_to_joint_positions(driver):
    """Test joint space motion."""
    driver.connect()
    driver.enable()

    positions = {
        'right_s0': 0.5,
        'right_s1': -0.5,
        'right_e0': 0.0,
        'right_e1': 1.0,
        'right_w0': 0.0,
        'right_w1': 1.5,
        'right_w2': 0.0,
    }

    assert driver.move_to_joint_positions('right', positions) is True

    # Verify state updated
    current = driver.get_joint_angles('right')
    assert current['right_s0'] == 0.5


def test_move_to_pose(driver):
    """Test Cartesian motion."""
    driver.connect()
    driver.enable()

    pose = [0.6, -0.3, 0.2, 0.0, 0.0, 0.0]
    assert driver.move_to_pose('right', pose) is True

    # Verify pose updated
    current_pose = driver.get_endpoint_pose('right')
    assert current_pose[0] == 0.6
    assert current_pose[1] == -0.3


def test_gripper_open(driver):
    """Test gripper open."""
    driver.connect()
    driver.enable()

    assert driver.gripper_command('right', 'open') is True

    position, force = driver.get_gripper_state('right')
    assert position == 100.0  # Fully open
    assert force == 0.0


def test_gripper_close(driver):
    """Test gripper close."""
    driver.connect()
    driver.enable()

    assert driver.gripper_command('right', 'close', force=30.0) is True

    position, force = driver.get_gripper_state('right')
    assert position == 0.0  # Fully closed
    assert force == 30.0


def test_emergency_stop(driver):
    """Test emergency stop."""
    driver.connect()
    driver.enable()

    assert driver.emergency_stop() is True
    assert driver.is_enabled() is False


def test_invalid_arm(driver):
    """Test that invalid arm names are handled."""
    driver.connect()
    driver.enable()

    assert driver.move_to_joint_positions('invalid', {}) is False
