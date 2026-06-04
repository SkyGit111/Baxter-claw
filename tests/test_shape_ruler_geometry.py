#!/usr/bin/env python
"""Unit tests for shape ruler geometry helpers."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from bridge.primitives import BaxterPrimitives


def test_distance_xy():
    """Test XY distance calculation."""
    print("\n" + "="*70)
    print("TEST: distance_xy")
    print("="*70)

    class MockDriver:
        pass
    class MockSafety:
        pass

    primitives = BaxterPrimitives(MockDriver(), MockSafety())

    # Test 1: Simple distance
    print("\nTest 1: Distance between [0, 0, 0] and [3, 4, 0]")
    dist = primitives.distance_xy([0, 0, 0], [3, 4, 0])
    print(f"  Result: {dist:.3f}")
    print(f"  Expected: 5.000")
    assert abs(dist - 5.0) < 0.01, f"Expected 5.0, got {dist}"
    print("  ✓ PASS")

    # Test 2: Z coordinate should be ignored
    print("\nTest 2: Distance ignores Z coordinate")
    dist = primitives.distance_xy([0, 0, 10], [3, 4, -10])
    print(f"  Result: {dist:.3f}")
    print(f"  Expected: 5.000")
    assert abs(dist - 5.0) < 0.01, f"Expected 5.0, got {dist}"
    print("  ✓ PASS")

    print("\n" + "="*70)
    print("✓ All distance_xy tests PASSED")
    print("="*70)


def test_rotate_vector_2d():
    """Test 2D vector rotation."""
    print("\n" + "="*70)
    print("TEST: rotate_vector_2d")
    print("="*70)

    class MockDriver:
        pass
    class MockSafety:
        pass

    primitives = BaxterPrimitives(MockDriver(), MockSafety())

    # Test 1: 90° counterclockwise
    print("\nTest 1: Rotate [1, 0] by 90° counterclockwise")
    vec = [1.0, 0.0]
    result = primitives.rotate_vector_2d(vec, np.pi/2)
    print(f"  Input: {vec}")
    print(f"  Result: [{result[0]:.3f}, {result[1]:.3f}]")
    print(f"  Expected: [0, 1]")
    assert abs(result[0]) < 0.01 and abs(result[1] - 1.0) < 0.01
    print("  ✓ PASS")

    # Test 2: 90° clockwise
    print("\nTest 2: Rotate [1, 0] by 90° clockwise")
    result = primitives.rotate_vector_2d(vec, -np.pi/2)
    print(f"  Result: [{result[0]:.3f}, {result[1]:.3f}]")
    print(f"  Expected: [0, -1]")
    assert abs(result[0]) < 0.01 and abs(result[1] + 1.0) < 0.01
    print("  ✓ PASS")

    print("\n" + "="*70)
    print("✓ All rotate_vector_2d tests PASSED")
    print("="*70)


def test_calculate_L_shape_target():
    """Test L-shape target calculation."""
    print("\n" + "="*70)
    print("TEST: calculate_two_link_target_L_shape")
    print("="*70)

    class MockDriver:
        pass
    class MockSafety:
        pass

    primitives = BaxterPrimitives(MockDriver(), MockSafety())

    # Test: Simple L-shape
    print("\nTest: Calculate L-shape target")
    motion_R = [0.5, 0.3, -0.16]
    motion_G = [0.6, 0.3, -0.16]
    motion_O = [0.7, 0.35, -0.16]
    motion_B = [0.8, 0.4, -0.16]

    result = primitives.calculate_two_link_target_L_shape(
        motion_R, motion_G, motion_O, motion_B,
        l_shape_blue_turn_direction="clockwise",
        red_yellow_target_angle_deg=165,
        red_yellow_bend_direction="clockwise",
        blue_yellow_target_angle_deg=90
    )

    print(f"  L1: {result['L1']:.3f}m")
    print(f"  L2: {result['L2']:.3f}m")
    print(f"  O_target: {result['O_target']}")
    print(f"  B_target: {result['B_target']}")

    # Check L1 and L2 are positive
    assert result['L1'] > 0, "L1 should be positive"
    assert result['L2'] > 0, "L2 should be positive"
    print("  ✓ Link lengths positive")

    # Check Z coordinates preserved
    assert abs(result['O_target'][2] - motion_G[2]) < 0.01
    assert abs(result['B_target'][2] - motion_B[2]) < 0.01
    print("  ✓ Z coordinates preserved")

    print("\n" + "="*70)
    print("✓ All calculate_L_shape_target tests PASSED")
    print("="*70)


def test_motion_coordinate_conversion():
    """Test raw to motion coordinate conversion."""
    print("\n" + "="*70)
    print("TEST: convert_to_motion_coordinates")
    print("="*70)

    class MockDriver:
        pass
    class MockSafety:
        pass

    primitives = BaxterPrimitives(MockDriver(), MockSafety())

    print("\nTest: Convert raw to motion coordinates")
    raw_positions = {
        'R': [0.5, 0.3, -0.20],
        'G': [0.6, 0.3, -0.18],
        'O': [0.7, 0.35, -0.19],
        'B': [0.8, 0.4, -0.17]
    }
    motion_z = -0.16

    motion_positions = primitives.convert_to_motion_coordinates(raw_positions, motion_z)

    print(f"  Motion Z: {motion_z}")
    for key in raw_positions:
        print(f"  {key}: {raw_positions[key]} → {motion_positions[key]}")

    # Check Z coordinates all equal motion_z
    for key, pos in motion_positions.items():
        assert abs(pos[2] - motion_z) < 0.001, f"{key} Z should be {motion_z}"
    print("  ✓ All Z coordinates set to motion_z")

    # Check XY preserved
    for key in raw_positions:
        assert abs(motion_positions[key][0] - raw_positions[key][0]) < 0.001
        assert abs(motion_positions[key][1] - raw_positions[key][1]) < 0.001
    print("  ✓ XY coordinates preserved")

    print("\n" + "="*70)
    print("✓ All motion coordinate conversion tests PASSED")
    print("="*70)


if __name__ == '__main__':
    print("\n" + "="*70)
    print("SHAPE RULER GEOMETRY UNIT TESTS")
    print("="*70)

    try:
        test_distance_xy()
        test_rotate_vector_2d()
        test_calculate_L_shape_target()
        test_motion_coordinate_conversion()

        print("\n" + "="*70)
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("="*70 + "\n")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ TEST ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
