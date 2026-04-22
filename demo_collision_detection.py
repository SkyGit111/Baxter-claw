#!/usr/bin/env python3
"""
Collision Detection Demo

This script demonstrates the collision detection feature in real scenarios.
Run this to see how collision detection works with actual robot movements.
"""

import asyncio
import sys
from bridge.arm_manager import ArmManager


async def demo_pick_with_collision_detection():
    """Demo: Pick operation with collision detection enabled."""
    print("\n" + "="*60)
    print("Demo: Pick with Collision Detection")
    print("="*60)

    # Initialize with collision detection enabled
    manager = ArmManager(config_path='config/baxter.yaml')

    # Enable collision detection with custom settings
    manager.collision_detector.update_config(
        enabled=True,
        position_threshold=0.005,  # 5mm
        stagnation_duration=2.0,   # 2 seconds
        debug=True                 # Show debug output
    )

    print("\n[Demo] Collision detection enabled")
    print(f"[Demo] Config: {manager.collision_detector.get_config()}")

    # Connect to robot
    if not manager.connect():
        print("[Demo] Failed to connect to robot")
        return False

    if not manager.enable():
        print("[Demo] Failed to enable robot")
        return False

    print("\n[Demo] Robot connected and enabled")

    # Define collision callback
    collision_detected = [False]
    def on_collision():
        collision_detected[0] = True
        print("\n[Demo] ⚠ COLLISION CALLBACK TRIGGERED!")
        print("[Demo] Stopping robot motion...")
        # In real scenario, you might want to:
        # - Stop the motion
        # - Retract the arm
        # - Alert the operator

    # Define position getter
    def get_position():
        pose = manager.driver.get_endpoint_pose('right')
        return pose[:3] if pose else None

    # Start collision monitoring
    manager.collision_detector.start_monitoring(
        arm='right',
        get_position_func=get_position,
        on_collision=on_collision
    )

    print("\n[Demo] Starting pick operation...")
    print("[Demo] Collision monitoring active")

    # Attempt to pick an object
    # If the object is not there or arm hits table, collision will be detected
    result = await manager.primitives.pick_by_name(
        arm='right',
        object_name='red block',
        approach_height=0.1,
        speed=0.2  # Slower speed for safety
    )

    # Stop monitoring
    collision_result = manager.collision_detector.stop_monitoring()

    print(f"\n[Demo] Pick result: {result}")
    print(f"[Demo] Collision detection result: {collision_result}")

    if collision_result['collision_detected']:
        print("\n[Demo] ⚠ Collision was detected during operation!")
        print("[Demo] This could mean:")
        print("  - Arm hit the table surface")
        print("  - Arm encountered an obstacle")
        print("  - Object was stuck or too heavy")
    else:
        print("\n[Demo] ✓ No collision detected - operation completed normally")

    # Cleanup
    manager.home('right')
    manager.disable()
    manager.disconnect()

    return True


async def demo_move_with_obstacle():
    """Demo: Move operation that encounters an obstacle."""
    print("\n" + "="*60)
    print("Demo: Move with Obstacle Detection")
    print("="*60)

    manager = ArmManager(config_path='config/baxter.yaml')

    # Enable with more sensitive settings
    manager.collision_detector.update_config(
        enabled=True,
        position_threshold=0.003,  # More sensitive: 3mm
        stagnation_duration=1.5,   # Faster response: 1.5s
        sample_interval=0.15,      # Higher frequency: 150ms
        debug=True
    )

    print("\n[Demo] Collision detection enabled (sensitive mode)")

    if not manager.connect() or not manager.enable():
        print("[Demo] Failed to initialize robot")
        return False

    # Position getter
    def get_position():
        pose = manager.driver.get_endpoint_pose('right')
        return pose[:3] if pose else None

    # Start monitoring
    manager.collision_detector.start_monitoring(
        arm='right',
        get_position_func=get_position,
        on_collision=lambda: print("\n[Demo] ⚠ Obstacle detected!")
    )

    print("\n[Demo] Moving arm forward...")
    print("[Demo] If an obstacle is in the way, it will be detected")

    # Try to move forward - may hit obstacle
    result = manager.primitives.move_to(
        arm='right',
        position=[0.8, 0.0, 0.0],  # Far forward
        speed=0.2
    )

    # Check results
    collision_result = manager.collision_detector.stop_monitoring()

    print(f"\n[Demo] Move result: {result}")
    print(f"[Demo] Collision result: {collision_result}")

    # Cleanup
    manager.home('right')
    manager.disable()
    manager.disconnect()

    return True


