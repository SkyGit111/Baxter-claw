"""Mock driver for testing without hardware."""

import time
from typing import Dict, List, Tuple
import numpy as np

from .base import ArmDriver


class MockDriver(ArmDriver):
    """Mock driver that simulates robot behavior without hardware.

    Useful for testing API logic, plugin development, and integration
    testing without requiring access to physical Baxter robot.
    """

    def __init__(self):
        self._connected = False
        self._enabled = False

        # Simulated state for both arms
        self._joint_angles = {
            'right': {
                'right_s0': 0.0,
                'right_s1': -0.55,
                'right_e0': 0.0,
                'right_e1': 0.75,
                'right_w0': 0.0,
                'right_w1': 1.26,
                'right_w2': 0.0,
            },
            'left': {
                'left_s0': 0.0,
                'left_s1': -0.55,
                'left_e0': 0.0,
                'left_e1': 0.75,
                'left_w0': 0.0,
                'left_w1': 1.26,
                'left_w2': 0.0,
            }
        }

        # Simulated end-effector poses [x, y, z, roll, pitch, yaw]
        self._endpoint_poses = {
            'right': [0.6, -0.3, 0.2, 0.0, 0.0, 0.0],
            'left': [0.6, 0.3, 0.2, 0.0, 0.0, 0.0],
        }

        # Simulated gripper state (position, force)
        self._gripper_states = {
            'right': (100.0, 0.0),  # Open, no force
            'left': (100.0, 0.0),
        }

    def connect(self) -> bool:
        """Simulate connection."""
        print("MockDriver: Simulating connection to Baxter...")
        time.sleep(0.5)
        self._connected = True
        print("MockDriver: Connected successfully")
        return True

    def disconnect(self) -> bool:
        """Simulate disconnection."""
        print("MockDriver: Disconnecting...")
        self._connected = False
        self._enabled = False
        return True

    def enable(self) -> bool:
        """Simulate enabling robot."""
        if not self._connected:
            print("MockDriver: Not connected")
            return False

        print("MockDriver: Enabling robot...")
        time.sleep(0.3)
        self._enabled = True
        print("MockDriver: Robot enabled")
        return True

    def disable(self) -> bool:
        """Simulate disabling robot."""
        print("MockDriver: Disabling robot...")
        self._enabled = False
        return True

    def is_enabled(self) -> bool:
        """Check if mock robot is enabled."""
        return self._enabled

    def move_to_joint_positions(
        self, arm: str, positions: Dict[str, float], speed: float = 0.3, timeout: float = 15.0
    ) -> bool:
        """Simulate joint space motion."""
        if not self._enabled:
            print("MockDriver: Robot not enabled")
            return False

        if arm not in ['left', 'right']:
            print(f"MockDriver: Invalid arm: {arm}")
            return False

        print(f"MockDriver: Moving {arm} arm to joint positions...")
        print(f"  Target: {positions}")

        # Simulate motion time based on distance
        current = self._joint_angles[arm]
        max_delta = max(abs(positions.get(j, current[j]) - current[j]) for j in current.keys())
        motion_time = max_delta / speed * 2.0  # Rough estimate

        time.sleep(min(motion_time, 2.0))  # Cap at 2 seconds for testing

        # Update simulated state
        self._joint_angles[arm].update(positions)

        # Update endpoint pose (simplified FK)
        self._update_endpoint_pose(arm)

        print(f"MockDriver: {arm} arm reached target")
        return True

    def move_to_pose(
        self, arm: str, pose: List[float], speed: float = 0.3, timeout: float = 15.0
    ) -> bool:
        """Simulate Cartesian motion."""
        if not self._enabled:
            print("MockDriver: Robot not enabled")
            return False

        if arm not in ['left', 'right']:
            print(f"MockDriver: Invalid arm: {arm}")
            return False

        print(f"MockDriver: Moving {arm} arm to pose...")
        print(f"  Target: x={pose[0]:.3f}, y={pose[1]:.3f}, z={pose[2]:.3f}")

        # Simulate motion time
        current_pose = self._endpoint_poses[arm]
        distance = np.linalg.norm(np.array(pose[:3]) - np.array(current_pose[:3]))
        motion_time = distance / (speed * 0.5)  # Rough estimate

        time.sleep(min(motion_time, 2.0))

        # Update simulated pose
        self._endpoint_poses[arm] = pose.copy()

        print(f"MockDriver: {arm} arm reached target pose")
        return True

    def get_joint_angles(self, arm: str) -> Dict[str, float]:
        """Get simulated joint angles."""
        if arm not in self._joint_angles:
            return {}
        return self._joint_angles[arm].copy()

    def get_endpoint_pose(self, arm: str) -> List[float]:
        """Get simulated endpoint pose."""
        if arm not in self._endpoint_poses:
            return [0.0] * 6
        return self._endpoint_poses[arm].copy()

    def gripper_command(self, arm: str, action: str, force: float = 30.0) -> bool:
        """Simulate gripper control."""
        if not self._enabled:
            print("MockDriver: Robot not enabled")
            return False

        if arm not in ['left', 'right']:
            print(f"MockDriver: Invalid arm: {arm}")
            return False

        print(f"MockDriver: {arm} gripper {action}")

        if action == "calibrate":
            time.sleep(1.0)
            self._gripper_states[arm] = (100.0, 0.0)
            print(f"MockDriver: {arm} gripper calibrated")
        elif action == "open":
            time.sleep(0.5)
            self._gripper_states[arm] = (100.0, 0.0)
            print(f"MockDriver: {arm} gripper opened")
        elif action == "close":
            time.sleep(0.5)
            self._gripper_states[arm] = (0.0, force)
            print(f"MockDriver: {arm} gripper closed with force {force}")
        else:
            print(f"MockDriver: Unknown action: {action}")
            return False

        return True

    def get_gripper_state(self, arm: str) -> Tuple[float, float]:
        """Get simulated gripper state."""
        if arm not in self._gripper_states:
            return (0.0, 0.0)
        return self._gripper_states[arm]

    def capture_image(self, camera: str) -> bytes:
        """Simulate camera capture."""
        print(f"MockDriver: Capturing image from {camera}")
        # Return empty bytes for now
        # In a more sophisticated mock, could return a test image
        return b""

    def emergency_stop(self) -> bool:
        """Simulate emergency stop."""
        print("MockDriver: EMERGENCY STOP")
        self._enabled = False
        return True

    def _update_endpoint_pose(self, arm: str):
        """Update endpoint pose based on joint angles (simplified FK)."""
        # This is a very simplified forward kinematics simulation
        # In reality, Baxter FK is much more complex
        joints = self._joint_angles[arm]

        # Rough approximation based on joint angles
        s1 = joints.get(f'{arm}_s1', 0.0)
        e1 = joints.get(f'{arm}_e1', 0.0)

        # Simplified calculation
        reach = 0.6 + 0.2 * np.cos(s1) + 0.15 * np.cos(e1)
        height = 0.2 + 0.3 * np.sin(s1) + 0.2 * np.sin(e1)
        lateral = 0.3 if arm == 'left' else -0.3

        self._endpoint_poses[arm] = [reach, lateral, height, 0.0, 0.0, 0.0]
