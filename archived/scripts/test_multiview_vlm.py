#!/usr/bin/env python3
"""Test multi-view VLM object localization.

This script demonstrates the complete multi-view approach:
1. Phase 1: D455 + head camera for global localization
   - Hand-eye calibration applied
   - Image preprocessing (crop, enhance, correct)
   - Optimized VLM prompts
2. Phase 2: D455 + wrist camera for refinement
   - Close-up detailed analysis
   - Multi-view fusion
"""

import asyncio
import sys
from bridge.drivers.baxter_driver import BaxterDriver
from bridge.vlm_client import VLMClient
from bridge.safety import SafetyValidator
from bridge.multi_view_vlm import MultiViewVLMCoordinator


async def test_multiview_localization():
    """Test complete multi-view object localization."""
    print("=" * 70)
    print("Multi-View VLM Object Localization Test")
    print("Complete Implementation with:")
    print("  - Hand-eye calibration")
    print("  - Image preprocessing")
    print("  - Optimized VLM prompts")
    print("  - Multi-view fusion")
    print("=" * 70)

    # Initialize components
    print("\n[1] Initializing components...")
    driver = BaxterDriver(use_depth_camera=True)

    if not driver.connect():
        print("✗ Failed to connect to Baxter")
        return False

    if not driver.enable():
        print("✗ Failed to enable Baxter")
        return False

    print("✓ Baxter connected and enabled")

    # Check depth camera
    if not driver.has_depth_camera():
        print("⚠ Warning: Depth camera not available!")
        print("Multi-view will work but without depth enhancement")
    else:
        print("✓ D455 depth camera available")

    # Initialize VLM client
    print("\n[2] Initializing VLM client...")
    vlm_client = VLMClient(provider='qwen')  # or 'claude', 'openai'
    print("✓ VLM client initialized (provider: qwen)")

    # Initialize safety validator
    print("\n[3] Initializing safety validator...")
    safety = SafetyValidator(config_path='config/baxter.yaml')
    print("✓ Safety validator initialized")

    # Initialize multi-view coordinator
    print("\n[4] Initializing multi-view coordinator...")
    coordinator = MultiViewVLMCoordinator(driver, vlm_client, safety)
    print("✓ Multi-view coordinator initialized")
    print("  - Hand-eye calibration loaded")
    print("  - Image processor ready")
    print("  - Optimized prompts ready")

    print("\n" + "=" * 70)
    print("Starting Multi-View Object Localization")
    print("=" * 70)

    # Test object
    object_name = input("\nEnter object name to locate (e.g., 'red cup', 'blue box'): ").strip()
    if not object_name:
        object_name = "red cup"
        print(f"Using default: '{object_name}'")

    # Choose arm
    arm = input("Which arm to use for wrist camera? (left/right) [right]: ").strip().lower()
    if arm not in ['left', 'right']:
        arm = 'right'
        print(f"Using default: {arm}")

    # Choose whether to use wrist refinement
    use_refinement = input("Use wrist camera refinement? (y/n) [y]: ").strip().lower()
    use_refinement = use_refinement != 'n'

    print(f"\n[5] Locating '{object_name}' using {arm} arm...")
    print(f"    Wrist refinement: {'enabled' if use_refinement else 'disabled'}")
    print(f"    Debug images will be saved to current directory")

    # Run multi-view localization
    result = await coordinator.locate_object_multiview(
        object_name=object_name,
        arm=arm,
        use_wrist_refinement=use_refinement
    )

    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    if result and result.get('found'):
        print(f"✓ Object found: {object_name}")
        print(f"\n  Position (base frame): {result['position']}")
        print(f"  Confidence: {result['confidence']}%")
        print(f"  Description: {result['description']}")
        print(f"  Bounding box: {result['bounding_box']}")

        # Show processing details
        print(f"\n  Processing Details:")
        if result.get('coordinate_transformed'):
            print(f"    ✓ Coordinate transformation applied")
            if 'position_camera_frame' in result:
                print(f"      Camera frame: {result['position_camera_frame']}")
                print(f"      Base frame: {result['position']}")

        if result.get('multi_view_validated'):
            print(f"    ✓ Multi-view validated (D455 + head camera)")
            print(f"      Validation quality: {result.get('validation_quality', 'N/A')}")
            if 'position_difference_m' in result:
                print(f"      Position difference: {result['position_difference_m']:.3f}m")

        if result.get('wrist_validated'):
            print(f"    ✓ Wrist camera validated")

        if result.get('depth_enhanced'):
            print(f"    ✓ Depth-enhanced positioning")
            if 'vlm_estimate' in result:
                print(f"      VLM estimate: {result['vlm_estimate']}")
                print(f"      Depth measurement: {result['position']}")

        if result.get('refinement_applied'):
            print(f"    ✓ Wrist refinement applied")

        if result.get('multi_stage_fusion'):
            print(f"    ✓ Multi-stage fusion completed")

        # Show grasp recommendations if available
        if 'grasp_recommendations' in result:
            print(f"\n  Grasp Recommendations:")
            grasp = result['grasp_recommendations']
            if isinstance(grasp, dict):
                for key, value in grasp.items():
                    print(f"    {key}: {value}")
            else:
                print(f"    {grasp}")

        # Ask if user wants to move to the object
        print("\n" + "=" * 70)
        move = input("\nMove gripper to detected position? (y/n) [n]: ").strip().lower()
        if move == 'y':
            print(f"\nMoving {arm} arm to object...")
            # Add approach height
            approach_pose = result['position'].copy()
            approach_pose[2] += 0.1  # 10cm above

            success = driver.move_to_pose(arm, approach_pose, speed=0.2, timeout=15.0)
            if success:
                print("✓ Moved to object location")
            else:
                print("✗ Failed to move to object")

    else:
        print(f"✗ Object not found: {object_name}")
        if result:
            print(f"  Reason: {result.get('description', 'Unknown')}")

    # Cleanup
    print("\n[6] Cleaning up...")
    driver.disconnect(keep_enabled=True)
    print("✓ Test completed")

    print("\n" + "=" * 70)
    print("Debug images saved:")
    print("  - debug_d455_phase1_*.jpg")
    print("  - debug_head_phase1_*.jpg")
    if use_refinement:
        print("  - debug_wrist_phase2_*.jpg")
        print("  - debug_d455_phase2_*.jpg")
    print("=" * 70)

    return result is not None and result.get('found', False)


def main():
    """Main entry point."""
    try:
        success = asyncio.run(test_multiview_localization())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
