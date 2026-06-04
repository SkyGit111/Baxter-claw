#!/usr/bin/env python
"""Demo script for bimanual shape ruler task.

This script demonstrates the shape ruler functionality with dry_run mode
to compute and display the adjustment plan without executing robot motion.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import argparse
from bridge.arm_manager import ArmManager


async def demo_shape_ruler(
    fixed_arm: str = "left",
    moving_arm: str = "right",
    target_shape: str = "L",
    l_shape_blue_turn_direction: str = "clockwise",
    config_path: str = "config/ruler_task.yaml",
    dry_run: bool = True
):
    """Run shape ruler demo.

    Args:
        fixed_arm: Arm to hold fixed segment
        moving_arm: Arm to push moving segment
        target_shape: Target shape configuration
        l_shape_blue_turn_direction: Blue segment turn direction
        config_path: Path to ruler task configuration
        dry_run: If True, only compute plan without executing
    """
    print("\n" + "="*70)
    print("BIMANUAL SHAPE RULER DEMO (PUSH MODE)")
    print("="*70)
    print(f"Fixed arm: {fixed_arm}")
    print(f"Moving arm: {moving_arm} (PUSH mode - no gripper close)")
    print(f"Target shape: {target_shape}")
    print(f"Blue turn direction: {l_shape_blue_turn_direction}")
    print(f"Config: {config_path}")
    print(f"Dry run: {dry_run}")
    print("="*70 + "\n")

    # Initialize manager
    print("[1] Initializing robot manager...")
    manager = ArmManager(config_path='config/baxter.yaml')

    if not manager.driver.connect():
        print("✗ Failed to connect to robot")
        return False

    print("✓ Connected to robot\n")

    # Execute shape ruler task
    print(f"[2] Executing shape ruler task...")
    print(f"    (dry_run={dry_run} - {'plan only' if dry_run else 'full execution'})\n")

    result = await manager.primitives.bimanual_shape_ruler(
        fixed_arm=fixed_arm,
        moving_arm=moving_arm,
        target_shape=target_shape,
        l_shape_blue_turn_direction=l_shape_blue_turn_direction,
        config_path=config_path,
        dry_run=dry_run
    )

    # Display results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)

    if result['success']:
        print("✓ Task completed successfully\n")

        print("Mode:")
        print(f"  Push mode: {result.get('push_mode')}")
        print(f"  Moving gripper close: {result.get('moving_gripper_close')}")

        print("\nRaw Localization (VLM+D455):")
        print(f"  Red grasp: {result.get('raw_red_grasp_position')}")
        print(f"  Green joint: {result.get('raw_green_joint_position')}")
        print(f"  Orange joint: {result.get('raw_orange_joint_position')}")
        print(f"  Blue push: {result.get('raw_blue_push_position')}")

        print("\nMotion Coordinates (Z fixed):")
        print(f"  Motion Z: {result.get('motion_z')}")
        print(f"  Approach Z: {result.get('approach_z')}")
        print(f"  Red grasp: {result.get('motion_red_grasp_position')}")
        print(f"  Green joint: {result.get('motion_green_joint_position')}")
        print(f"  Orange joint: {result.get('motion_orange_joint_position')}")
        print(f"  Blue push: {result.get('motion_blue_push_position')}")

        print("\nGeometry:")
        print(f"  L1 (G-O): {result.get('L1', 0):.3f}m")
        print(f"  L2 (O-B): {result.get('L2', 0):.3f}m")
        print(f"  O_target: {result.get('O_target')}")
        print(f"  B_target: {result.get('B_target')}")
        print(f"  Red-yellow target angle: {result.get('red_yellow_target_angle_deg')}°")
        print(f"  Blue-yellow target angle: {result.get('blue_yellow_target_angle_deg')}°")

        print("\nWaypoints:")
        all_model = result.get('all_model_waypoints', [])
        execution = result.get('execution_waypoints', [])
        push_exec = result.get('push_execution_waypoints', [])
        print(f"  All model waypoints: {len(all_model)}")
        print(f"  Execution waypoints: {len(execution)} (skipped first: {result.get('skip_first_waypoint')})")
        print(f"  Push execution waypoints: {len(push_exec)}")
        if push_exec:
            print(f"  First push waypoint: {push_exec[0]}")
            print(f"  Last push waypoint: {push_exec[-1]}")

        print("\nJoint Angle Validation:")
        green_checks = result.get('green_joint_angle_check_results', [])
        orange_checks = result.get('orange_joint_angle_check_results', [])
        print(f"  Green joint checks: {len(green_checks)}")
        print(f"  Orange joint checks: {len(orange_checks)}")
        print(f"  Joint limit violation: {result.get('joint_limit_violation')}")

        warnings = result.get('warnings', [])
        if warnings:
            print(f"\n⚠ Warnings ({len(warnings)}):")
            for warning in warnings:
                print(f"  - {warning}")

        if dry_run:
            print("\n✓ Dry run complete - plan computed successfully")
            print("  To execute for real, run with --execute flag")
        else:
            print("\n✓ Robot execution complete")

    else:
        print(f"✗ Task failed: {result.get('message')}")
        print(f"  Failed stage: {result.get('failed_stage')}")
        if result.get('failed_waypoint_index') is not None:
            print(f"  Failed waypoint: {result.get('failed_waypoint_index')}")

    print("="*70 + "\n")

    # DO NOT disconnect - keep robot enabled for next run
    # manager.driver.disconnect()
    print("✓ Task complete - robot remains enabled for next run\n")

    return result['success']


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Demo for bimanual shape ruler task (push mode)"
    )
    parser.add_argument(
        '--fixed-arm',
        type=str,
        default='left',
        choices=['left', 'right'],
        help='Arm to hold fixed segment (default: left)'
    )
    parser.add_argument(
        '--moving-arm',
        type=str,
        default='right',
        choices=['left', 'right'],
        help='Arm to push moving segment (default: right)'
    )
    parser.add_argument(
        '--target-shape',
        type=str,
        default='L',
        choices=['L'],
        help='Target shape configuration (default: L)'
    )
    parser.add_argument(
        '--blue-turn',
        type=str,
        default='clockwise',
        choices=['clockwise', 'counterclockwise'],
        help='Blue segment turn direction (default: clockwise)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/ruler_task.yaml',
        help='Path to ruler task configuration (default: config/ruler_task.yaml)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute robot motion (default: dry run only)'
    )

    args = parser.parse_args()

    # Run demo
    success = asyncio.run(demo_shape_ruler(
        fixed_arm=args.fixed_arm,
        moving_arm=args.moving_arm,
        target_shape=args.target_shape,
        l_shape_blue_turn_direction=args.blue_turn,
        config_path=args.config,
        dry_run=not args.execute
    ))

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
