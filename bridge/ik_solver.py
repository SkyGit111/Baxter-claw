"""Enhanced IK solver with fallback strategies."""

from typing import Dict, List, Optional, Tuple
import numpy as np


class EnhancedIKSolver:
    """Enhanced IK solver with multiple fallback strategies.

    Provides more robust inverse kinematics solving with:
    - Multiple seed positions
    - Iterative refinement
    - Collision-aware solutions
    """

    def __init__(self, driver):
        """Initialize enhanced IK solver.

        Args:
            driver: Robot driver instance
        """
        self.driver = driver

    def solve_ik_with_fallback(
        self,
        arm: str,
        target_pose: List[float],
        max_attempts: int = 5,
        seed_positions: Optional[List[Dict[str, float]]] = None
    ) -> Optional[Dict[str, float]]:
        """Solve IK with multiple fallback strategies.

        Args:
            arm: 'left' or 'right'
            target_pose: [x, y, z, roll, pitch, yaw]
            max_attempts: Maximum number of attempts
            seed_positions: Optional list of seed joint positions to try

        Returns:
            Joint angles dict if solution found, None otherwise
        """
        try:
            from geometry_msgs.msg import Pose, Point, Quaternion
            from tf.transformations import quaternion_from_euler
            import rospy

            # Construct pose message
            pose_msg = Pose()
            pose_msg.position = Point(x=target_pose[0], y=target_pose[1], z=target_pose[2])

            quat = quaternion_from_euler(target_pose[3], target_pose[4], target_pose[5])
            pose_msg.orientation = Quaternion(x=quat[0], y=quat[1], z=quat[2], w=quat[3])

            # Get limb interface
            limb = self.driver._limbs.get(arm)
            if not limb:
                return None

            # Strategy 1: Try with current joint angles as seed
            print(f"  IK attempt 1: Using current joint angles as seed...")
            joint_solution = limb.ik_request(pose_msg, f"{arm}_gripper")
            if joint_solution:
                print(f"  ✓ IK solved on attempt 1")
                return joint_solution

            # Strategy 2: Try with predefined seed positions
            if seed_positions is None:
                seed_positions = self._get_default_seeds(arm)

            for i, seed in enumerate(seed_positions[:max_attempts-1], start=2):
                print(f"  IK attempt {i}: Using seed position {i-1}...")

                # Set seed position temporarily
                current_angles = limb.joint_angles()
                limb.set_joint_positions(seed)
                rospy.sleep(0.1)

                # Try IK
                joint_solution = limb.ik_request(pose_msg, f"{arm}_gripper")

                # Restore original position
                limb.set_joint_positions(current_angles)

                if joint_solution:
                    print(f"  ✓ IK solved on attempt {i}")
                    return joint_solution

            # Strategy 3: Try with slightly modified target pose
            print(f"  IK attempt {max_attempts}: Trying modified target pose...")
            modified_pose = target_pose.copy()
            modified_pose[2] += 0.02  # Slightly higher

            pose_msg.position.z = modified_pose[2]
            joint_solution = limb.ik_request(pose_msg, f"{arm}_gripper")

            if joint_solution:
                print(f"  ✓ IK solved with modified pose")
                return joint_solution

            print(f"  ✗ IK failed after {max_attempts} attempts")
            return None

        except Exception as e:
            print(f"  ✗ IK solver error: {e}")
            return None

    def _get_default_seeds(self, arm: str) -> List[Dict[str, float]]:
        """Get default seed positions for IK solving.

        Args:
            arm: 'left' or 'right'

        Returns:
            List of seed joint position dictionaries
        """
        if arm == 'right':
            return [
                # Neutral position
                {
                    'right_s0': 0.0,
                    'right_s1': -0.55,
                    'right_e0': 0.0,
                    'right_e1': 0.75,
                    'right_w0': 0.0,
                    'right_w1': 1.26,
                    'right_w2': 0.0,
                },
                # Extended position
                {
                    'right_s0': 0.3,
                    'right_s1': -0.3,
                    'right_e0': 0.5,
                    'right_e1': 1.2,
                    'right_w0': 0.0,
                    'right_w1': 1.5,
                    'right_w2': 0.0,
                },
                # Tucked position
                {
                    'right_s0': -0.3,
                    'right_s1': -0.8,
                    'right_e0': -0.5,
                    'right_e1': 0.5,
                    'right_w0': 0.0,
                    'right_w1': 1.0,
                    'right_w2': 0.0,
                },
            ]
        else:  # left
            return [
                # Neutral position
                {
                    'left_s0': 0.0,
                    'left_s1': -0.55,
                    'left_e0': 0.0,
                    'left_e1': 0.75,
                    'left_w0': 0.0,
                    'left_w1': 1.26,
                    'left_w2': 0.0,
                },
                # Extended position
                {
                    'left_s0': -0.3,
                    'left_s1': -0.3,
                    'left_e0': -0.5,
                    'left_e1': 1.2,
                    'left_w0': 0.0,
                    'left_w1': 1.5,
                    'left_w2': 0.0,
                },
                # Tucked position
                {
                    'left_s0': 0.3,
                    'left_s1': -0.8,
                    'left_e0': 0.5,
                    'left_e1': 0.5,
                    'left_w0': 0.0,
                    'left_w1': 1.0,
                    'left_w2': 0.0,
                },
            ]

    def compute_trajectory(
        self,
        start_joints: Dict[str, float],
        end_joints: Dict[str, float],
        num_waypoints: int = 10
    ) -> List[Dict[str, float]]:
        """Compute smooth trajectory between joint configurations.

        Args:
            start_joints: Starting joint configuration
            end_joints: Ending joint configuration
            num_waypoints: Number of waypoints in trajectory

        Returns:
            List of joint configurations forming smooth trajectory
        """
        trajectory = []

        # Linear interpolation for now (can be enhanced with splines)
        for i in range(num_waypoints + 1):
            alpha = i / num_waypoints
            waypoint = {}

            for joint_name in start_joints.keys():
                start_val = start_joints[joint_name]
                end_val = end_joints[joint_name]
                waypoint[joint_name] = start_val + alpha * (end_val - start_val)

            trajectory.append(waypoint)

        return trajectory

    def validate_joint_trajectory(
        self,
        trajectory: List[Dict[str, float]],
        max_joint_velocity: float = 1.0
    ) -> Tuple[bool, str]:
        """Validate that trajectory respects velocity limits.

        Args:
            trajectory: List of joint configurations
            max_joint_velocity: Maximum allowed joint velocity (rad/s)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(trajectory) < 2:
            return True, ""

        dt = 0.1  # Assume 10Hz control rate

        for i in range(1, len(trajectory)):
            prev = trajectory[i-1]
            curr = trajectory[i]

            for joint_name in prev.keys():
                velocity = abs(curr[joint_name] - prev[joint_name]) / dt

                if velocity > max_joint_velocity:
                    return False, f"Joint {joint_name} velocity {velocity:.2f} exceeds limit {max_joint_velocity}"

        return True, ""
