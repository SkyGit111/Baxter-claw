"""MoveIt IK solver wrapper for Baxter robot.

This module provides an interface to use MoveIt's IK solver as an alternative
to the custom enhanced IK solver. MoveIt provides more robust IK solving with
better collision avoidance and path planning capabilities.
"""

from typing import Dict, List, Optional
import numpy as np


class MoveItIKSolver:
    """MoveIt-based IK solver for Baxter robot.

    This solver uses MoveIt's compute_ik service which typically provides
    more robust solutions than the basic Baxter IK service.
    """

    def __init__(self, driver):
        """Initialize MoveIt IK solver.

        Args:
            driver: Robot driver instance
        """
        self.driver = driver
        self._moveit_available = False
        self._check_moveit_availability()

    def _check_moveit_availability(self):
        """Check if MoveIt services are available."""
        try:
            import rospy
            from moveit_msgs.srv import GetPositionIK

            # Check if MoveIt compute_ik service is available
            service_name = '/compute_ik'
            try:
                rospy.wait_for_service(service_name, timeout=2.0)
                self._moveit_available = True
                print("[MoveItIK] MoveIt IK service is available")
            except rospy.ROSException:
                print("[MoveItIK] Warning: MoveIt IK service not available")
                print("[MoveItIK] Falling back to basic Baxter IK")
                self._moveit_available = False

        except ImportError:
            print("[MoveItIK] Warning: MoveIt Python packages not installed")
            print("[MoveItIK] Falling back to basic Baxter IK")
            self._moveit_available = False

    def solve_ik_with_fallback(
        self,
        arm: str,
        target_pose: List[float],
        max_attempts: int = 5,
        seed_positions: Optional[List[Dict[str, float]]] = None
    ) -> Optional[Dict[str, float]]:
        """Solve IK using MoveIt with fallback to basic IK.

        Args:
            arm: 'left' or 'right'
            target_pose: [x, y, z, roll, pitch, yaw]
            max_attempts: Maximum number of attempts
            seed_positions: Optional list of seed joint positions (not used by MoveIt)

        Returns:
            Joint angles dict if solution found, None otherwise
        """
        if self._moveit_available:
            return self._solve_with_moveit(arm, target_pose, max_attempts)
        else:
            # Fallback to basic Baxter IK
            return self._solve_with_basic_ik(arm, target_pose, max_attempts)

    def _solve_with_moveit(
        self,
        arm: str,
        target_pose: List[float],
        max_attempts: int = 5
    ) -> Optional[Dict[str, float]]:
        """Solve IK using MoveIt's compute_ik service.

        Args:
            arm: 'left' or 'right'
            target_pose: [x, y, z, roll, pitch, yaw]
            max_attempts: Maximum number of attempts

        Returns:
            Joint angles dict if solution found, None otherwise
        """
        try:
            import rospy
            from moveit_msgs.srv import GetPositionIK, GetPositionIKRequest
            from moveit_msgs.msg import PositionIKRequest
            from geometry_msgs.msg import PoseStamped, Pose, Point, Quaternion
            from sensor_msgs.msg import JointState
            from tf.transformations import quaternion_from_euler

            # Create service proxy
            compute_ik = rospy.ServiceProxy('/compute_ik', GetPositionIK)

            # Construct pose
            pose_stamped = PoseStamped()
            pose_stamped.header.frame_id = 'base'
            pose_stamped.header.stamp = rospy.Time.now()

            pose_stamped.pose.position = Point(
                x=target_pose[0],
                y=target_pose[1],
                z=target_pose[2]
            )

            quat = quaternion_from_euler(target_pose[3], target_pose[4], target_pose[5])
            pose_stamped.pose.orientation = Quaternion(
                x=quat[0],
                y=quat[1],
                z=quat[2],
                w=quat[3]
            )

            # Create IK request
            ik_request = PositionIKRequest()
            ik_request.group_name = f"{arm}_arm"  # MoveIt group name
            ik_request.pose_stamped = pose_stamped
            ik_request.timeout = rospy.Duration(5.0)
            ik_request.attempts = max_attempts

            # Get current joint state as seed
            limb = self.driver._limbs.get(arm)
            if limb:
                current_angles = limb.joint_angles()
                joint_state = JointState()
                joint_state.name = list(current_angles.keys())
                joint_state.position = list(current_angles.values())
                ik_request.robot_state.joint_state = joint_state

            # Call MoveIt IK service
            print(f"  [MoveItIK] Solving IK for {arm} arm using MoveIt...")
            request = GetPositionIKRequest()
            request.ik_request = ik_request

            response = compute_ik(request)

            if response.error_code.val == response.error_code.SUCCESS:
                # Extract joint angles from response
                joint_solution = {}
                for i, name in enumerate(response.solution.joint_state.name):
                    if arm in name:  # Only get joints for the specified arm
                        joint_solution[name] = response.solution.joint_state.position[i]

                print(f"  ✓ [MoveItIK] IK solved successfully")
                return joint_solution
            else:
                print(f"  ✗ [MoveItIK] IK failed with error code: {response.error_code.val}")
                return None

        except Exception as e:
            print(f"  ✗ [MoveItIK] Exception during IK solving: {e}")
            return None

    def _solve_with_basic_ik(
        self,
        arm: str,
        target_pose: List[float],
        max_attempts: int = 5
    ) -> Optional[Dict[str, float]]:
        """Fallback to basic Baxter IK service.

        Args:
            arm: 'left' or 'right'
            target_pose: [x, y, z, roll, pitch, yaw]
            max_attempts: Maximum number of attempts

        Returns:
            Joint angles dict if solution found, None otherwise
        """
        try:
            import rospy
            from geometry_msgs.msg import Pose, Point, Quaternion, PoseStamped
            from std_msgs.msg import Header
            from baxter_core_msgs.srv import SolvePositionIK, SolvePositionIKRequest
            from tf.transformations import quaternion_from_euler

            print(f"  [MoveItIK] Using basic Baxter IK as fallback...")

            # Create pose
            pose_msg = Pose()
            pose_msg.position = Point(x=target_pose[0], y=target_pose[1], z=target_pose[2])

            quat = quaternion_from_euler(target_pose[3], target_pose[4], target_pose[5])
            pose_msg.orientation = Quaternion(x=quat[0], y=quat[1], z=quat[2], w=quat[3])

            # Create IK service proxy
            ns = f"ExternalTools/{arm}/PositionKinematicsNode/IKService"
            iksvc = rospy.ServiceProxy(ns, SolvePositionIK)

            # Try IK
            hdr = Header(stamp=rospy.Time.now(), frame_id='base')
            ikreq = SolvePositionIKRequest()
            ikreq.pose_stamp.append(PoseStamped(header=hdr, pose=pose_msg))

            resp = iksvc(ikreq)
            if resp.result_type[0] != resp.RESULT_INVALID:
                joint_solution = dict(zip(resp.joints[0].name, resp.joints[0].position))
                print(f"  ✓ [MoveItIK] Basic IK solved successfully")
                return joint_solution
            else:
                print(f"  ✗ [MoveItIK] Basic IK failed")
                return None

        except Exception as e:
            print(f"  ✗ [MoveItIK] Exception during basic IK: {e}")
            return None

    def check_pose_reachable(self, arm: str, pose: List[float]) -> bool:
        """Check if a pose is reachable by solving IK.

        Args:
            arm: 'left' or 'right'
            pose: [x, y, z, roll, pitch, yaw]

        Returns:
            True if pose is reachable, False otherwise
        """
        result = self.solve_ik_with_fallback(arm, pose, max_attempts=3)
        return result is not None
