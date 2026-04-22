"""Test script for collision detection functionality.

This script demonstrates and tests the collision detection feature.
"""

import time
import sys
from bridge.arm_manager import ArmManager


def test_collision_detection_disabled():
    """Test that system works normally with collision detection disabled."""
    print("\n=== Test 1: Collision Detection Disabled ===")

    # Initialize with collision detection disabled (default)
    manager = ArmManager(config_path='config/baxter.yaml')

    # Check collision detector state
    if manager.collision_detector:
        print(f"Collision detector config: {manager.collision_detector.get_config()}")
        assert not manager.collision_detector.enabled, "Should be disabled by default"
        print("✓ Collision detection is disabled as expected")
    else:
        print("✗ Collision detector not initialized")
        return False

    return True


def test_collision_detection_enabled():
    """Test collision detection when enabled."""
    print("\n=== Test 2: Collision Detection Enabled ===")

    # Initialize manager
    manager = ArmManager(config_path='config/baxter.yaml')

    if not manager.collision_detector:
        print("✗ Collision detector not available")
        return False

    # Enable collision detection with debug mode
    manager.collision_detector.update_config(enabled=True, debug=True)
    print(f"Collision detector config: {manager.collision_detector.get_config()}")

    # Simulate position monitoring
    print("\nSimulating arm motion with collision...")

    # Mock position function that simulates stagnation
    call_count = [0]
    def mock_get_position():
        call_count[0] += 1
        if call_count[0] < 5:
            # First few samples: arm is moving
            return [0.5 + call_count[0] * 0.01, 0.0, 0.0]
        else:
            # After 5 samples: arm stops (collision)
            return [0.55, 0.0, 0.0]

    # Start monitoring
    collision_callback_triggered = [False]
    def on_collision():
        collision_callback_triggered[0] = True
        print("  Collision callback triggered!")

    success = manager.collision_detector.start_monitoring(
        arm='right',
        get_position_func=mock_get_position,
        on_collision=on_collision
    )

    if not success:
        print("✗ Failed to start monitoring")
        return False

    print("  Monitoring started...")

    # Wait for collision detection (should take ~2 seconds)
    time.sleep(3.5)

    # Stop monitoring and check results
    result = manager.collision_detector.stop_monitoring()

    print(f"\nMonitoring result: {result}")
    print(f"Callback triggered: {collision_callback_triggered[0]}")

    if result['collision_detected']:
        print("✓ Collision detected successfully")
        return True
    else:
        print("✗ Collision not detected")
        return False


def test_collision_detection_no_collision():
    """Test that normal motion doesn't trigger false positives."""
    print("\n=== Test 3: Normal Motion (No False Positives) ===")

    # Initialize manager
    manager = ArmManager(config_path='config/baxter.yaml')

    if not manager.collision_detector:
        print("✗ Collision detector not available")
        return False

    # Enable collision detection
    manager.collision_detector.enable()

    # Mock position function that simulates continuous movement
    call_count = [0]
    def mock_get_position_moving():
        call_count[0] += 1
        # Arm keeps moving
        return [0.5 + call_count[0] * 0.01, 0.0, 0.0]

    # Start monitoring
    success = manager.collision_detector.start_monitoring(
        arm='right',
        get_position_func=mock_get_position_moving,
        on_collision=None
    )

    if not success:
        print("✗ Failed to start monitoring")
        return False

    print("  Monitoring started...")

    # Wait for a while (should NOT detect collision)
    time.sleep(2.5)

    # Stop monitoring and check results
    result = manager.collision_detector.stop_monitoring()

    print(f"\nMonitoring result: {result}")

    if not result['collision_detected']:
        print("✓ No false positive - normal motion not flagged as collision")
        return True
    else:
        print("✗ False positive detected")
        return False


def test_config_update():
    """Test dynamic configuration updates."""
    print("\n=== Test 4: Dynamic Configuration Update ===")

    manager = ArmManager(config_path='config/baxter.yaml')

    if not manager.collision_detector:
        print("✗ Collision detector not available")
        return False

    # Get initial config
    initial_config = manager.collision_detector.get_config()
    print(f"Initial config: {initial_config}")

    # Update configuration
    manager.collision_detector.update_config(
        enabled=True,
        position_threshold=0.003,
        stagnation_duration=1.5,
        debug=True
    )

    # Get updated config
    updated_config = manager.collision_detector.get_config()
    print(f"Updated config: {updated_config}")

    # Verify changes
    assert updated_config['enabled'] == True
    assert updated_config['position_threshold'] == 0.003
    assert updated_config['stagnation_duration'] == 1.5
    assert updated_config['debug'] == True

    print("✓ Configuration updated successfully")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Collision Detection Test Suite")
    print("=" * 60)

    tests = [
        ("Disabled by default", test_collision_detection_disabled),
        ("Collision detection", test_collision_detection_enabled),
        ("No false positives", test_collision_detection_no_collision),
        ("Config updates", test_config_update),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
