"""Unit tests for primitives."""

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


def test_pick_success(primitives):
    """Test successful pick operation."""
    position = [0.6, 0.2, 0.1]
    result = primitives.pick('right', position)

    assert result['success'] is True
    assert 'Successfully picked' in result['message']
    assert result['arm'] == 'right'


def test_pick_invalid_position_length(primitives):
    """Test that invalid position length is caught."""
    position = [0.6, 0.2]  # Missing z
    result = primitives.pick('right', position)

    assert result['success'] is False
    assert 'must be [x, y, z]' in result['message']


def test_pick_outside_workspace(primitives):
    """Test that pick outside workspace is rejected."""
    position = [2.0, 0.0, 0.0]  # Too far
    result = primitives.pick('right', position)

    assert result['success'] is False
    assert 'unsafe' in result['message'].lower()


def test_place_success(primitives):
    """Test successful place operation."""
    position = [0.5, -0.3, 0.15]
    result = primitives.place('right', position)

    assert result['success'] is True
    assert 'Successfully placed' in result['message']


def test_place_invalid_position(primitives):
    """Test that invalid position is caught."""
    position = [0.5]  # Too short
    result = primitives.place('right', position)

    assert result['success'] is False


def test_move_to_success(primitives):
    """Test successful move_to operation."""
    position = [0.6, 0.0, 0.3]
    result = primitives.move_to('right', position)

    assert result['success'] is True
    assert 'Successfully moved' in result['message']


def test_move_to_with_orientation(primitives):
    """Test move_to with explicit orientation."""
    position = [0.6, 0.0, 0.3]
    orientation = [0.0, 0.0, 1.57]  # 90 degree yaw
    result = primitives.move_to('right', position, orientation)

    assert result['success'] is True


def test_move_to_invalid_orientation(primitives):
    """Test that invalid orientation is caught."""
    position = [0.6, 0.0, 0.3]
    orientation = [0.0, 0.0]  # Too short
    result = primitives.move_to('right', position, orientation)

    assert result['success'] is False
    assert 'Orientation must be' in result['message']


def test_home_success(primitives):
    """Test successful home operation."""
    result = primitives.home('right')

    assert result['success'] is True
    assert 'returned to home' in result['message'].lower()
    assert result['arm'] == 'right'


def test_home_invalid_arm(primitives):
    """Test that invalid arm is caught."""
    result = primitives.home('invalid')

    assert result['success'] is False
    assert 'Unknown arm' in result['message']


def test_pick_place_sequence(primitives):
    """Test complete pick and place sequence."""
    # Pick
    pick_pos = [0.6, 0.2, 0.1]
    result = primitives.pick('right', pick_pos)
    assert result['success'] is True

    # Place
    place_pos = [0.5, -0.3, 0.15]
    result = primitives.place('right', place_pos)
    assert result['success'] is True

    # Home
    result = primitives.home('right')
    assert result['success'] is True


def test_custom_approach_height(primitives):
    """Test pick with custom approach height."""
    position = [0.6, 0.2, 0.1]
    result = primitives.pick('right', position, approach_height=0.15)

    assert result['success'] is True
