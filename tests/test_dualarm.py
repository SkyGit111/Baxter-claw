"""Unit tests for dual-arm coordination primitives."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bridge.primitives import BaxterPrimitives
from bridge.drivers.mock_driver import MockDriver
from bridge.safety import SafetyValidator


@pytest.fixture
def primitives():
    """Create primitives instance with mock driver."""
    driver = MockDriver()
    driver.connect()
    driver.enable()

    safety = SafetyValidator()
    return BaxterPrimitives(driver, safety)


def test_bimanual_pick_success(primitives):
    """Test successful bimanual pick operation."""
    object_position = [0.65, 0.0, 0.1]
    result = primitives.bimanual_pick(object_position)

    assert result['success'] is True
    assert 'both arms' in result['message'].lower()
    assert 'left_position' in result
    assert 'right_position' in result


def test_bimanual_pick_collision_detection(primitives):
    """Test that collision detection prevents unsafe bimanual pick."""
    # Positions too close together
    object_position = [0.6, 0.0, 0.1]
    result = primitives.bimanual_pick(
        object_position,
        left_offset=[0.02, 0.0, 0.0],
        right_offset=[-0.02, 0.0, 0.0]
    )

    assert result['success'] is False
    assert 'collide' in result['message'].lower()


def test_handover_success(primitives):
    """Test successful handover operation."""
    result = primitives.handover(
        from_arm='right',
        to_arm='left',
        handover_position=[0.6, 0.0, 0.3]
    )

    assert result['success'] is True
    assert 'handed over' in result['message'].lower()
    assert result.get('handover_position') is not None


def test_handover_same_arm(primitives):
    """Test that handover to same arm is rejected."""
    result = primitives.handover(
        from_arm='right',
        to_arm='right'
    )

    assert result['success'] is False
    assert 'same arm' in result['message'].lower()


def test_handover_invalid_arm(primitives):
    """Test that invalid arm names are rejected."""
    result = primitives.handover(
        from_arm='invalid',
        to_arm='left'
    )

    assert result['success'] is False
    assert 'invalid' in result['message'].lower()


def test_synchronized_move_success(primitives):
    """Test successful synchronized move."""
    left_pos = [0.6, 0.3, 0.2]
    right_pos = [0.6, -0.3, 0.2]

    result = primitives.synchronized_move(left_pos, right_pos)

    assert result['success'] is True
    assert 'both arms' in result['message'].lower()
    assert result['left_position'] == left_pos
    assert result['right_position'] == right_pos


def test_synchronized_move_collision(primitives):
    """Test that collision detection prevents unsafe synchronized move."""
    # Same position for both arms
    position = [0.6, 0.0, 0.2]

    result = primitives.synchronized_move(position, position)

    assert result['success'] is False
    assert 'collide' in result['message'].lower()


def test_collision_check(primitives):
    """Test collision detection function."""
    # Safe distance
    assert primitives._check_arm_collision([0.6, 0.3, 0.2], [0.6, -0.3, 0.2]) is True

    # Too close
    assert primitives._check_arm_collision([0.6, 0.0, 0.2], [0.6, 0.05, 0.2]) is False

    # Same position
    assert primitives._check_arm_collision([0.6, 0.0, 0.2], [0.6, 0.0, 0.2]) is False


def test_bimanual_pick_invalid_position(primitives):
    """Test that invalid position format is rejected."""
    result = primitives.bimanual_pick([0.6, 0.2])  # Missing z

    assert result['success'] is False
    assert 'must be' in result['message'].lower()


def test_synchronized_move_invalid_position(primitives):
    """Test that invalid position format is rejected."""
    result = primitives.synchronized_move([0.6, 0.3], [0.6, -0.3, 0.2])

    assert result['success'] is False
    assert 'must be' in result['message'].lower()
