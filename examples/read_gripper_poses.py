#!/usr/bin/env python3
"""
Simple script to read and display gripper positions and orientations.
Allows manual positioning of grippers and reads their current pose.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bridge.arm_manager import ArmManager
import numpy as np


def print_pose(arm_name: str, pose: list):
    """Print pose in a clear format with position and orientation separated.

    Args:
        arm_name: Name of the arm ('left' or 'right')
        pose: [x, y, z, roll, pitch, yaw]
    """
    print(f"\n{'='*60}")
    print(f"{arm_name.upper()} ARM POSE")
    print(f"{'='*60}")

    # Position
    print(f"\nPosition (meters):")
    print(f"  X: {pose[0]:8.4f} m")
    print(f"  Y: {pose[1]:8.4f} m")
    print(f"  Z: {pose[2]:8.4f} m")

    # Orientation
    print(f"\nOrientation (radians):")
    print(f"  Roll:  {pose[3]:8.4f} rad  ({np.rad2deg(pose[3]):7.2f}°)")
    print(f"  Pitch: {pose[4]:8.4f} rad  ({np.rad2deg(pose[4]):7.2f}°)")
    print(f"  Yaw:   {pose[5]:8.4f} rad  ({np.rad2deg(pose[5]):7.2f}°)")

    print(f"\nFull Pose (copy-paste ready):")
    print(f"  {pose}")
    print(f"{'='*60}\n")


def main():
    print("\n" + "="*60)
    print("GRIPPER POSE READER")
    print("="*60)
    print("\nThis script will read the current position and orientation")
    print("of the left and right grippers.")
    print("\nMake sure the robot is enabled before running this script.")
    print("="*60 + "\n")

    # Initialize arm manager with Baxter config
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
    print(f"   Driver type: {type(manager.driver).__name__}")

    if not manager.connect():
        print("❌ Failed to connect to robot")
        print("\nPossible issues:")
        print("  1. ROS is not running")
        print("  2. Baxter robot is not powered on")
        print("  3. Network connection issue")
        print("  4. Wrong driver type in config")
        print(f"\nCurrent driver: {type(manager.driver).__name__}")
        return False

    print("✓ Connected to robot")
    print(f"   Driver: {type(manager.driver).__name__}")

    # Check if robot is enabled (but don't block if check fails)
    try:
        is_enabled = manager.driver.is_enabled()
        if not is_enabled:
            print("⚠️  WARNING: Robot reports as not enabled")
            print("    This may be a false alarm - will try to read anyway\n")
    except Exception as e:
        print(f"⚠️  WARNING: Could not check enable status: {e}")
        print("    Will try to read anyway\n")

    while True:
        print("\n" + "="*60)
        print("INSTRUCTIONS")
        print("="*60)
        print("\n1. Manually move the left and right grippers to desired positions")
        print("2. Press ENTER when ready to read poses")
        print("3. Type 'j' to read joint angles (for debugging)")
        print("4. Type 'q' to quit")
        print("\n" + "="*60)

        user_input = input("\nPress ENTER to read poses (or 'j'/'q'): ")

        if user_input.lower() == 'q':
            print("\nExiting...")
            break

        if user_input.lower() == 'j':
            # Read joint angles for debugging
            print("\n" + "="*60)
            print("JOINT ANGLES (for debugging)")
            print("="*60)
            try:
                left_joints = manager.driver.get_joint_angles('left')
                right_joints = manager.driver.get_joint_angles('right')
                print(f"\nLeft arm joints: {left_joints}")
                print(f"Right arm joints: {right_joints}")
            except Exception as e:
                print(f"❌ Error reading joint angles: {e}")
            continue

        # Read left arm pose
        print("\nReading left arm pose...")
        try:
            left_pose = manager.driver.get_endpoint_pose('left')
            if left_pose is None:
                print("❌ Failed to read left arm pose (returned None)")
                print("   Make sure the robot is enabled and connected")
                continue

            # Check if it's all zeros (indicates error)
            if all(abs(v) < 0.001 for v in left_pose):
                print("❌ Left arm pose is all zeros (robot may not be connected)")
                print("   Make sure the robot is enabled and ROS is running")
                continue

            print(f"✓ Left pose read successfully")
            print(f"   Raw values: {left_pose}")
        except Exception as e:
            print(f"❌ Error reading left arm pose: {e}")
            import traceback
            traceback.print_exc()
            continue

        # Read right arm pose
        print("Reading right arm pose...")
        try:
            right_pose = manager.driver.get_endpoint_pose('right')
            if right_pose is None:
                print("❌ Failed to read right arm pose (returned None)")
                print("   Make sure the robot is enabled and connected")
                continue

            # Check if it's all zeros (indicates error)
            if all(abs(v) < 0.001 for v in right_pose):
                print("❌ Right arm pose is all zeros (robot may not be connected)")
                print("   Make sure the robot is enabled and ROS is running")
                continue

            print(f"✓ Right pose read successfully")
            print(f"   Raw values: {right_pose}")
        except Exception as e:
            print(f"❌ Error reading right arm pose: {e}")
            import traceback
            traceback.print_exc()
            continue

        # Display poses
        print_pose("left", left_pose)
        print_pose("right", right_pose)

        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"\nLeft Position:  [{left_pose[0]:.4f}, {left_pose[1]:.4f}, {left_pose[2]:.4f}]")
        print(f"Right Position: [{right_pose[0]:.4f}, {right_pose[1]:.4f}, {right_pose[2]:.4f}]")
        print(f"\nDistance between grippers: {np.linalg.norm(np.array(left_pose[:3]) - np.array(right_pose[:3])):.4f} m")
        print("="*60 + "\n")

    print("\n✓ Done\n")
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
