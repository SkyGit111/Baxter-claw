"""Example: Test primitives with mock driver."""

import time
import sys
from pathlib import Path

# Add bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bridge.arm_manager import ArmManager


def main():
    """Test all primitives with mock driver."""
    print("=" * 60)
    print("Baxter-Claw Primitives Test")
    print("=" * 60)

    # Initialize with mock driver
    config_path = Path(__file__).parent.parent / "config" / "baxter.example.yaml"
    manager = ArmManager(config_path=str(config_path))

    # Connect and enable
    print("\n1. Connecting to robot...")
    manager.connect()

    print("\n2. Enabling robot...")
    manager.enable()

    # Get initial status
    print("\n3. Getting robot status...")
    status = manager.get_status('right')
    print(f"   Connected: {status['connected']}")
    print(f"   Enabled: {status['enabled']}")
    print(f"   Endpoint pose: {status['endpoint_pose'][:3]}")

    # Test pick primitive
    print("\n4. Testing PICK primitive...")
    pick_position = [0.6, 0.2, 0.1]
    result = manager.primitives.pick('right', pick_position)
    print(f"   Result: {result['message']}")

    time.sleep(1)

    # Test place primitive
    print("\n5. Testing PLACE primitive...")
    place_position = [0.5, -0.3, 0.15]
    result = manager.primitives.place('right', place_position)
    print(f"   Result: {result['message']}")

    time.sleep(1)

    # Test move_to primitive
    print("\n6. Testing MOVE_TO primitive...")
    target_position = [0.6, 0.0, 0.3]
    result = manager.primitives.move_to('right', target_position)
    print(f"   Result: {result['message']}")

    time.sleep(1)

    # Test home primitive
    print("\n7. Testing HOME primitive...")
    result = manager.primitives.home('right')
    print(f"   Result: {result['message']}")

    # Get final status
    print("\n8. Final robot status...")
    status = manager.get_status('right')
    print(f"   Endpoint pose: {status['endpoint_pose'][:3]}")

    # Cleanup
    print("\n9. Disabling and disconnecting...")
    manager.disable()
    manager.disconnect()

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