async def demo_table_press_detection():
    """Demo: Detect when arm presses against table."""
    print("\n" + "="*60)
    print("Demo: Table Press Detection")
    print("="*60)

    manager = ArmManager(config_path='config/baxter.yaml')

    # Enable collision detection
    manager.collision_detector.update_config(
        enabled=True,
        position_threshold=0.005,
        stagnation_duration=2.0,
        debug=True
    )

    print("\n[Demo] Testing table press detection")

    if not manager.connect() or not manager.enable():
        print("[Demo] Failed to initialize robot")
        return False

    # Position getter
    def get_position():
        pose = manager.driver.get_endpoint_pose('right')
        return pose[:3] if pose else None

    # Start monitoring
    manager.collision_detector.start_monitoring(
        arm='right',
        get_position_func=get_position,
        on_collision=lambda: print("\n[Demo] ⚠ Table contact detected!")
    )

    print("\n[Demo] Lowering arm to table level...")

    # Try to move down to table (and potentially through it)
    result = manager.primitives.move_to(
        arm='right',
        position=[0.6, 0.0, -0.20],  # Below table surface
        speed=0.15  # Slow and careful
    )

    # Check results
    collision_result = manager.collision_detector.stop_monitoring()

    print(f"\n[Demo] Move result: {result}")
    print(f"[Demo] Collision result: {collision_result}")

    if collision_result['collision_detected']:
        print("\n[Demo] ✓ Successfully detected table contact!")
        print("[Demo] This prevents damage from continuous pressing")
    else:
        print("\n[Demo] No collision detected")

    # Cleanup
    manager.home('right')
    manager.disable()
    manager.disconnect()

    return True


def demo_config_comparison():
    """Demo: Compare different configuration settings."""
    print("\n" + "="*60)
    print("Demo: Configuration Comparison")
    print("="*60)

    manager = ArmManager(config_path='config/baxter.yaml')

    configs = [
        {
            'name': 'Conservative (Low false positives)',
            'settings': {
                'position_threshold': 0.008,
                'stagnation_duration': 3.0,
                'min_samples': 5
            }
        },
        {
            'name': 'Balanced (Default)',
            'settings': {
                'position_threshold': 0.005,
                'stagnation_duration': 2.0,
                'min_samples': 3
            }
        },
        {
            'name': 'Sensitive (Quick response)',
            'settings': {
                'position_threshold': 0.003,
                'stagnation_duration': 1.0,
                'min_samples': 2
            }
        }
    ]

    print("\n[Demo] Comparing different configurations:\n")

    for config in configs:
        print(f"  {config['name']}:")
        for key, value in config['settings'].items():
            print(f"    {key}: {value}")
        print()

    print("[Demo] Choose configuration based on your needs:")
    print("  - Conservative: For delicate operations, avoid false alarms")
    print("  - Balanced: Good for general use")
    print("  - Sensitive: For safety-critical operations, quick response")

    return True


async def main():
    """Run all demos."""
    print("="*60)
    print("Collision Detection Demo Suite")
    print("="*60)
    print("\nThis demo shows how collision detection works in practice.")
    print("Make sure the robot is connected and workspace is clear.")
    print()

    demos = [
        ("Configuration Comparison", demo_config_comparison, False),
        ("Pick with Collision Detection", demo_pick_with_collision_detection, True),
        ("Move with Obstacle Detection", demo_move_with_obstacle, True),
        ("Table Press Detection", demo_table_press_detection, True),
    ]

    print("Available demos:")
    for i, (name, _, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print(f"  {len(demos)+1}. Run all demos")
    print("  0. Exit")

    try:
        choice = input("\nSelect demo (0-{}): ".format(len(demos)+1))
        choice = int(choice)

        if choice == 0:
            print("Exiting...")
            return

        if choice == len(demos) + 1:
            # Run all demos
            for name, demo_func, is_async in demos:
                print(f"\n\nRunning: {name}")
                input("Press Enter to continue...")
                try:
                    if is_async:
                        await demo_func()
                    else:
                        demo_func()
                except Exception as e:
                    print(f"\n[Demo] Error: {e}")
                    import traceback
                    traceback.print_exc()
        elif 1 <= choice <= len(demos):
            # Run selected demo
            name, demo_func, is_async = demos[choice - 1]
            print(f"\n\nRunning: {name}")
            try:
                if is_async:
                    await demo_func()
                else:
                    demo_func()
            except Exception as e:
                print(f"\n[Demo] Error: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("Invalid choice")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("Demo completed")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
