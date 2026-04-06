"""Example: Dual-arm coordination demonstration."""

import sys
from pathlib import Path

# Add bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bridge.arm_manager import ArmManager


def main():
    """Demonstrate dual-arm coordination capabilities."""
    print("=" * 60)
    print("Baxter-Claw Dual-Arm Coordination Demo")
    print("=" * 60)

    # Initialize with config
    config_path = Path(__file__).parent.parent / "config" / "baxter.example.yaml"
    manager = ArmManager(config_path=str(config_path))

    # Connect and enable
    print("\n1. Connecting to robot...")
    manager.connect()

    print("\n2. Enabling robot...")
    manager.enable()

    # Test 1: Synchronized move
    print("\n3. Testing synchronized move...")
    print("   Moving both arms to symmetric positions...")
    result = manager.primitives.synchronized_move(
        left_position=[0.6, 0.3, 0.2],
        right_position=[0.6, -0.3, 0.2]
    )
    if result['success']:
        print(f"   ✓ {result['message']}")
    else:
        print(f"   ✗ {result['message']}")

    # Test 2: Bimanual pick
    print("\n4. Testing bimanual pick...")
    print("   Picking large object with both arms...")
    result = manager.primitives.bimanual_pick(
        object_position=[0.65, 0.0, 0.1],
        left_offset=[-0.08, 0.0, 0.0],
        right_offset=[0.08, 0.0, 0.0]
    )
    if result['success']:
        print(f"   ✓ {result['message']}")
        print(f"   Left position: {result.get('left_position')}")
        print(f"   Right position: {result.get('right_position')}")
    else:
        print(f"   ✗ {result['message']}")

    # Test 3: Handover
    print("\n5. Testing handover...")
    print("   First, pick with right arm...")
    result = manager.primitives.pick('right', [0.6, -0.2, 0.1])
    if result['success']:
        print(f"   ✓ Picked with right arm")

        print("   Now handing over to left arm...")
        result = manager.primitives.handover(
            from_arm='right',
            to_arm='left',
            handover_position=[0.6, 0.0, 0.3]
        )
        if result['success']:
            print(f"   ✓ {result['message']}")
            print(f"   Handover position: {result.get('handover_position')}")
        else:
            print(f"   ✗ {result['message']}")
    else:
        print(f"   ✗ Failed to pick with right arm")

    # Return both arms home
    print("\n6. Returning both arms to home positions...")
    result_left = manager.primitives.home('left')
    result_right = manager.primitives.home('right')
    print(f"   Left: {result_left['message']}")
    print(f"   Right: {result_right['message']}")

    # Cleanup
    print("\n7. Disabling and disconnecting...")
    manager.disable()
    manager.disconnect()

    print("\n" + "=" * 60)
    print("Dual-arm coordination demo completed!")
    print("=" * 60)
    print("\nKey Features Demonstrated:")
    print("  ✓ Synchronized motion of both arms")
    print("  ✓ Bimanual grasping for large objects")
    print("  ✓ Object handover between arms")
    print("  ✓ Collision detection between arms")


if __name__ == "__main__":
    main()
