#!/usr/bin/env python
"""Unit tests for hold-and-rotate geometry helpers."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from bridge.primitives import BaxterPrimitives


def test_rotate_point_around_center_xy():
    """Test 2D point rotation around center."""
    print("\n" + "="*70)
    print("TEST: rotate_point_around_center_xy")
    print("="*70)
    
    # Create a mock primitives instance (we only need the geometry method)
    class MockDriver:
        pass
    class MockSafety:
        pass
    
    primitives = BaxterPrimitives(MockDriver(), MockSafety())
    
    # Test 1: Counterclockwise 90° rotation
    print("\nTest 1: Counterclockwise 90° from [1, 0, 0] around origin")
    point = [1.0, 0.0, 0.5]
    center = [0.0, 0.0, 0.0]
    result = primitives.rotate_point_around_center_xy(point, center, 90, "counterclockwise")
    print(f"  Input: {point}")
    print(f"  Result: {result}")
    print(f"  Expected: ~[0, 1, 0.5]")
    assert abs(result[0]) < 0.01, f"X should be ~0, got {result[0]}"
    assert abs(result[1] - 1.0) < 0.01, f"Y should be ~1, got {result[1]}"
    assert abs(result[2] - 0.5) < 0.01, f"Z should be 0.5, got {result[2]}"
    print("  ✓ PASS")
    
    # Test 2: Clockwise 90° rotation
    print("\nTest 2: Clockwise 90° from [1, 0, 0] around origin")
    result = primitives.rotate_point_around_center_xy(point, center, 90, "clockwise")
    print(f"  Input: {point}")
    print(f"  Result: {result}")
    print(f"  Expected: ~[0, -1, 0.5]")
    assert abs(result[0]) < 0.01, f"X should be ~0, got {result[0]}"
    assert abs(result[1] + 1.0) < 0.01, f"Y should be ~-1, got {result[1]}"
    assert abs(result[2] - 0.5) < 0.01, f"Z should be 0.5, got {result[2]}"
    print("  ✓ PASS")
    
    # Test 3: 180° rotation
    print("\nTest 3: Counterclockwise 180° from [1, 0, 0] around origin")
    result = primitives.rotate_point_around_center_xy(point, center, 180, "counterclockwise")
    print(f"  Input: {point}")
    print(f"  Result: {result}")
    print(f"  Expected: ~[-1, 0, 0.5]")
    assert abs(result[0] + 1.0) < 0.01, f"X should be ~-1, got {result[0]}"
    assert abs(result[1]) < 0.01, f"Y should be ~0, got {result[1]}"
    print("  ✓ PASS")
    
    # Test 4: Rotation around non-origin center
    print("\nTest 4: Counterclockwise 90° from [2, 1, 0] around [1, 1, 0]")
    point = [2.0, 1.0, 0.3]
    center = [1.0, 1.0, 0.0]
    result = primitives.rotate_point_around_center_xy(point, center, 90, "counterclockwise")
    print(f"  Input: {point}")
    print(f"  Center: {center}")
    print(f"  Result: {result}")
    print(f"  Expected: ~[1, 2, 0.3]")
    assert abs(result[0] - 1.0) < 0.01, f"X should be ~1, got {result[0]}"
    assert abs(result[1] - 2.0) < 0.01, f"Y should be ~2, got {result[1]}"
    assert abs(result[2] - 0.3) < 0.01, f"Z should be 0.3, got {result[2]}"
    print("  ✓ PASS")
    
    print("\n" + "="*70)
    print("✓ All rotate_point_around_center_xy tests PASSED")
    print("="*70)


def test_plan_arc_waypoints_xy():
    """Test arc waypoint generation."""
    print("\n" + "="*70)
    print("TEST: plan_arc_waypoints_xy")
    print("="*70)
    
    class MockDriver:
        pass
    class MockSafety:
        pass
    
    primitives = BaxterPrimitives(MockDriver(), MockSafety())
    
    # Test: 90° rotation with 10° steps
    print("\nTest: 90° counterclockwise rotation from [1, 0, 0] around origin")
    start_point = [1.0, 0.0, 0.5]
    center = [0.0, 0.0, 0.0]
    waypoints = primitives.plan_arc_waypoints_xy(start_point, center, 90, "counterclockwise", 10.0)
    
    print(f"  Generated {len(waypoints)} waypoints")
    print(f"  First waypoint: {waypoints[0]}")
    print(f"  Last waypoint: {waypoints[-1]}")
    
    # Check minimum waypoints
    assert len(waypoints) >= 5, f"Should have at least 5 waypoints, got {len(waypoints)}"
    print(f"  ✓ At least 5 waypoints")
    
    # Check first waypoint is start
    assert np.allclose(waypoints[0], start_point, atol=0.01), "First waypoint should be start point"
    print(f"  ✓ First waypoint matches start")
    
    # Check last waypoint is at 90°
    expected_end = [0.0, 1.0, 0.5]
    assert np.allclose(waypoints[-1], expected_end, atol=0.01), f"Last waypoint should be ~{expected_end}"
    print(f"  ✓ Last waypoint at correct position")
    
    # Check all waypoints have same radius
    radius = 1.0
    for i, wp in enumerate(waypoints):
        wp_radius = np.sqrt((wp[0] - center[0])**2 + (wp[1] - center[1])**2)
        assert abs(wp_radius - radius) < 0.01, f"Waypoint {i} radius {wp_radius} != {radius}"
    print(f"  ✓ All waypoints at correct radius")
    
    # Check Z unchanged
    for i, wp in enumerate(waypoints):
        assert abs(wp[2] - start_point[2]) < 0.01, f"Waypoint {i} Z changed"
    print(f"  ✓ Z coordinate unchanged")
    
    print("\n" + "="*70)
    print("✓ All plan_arc_waypoints_xy tests PASSED")
    print("="*70)


def test_estimate_hinge_center():
    """Test hinge center estimation from two midpoints."""
    print("\n" + "="*70)
    print("TEST: estimate_hinge_center_from_two_midpoints_and_observed_joint")
    print("="*70)
    
    class MockDriver:
        pass
    class MockSafety:
        pass
    
    primitives = BaxterPrimitives(MockDriver(), MockSafety())
    
    # Test 1: Two segments aligned horizontally
    print("\nTest 1: Horizontal segments")
    segment_length = 0.15
    r = segment_length / 2.0  # 0.075
    
    # Midpoints at distance 2r apart (segments touching at hinge)
    midpoint_a = [0.0, 0.0, -0.15]
    midpoint_b = [0.15, 0.0, -0.15]
    
    # Observed hinge should be at midpoint between them
    observed_hinge = [0.075, 0.05, -0.15]  # Slightly off in Y
    
    result = primitives.estimate_hinge_center_from_two_midpoints_and_observed_joint(
        midpoint_a, midpoint_b, observed_hinge, segment_length, tolerance=0.02
    )
    
    print(f"  Midpoint A: {midpoint_a}")
    print(f"  Midpoint B: {midpoint_b}")
    print(f"  Observed hinge: {observed_hinge}")
    print(f"  Result: {result}")
    
    assert result['success'], f"Should succeed, got: {result.get('error')}"
    print(f"  ✓ Computation succeeded")
    
    selected = result['selected_hinge']
    print(f"  Selected hinge: {selected}")
    print(f"  Candidates: {result['candidate_hinges']}")
    print(f"  Selection reason: {result['selection_reason']}")
    
    # Check distances to midpoints
    dist_a = np.sqrt((selected[0] - midpoint_a[0])**2 + (selected[1] - midpoint_a[1])**2)
    dist_b = np.sqrt((selected[0] - midpoint_b[0])**2 + (selected[1] - midpoint_b[1])**2)
    
    print(f"  Distance to midpoint A: {dist_a:.4f}m (expected {r:.4f}m)")
    print(f"  Distance to midpoint B: {dist_b:.4f}m (expected {r:.4f}m)")
    
    assert abs(dist_a - r) < 0.02, f"Distance to A should be ~{r}, got {dist_a}"
    assert abs(dist_b - r) < 0.02, f"Distance to B should be ~{r}, got {dist_b}"
    print(f"  ✓ Distances to midpoints correct")
    
    # Test 2: Segments too far apart (should fail)
    print("\nTest 2: Segments too far apart (should fail)")
    midpoint_a = [0.0, 0.0, -0.15]
    midpoint_b = [0.30, 0.0, -0.15]  # Too far
    observed_hinge = [0.15, 0.0, -0.15]
    
    result = primitives.estimate_hinge_center_from_two_midpoints_and_observed_joint(
        midpoint_a, midpoint_b, observed_hinge, segment_length, tolerance=0.02
    )
    
    print(f"  Result: {result}")
    assert not result['success'], "Should fail for segments too far apart"
    print(f"  ✓ Correctly rejected invalid geometry")
    
    print("\n" + "="*70)
    print("✓ All estimate_hinge_center tests PASSED")
    print("="*70)


if __name__ == '__main__':
    print("\n" + "="*70)
    print("HOLD AND ROTATE GEOMETRY UNIT TESTS")
    print("="*70)
    
    try:
        test_rotate_point_around_center_xy()
        test_plan_arc_waypoints_xy()
        test_estimate_hinge_center()
        
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

