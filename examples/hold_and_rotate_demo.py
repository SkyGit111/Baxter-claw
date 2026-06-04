#!/usr/bin/env python
"""Demo script for bimanual hold-and-rotate task.

This script demonstrates the hold-and-rotate functionality with dry_run mode
to compute and display the rotation plan without executing robot motion.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import argparse
from bridge.arm_manager import ArmManager


async def demo_hold_and_rotate(
    fixed_segment_color: str = "blue",
    moving_segment_color: str = "yellow",
    angle_degrees: float = 90,
    direction: str = "clockwise",
    dry_run: bool = True
):
    """Run hold-and-rotate demo.
    
    Args:
        fixed_segment_color: Color of segment to hold fixed
        moving_segment_color: Color of segment to rotate
        angle_degrees: Rotation angle in degrees
        direction: 'clockwise' or 'counterclockwise'
        dry_run: If True, only compute plan without executing
    """
    print("\n" + "="*70)
    print("BIMANUAL HOLD AND ROTATE DEMO")
    print("="*70)
    print(f"Fixed segment: {fixed_segment_color}")
    print(f"Moving segment: {moving_segment_color}")
    print(f"Rotation: {angle_degrees}° {direction}")
    print(f"Dry run: {dry_run}")
    print("="*70 + "\n")
    
    # Initialize manager
    print("[1] Initializing robot manager...")
    manager = ArmManager(config_path='config/baxter.yaml')
    
    if not manager.driver.connect():
        print("✗ Failed to connect to robot")
        return False
    
    print("✓ Connected to robot\n")
    
    # Execute hold-and-rotate
    print(f"[2] Executing hold-and-rotate task...")
    print(f"    (dry_run={dry_run} - {'plan only' if dry_run else 'full execution'})\n")
    
    result = await manager.primitives.bimanual_hold_and_rotate(
        fixed_arm='left',
        moving_arm='right',
        fixed_segment_color=fixed_segment_color,
        moving_segment_color=moving_segment_color,
        angle_degrees=angle_degrees,
        direction=direction,
        segment_length=0.15,
        use_d455=True,
        approach_height=0.10,
        speed=0.10,
        waypoint_angle_step_degrees=10.0,
        keep_z_constant=True,
        dry_run=dry_run
    )
    
    # Display results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    
    if result['success']:
        print("✓ Task completed successfully\n")
        
        print("Localization Results:")
        print(f"  Fixed grasp: {result.get('fixed_grasp_position')}")
        print(f"  Moving grasp: {result.get('moving_grasp_position')}")
        print(f"  Fixed midpoint: {result.get('fixed_segment_midpoint')}")
        print(f"  Moving midpoint: {result.get('moving_segment_midpoint')}")
        print(f"  Observed hinge: {result.get('hinge_observed_position')}")
        
        print("\nGeometry Computation:")
        print(f"  Candidate hinges: {result.get('candidate_hinges')}")
        print(f"  Selected hinge: {result.get('hinge_position')}")
        print(f"  Selection reason: {result.get('hinge_selection_reason')}")
        print(f"  Target position: {result.get('target_position')}")
        
        print("\nPath Planning:")
        waypoints = result.get('waypoints', [])
        print(f"  Total waypoints: {len(waypoints)}")
        if waypoints:
            print(f"  First waypoint: {waypoints[0]}")
            print(f"  Last waypoint: {waypoints[-1]}")
        
        warnings = result.get('warnings', [])
        if warnings:
            print(f"\nWarnings ({len(warnings)}):")
            for warning in warnings:
                print(f"  ⚠ {warning}")
        
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
    
    # Cleanup
    manager.driver.disconnect()
    
    return result['success']


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Demo for bimanual hold-and-rotate task"
    )
    parser.add_argument(
        '--fixed-color',
        type=str,
        default='blue',
        help='Color of segment to hold fixed (default: blue)'
    )
    parser.add_argument(
        '--moving-color',
        type=str,
        default='yellow',
        help='Color of segment to rotate (default: yellow)'
    )
    parser.add_argument(
        '--angle',
        type=float,
        default=90,
        help='Rotation angle in degrees (default: 90)'
    )
    parser.add_argument(
        '--direction',
        type=str,
        choices=['clockwise', 'counterclockwise'],
        default='clockwise',
        help='Rotation direction (default: clockwise)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute robot motion (default: dry run only)'
    )
    
    args = parser.parse_args()
    
    # Run demo
    success = asyncio.run(demo_hold_and_rotate(
        fixed_segment_color=args.fixed_color,
        moving_segment_color=args.moving_color,
        angle_degrees=args.angle,
        direction=args.direction,
        dry_run=not args.execute
    ))
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

