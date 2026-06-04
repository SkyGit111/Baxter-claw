#!/usr/bin/env python3
"""
Demo script for flatten articulated ruler task.

This script demonstrates the dual-arm coordinated pulling task to straighten
an S-shaped folded ruler by grasping both endpoints and pulling them apart.
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bridge.arm_manager import ArmManager


async def main():
    print("\n" + "="*70)
    print("FLATTEN ARTICULATED RULER - DEMO")
    print("="*70)
    print("\nThis demo will:")
    print("  1. Locate red endpoint (purple tape) and blue endpoint (green tape)")
    print("  2. Grasp both endpoints with left and right arms")
    print("  3. Pull the endpoints apart to straighten the ruler")
    print("  4. Interpolate position and orientation during pulling")
    print("="*70 + "\n")

    # Initialize arm manager
    print("Initializing arm manager...")
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'baxter.yaml')

    if not os.path.exists(config_path):
        print(f"⚠️  Config file not found: {config_path}")
        print("   Using default configuration...")
        manager = ArmManager()
    else:
        print(f"   Using config: {config_path}")
        manager = ArmManager(config_path=config_path)

    # Connect to robot
    print("\nConnecting to robot...")
    if not manager.connect():
        print("❌ Failed to connect to robot")
        return False

    print("✓ Connected to robot")
    print(f"   Driver: {type(manager.driver).__name__}")

    # Task configuration
    flatten_config_path = os.path.join(
        os.path.dirname(__file__), '..', 'config', 'flatten_ruler_task.yaml'
    )

    # Direct execution mode (no confirmation prompts)
    dry_run = False

    print("\n" + "="*70)
    print("EXECUTION MODE: REAL ROBOT")
    print("="*70)
    print("\n⚠️  Robot will move in 3 seconds...")
    print("Press Ctrl+C to cancel\n")

    import time
    for i in range(3, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    print("\n" + "="*70)
    print("STARTING FLATTEN RULER TASK")
    print("="*70 + "\n")

    # Execute task
    try:
        result = await manager.primitives.flatten_articulated_ruler(
            config_path=flatten_config_path,
            dry_run=dry_run
        )

        # Display results
        print("\n" + "="*70)
        print("TASK RESULT")
        print("="*70)

        if result['success']:
            print(f"✓ Task completed successfully")
            print(f"\nEndpoints:")
            print(f"  Red endpoint: {result['red_endpoint']}")
            print(f"  Blue endpoint: {result['blue_endpoint']}")
            print(f"\nSeparation:")
            print(f"  Initial: {result['initial_separation']:.3f}m")
            print(f"  Final: {result['final_separation']:.3f}m")
            print(f"  Pull distance: {result.get('pull_distance', 0):.3f}m")
            print(f"\nTrajectory:")
            print(f"  Waypoints: {result['num_waypoints']}")

            if dry_run:
                print(f"\n⚠️  This was a dry run - no actual motion executed")
                print(f"   Left arm trajectory: {len(result['left_arm_trajectory'])} waypoints")
                print(f"   Right arm trajectory: {len(result['right_arm_trajectory'])} waypoints")
        else:
            print(f"✗ Task failed: {result.get('message', 'Unknown error')}")
            if 'failed_stage' in result:
                print(f"   Failed at stage: {result['failed_stage']}")

        print("="*70 + "\n")

        return result['success']

    except Exception as e:
        print(f"\n❌ Error during task execution: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
