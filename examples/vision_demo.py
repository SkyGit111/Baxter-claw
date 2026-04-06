"""Example: Vision-guided pick and place using VLM."""

import asyncio
import sys
from pathlib import Path

# Add bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bridge.arm_manager import ArmManager


async def main():
    """Demonstrate vision-guided manipulation."""
    print("=" * 60)
    print("Baxter-Claw Vision Demo")
    print("=" * 60)

    # Initialize with config
    config_path = Path(__file__).parent.parent / "config" / "baxter.example.yaml"
    manager = ArmManager(config_path=str(config_path))

    # Check if VLM is enabled
    if not manager.vlm_client:
        print("\n⚠️  VLM client not configured!")
        print("To enable vision features:")
        print("1. Edit config/baxter.yaml:")
        print("   vlm:")
        print("     enabled: true")
        print("     provider: 'claude'")
        print("     api_key: '${ANTHROPIC_API_KEY}'")
        print("\n2. Set environment variable:")
        print("   export ANTHROPIC_API_KEY='your-api-key'")
        print("\n3. Restart the bridge server")
        return

    # Connect and enable
    print("\n1. Connecting to robot...")
    manager.connect()

    print("\n2. Enabling robot...")
    manager.enable()

    # Describe scene
    print("\n3. Describing scene...")
    result = await manager.primitives.describe_scene(camera='right_hand')
    if result['success']:
        print(f"   Scene: {result['description']}")
    else:
        print(f"   Failed: {result['message']}")

    # Identify objects
    print("\n4. Identifying objects...")
    result = await manager.primitives.identify_objects(camera='right_hand')
    if result['success']:
        print(f"   Found {len(result['objects'])} objects:")
        for obj in result['objects']:
            print(f"   - {obj['name']} ({obj['color']}, {obj['size']}) at {obj['location']}")
    else:
        print(f"   Failed: {result['message']}")

    # Locate specific object
    print("\n5. Locating 'red cup'...")
    result = await manager.primitives.locate_object('red cup', camera='right_hand')
    if result['success']:
        print(f"   Found at position: {result['position']}")
        print(f"   Confidence: {result['confidence']}%")
        print(f"   Description: {result['description']}")
    else:
        print(f"   Not found: {result['message']}")

    # Pick by name
    print("\n6. Picking 'red cup' using vision...")
    result = await manager.primitives.pick_by_name(
        arm='right',
        object_name='red cup',
        camera='right_hand'
    )
    if result['success']:
        print(f"   Success! {result['message']}")
        print(f"   Position: {result.get('position')}")
        print(f"   Confidence: {result.get('confidence')}%")
    else:
        print(f"   Failed: {result['message']}")

    # Return home
    print("\n7. Returning to home position...")
    result = manager.primitives.home('right')
    print(f"   {result['message']}")

    # Cleanup
    print("\n8. Disabling and disconnecting...")
    manager.disable()
    manager.disconnect()

    print("\n" + "=" * 60)
    print("Vision demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
