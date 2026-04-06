"""Unit tests for safety validator."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bridge.safety import SafetyValidator


@pytest.fixture
def validator():
    """Create safety validator instance."""
    return SafetyValidator()


def test_joint_limits_valid(validator):
    """Test that valid joint positions pass."""
    positions = {
        'right_s0': 0.0,
        'right_s1': -0.5,
        'right_e0': 0.0,
        'right_e1': 1.0,
        'right_w0': 0.0,
        'right_w1': 1.5,
        'right_w2': 0.0,
    }

    is_safe, msg = validator.check_joint_limits('right', positions)
    assert is_safe is True
    assert msg == ""


def test_joint_limits_exceed_max(validator):
    """Test that exceeding max limit is caught."""
    positions = {
        'right_s0': 2.0,  # Exceeds max of 1.701
    }

    is_safe, msg = validator.check_joint_limits('right', positions)
    assert is_safe is False
    assert "right_s0" in msg
    assert "outside limits" in msg


def test_joint_limits_exceed_min(validator):
    """Test that exceeding min limit is caught."""
    positions = {
        'right_e1': -0.1,  # Below min of -0.05
    }

    is_safe, msg = validator.check_joint_limits('right', positions)
    assert is_safe is False
    assert "right_e1" in msg


def test_workspace_valid(validator):
    """Test that valid workspace positions pass."""
    pose = [0.6, 0.0, 0.2, 0.0, 0.0, 0.0]

    is_safe, msg = validator.check_workspace('right', pose)
    assert is_safe is True
    assert msg == ""


def test_workspace_x_too_far(validator):
    """Test that x position too far is caught."""
    pose = [1.5, 0.0, 0.2, 0.0, 0.0, 0.0]  # x exceeds 0.9

    is_safe, msg = validator.check_workspace('right', pose)
    assert is_safe is False
    assert "X position" in msg


def test_workspace_x_too_close(validator):
    """Test that x position too close is caught."""
    pose = [0.1, 0.0, 0.2, 0.0, 0.0, 0.0]  # x below 0.3

    is_safe, msg = validator.check_workspace('right', pose)
    assert is_safe is False
    assert "X position" in msg


def test_workspace_y_out_of_bounds(validator):
    """Test that y position out of bounds is caught."""
    pose = [0.6, 1.0, 0.2, 0.0, 0.0, 0.0]  # y exceeds 0.7

    is_safe, msg = validator.check_workspace('right', pose)
    assert is_safe is False
    assert "Y position" in msg


def test_workspace_z_too_low(validator):
    """Test that z position too low is caught."""
    pose = [0.6, 0.0, -0.5, 0.0, 0.0, 0.0]  # z below -0.2

    is_safe, msg = validator.check_workspace('right', pose)
    assert is_safe is False
    assert "Z position" in msg


def test_workspace_z_too_high(validator):
    """Test that z position too high is caught."""
    pose = [0.6, 0.0, 1.0, 0.0, 0.0, 0.0]  # z exceeds 0.5

    is_safe, msg = validator.check_workspace('right', pose)
    assert is_safe is False
    assert "Z position" in msg


def test_speed_valid(validator):
    """Test that valid speed passes."""
    is_safe, msg = validator.check_speed(0.3)
    assert is_safe is True


def test_speed_too_high(validator):
    """Test that excessive speed is caught."""
    is_safe, msg = validator.check_speed(0.8)  # Exceeds max of 0.5
    assert is_safe is False
    assert "Speed" in msg


def test_speed_negative(validator):
    """Test that negative speed is caught."""
    is_safe, msg = validator.check_speed(-0.1)
    assert is_safe is False


def test_validate_motion_joint(validator):
    """Test comprehensive joint motion validation."""
    positions = {
        'right_s0': 0.0,
        'right_s1': -0.5,
        'right_e0': 0.0,
        'right_e1': 1.0,
        'right_w0': 0.0,
        'right_w1': 1.5,
        'right_w2': 0.0,
    }

    is_safe, msg = validator.validate_motion('right', 'joint', positions, speed=0.3)
    assert is_safe is True


def test_validate_motion_pose(validator):
    """Test comprehensive pose motion validation."""
    pose = [0.6, 0.0, 0.2, 0.0, 0.0, 0.0]

    is_safe, msg = validator.validate_motion('right', 'pose', pose, speed=0.3)
    assert is_safe is True


def test_validate_motion_invalid_type(validator):
    """Test that invalid motion type is caught."""
    is_safe, msg = validator.validate_motion('right', 'invalid', [], speed=0.3)
    assert is_safe is False
    assert "Unknown target type" in msg
