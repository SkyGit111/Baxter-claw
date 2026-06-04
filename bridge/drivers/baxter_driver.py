"""Baxter robot driver using baxter_interface SDK."""

import sys
import time
from typing import Dict, List, Tuple, Optional

# Add ROS Python paths ONLY for ROS imports, before importing numpy
_ros_paths = ['/opt/ros/noetic/lib/python3/dist-packages', '/usr/lib/python3/dist-packages']
for path in _ros_paths:
    if path not in sys.path:
        sys.path.append(path)

# Import numpy from conda environment first
import numpy as np

try:
    import rospy
    import baxter_interface
    from baxter_interface import CHECK_VERSION
    BAXTER_AVAILABLE = True
except ImportError:
    BAXTER_AVAILABLE = False
    print("Warning: baxter_interface not available. Use MockDriver for testing.")

from .base import ArmDriver


class BaxterDriver(ArmDriver):
    """Driver for Baxter robot using baxter_interface SDK.

    Requires ROS environment and Baxter SDK to be properly configured.
    """

    def __init__(self, use_depth_camera: bool = False, ik_solver_type: str = "enhanced"):
        """Initialize Baxter driver.

        Args:
            use_depth_camera: Whether to use RealSense D455 depth camera
            ik_solver_type: Type of IK solver to use ("enhanced", "moveit", or "basic")
        """
        if not BAXTER_AVAILABLE:
            raise RuntimeError(
                "baxter_interface not available. "
                "Ensure ROS and Baxter SDK are installed and sourced."
            )

        self._connected = False
        self._robot_enable = None
        self._limbs = {}
        self._grippers = {}
        self._ik_solver = None  # Will be initialized after connection
        self._ik_solver_type = ik_solver_type  # Store IK solver type

        # Depth camera support
        self._use_depth_camera = use_depth_camera
        self._depth_camera = None

        if use_depth_camera:
            try:
                from .realsense_driver import RealSenseDriver
                self._depth_camera = RealSenseDriver()
                print("RealSense D455 depth camera initialized")
            except Exception as e:
                print(f"Warning: Could not initialize depth camera: {e}")
                self._depth_camera = None

    def connect(self) -> bool:
        """Initialize ROS node and connect to Baxter."""
        try:
            # Initialize ROS node if not already initialized
            if not rospy.core.is_initialized():
                rospy.init_node('baxter_claw_bridge', anonymous=True)

            # Create robot enable interface
            self._robot_enable = baxter_interface.RobotEnable(CHECK_VERSION)

            # Initialize limb interfaces
            self._limbs['right'] = baxter_interface.Limb('right')
            self._limbs['left'] = baxter_interface.Limb('left')

            # Initialize gripper interfaces
            self._grippers['right'] = baxter_interface.Gripper('right', CHECK_VERSION)
            self._grippers['left'] = baxter_interface.Gripper('left', CHECK_VERSION)

            # Calibrate grippers
            print("Calibrating grippers...")
            try:
                self._grippers['right'].calibrate()
                print("  Right gripper calibrated")
            except Exception as e:
                print(f"  Warning: Right gripper calibration failed: {e}")

            try:
                self._grippers['left'].calibrate()
                print("  Left gripper calibrated")
            except Exception as e:
                print(f"  Warning: Left gripper calibration failed: {e}")

            # Initialize IK solver based on configuration
            try:
                if self._ik_solver_type == "moveit":
                    from ..moveit_ik_solver import MoveItIKSolver
                    self._ik_solver = MoveItIKSolver(self)
                    print("MoveIt IK solver initialized")
                elif self._ik_solver_type == "enhanced":
                    from ..ik_solver import EnhancedIKSolver
                    self._ik_solver = EnhancedIKSolver(self)
                    print("Enhanced IK solver initialized")
                else:  # "basic" or any other value
                    print("Using basic Baxter IK solver (no enhanced solver)")
                    self._ik_solver = None
            except Exception as e:
                print(f"Warning: Could not initialize {self._ik_solver_type} IK solver: {e}")
                print("Falling back to basic Baxter IK")
                self._ik_solver = None

            self._connected = True
            print("Successfully connected to Baxter robot")
            return True

        except Exception as e:
            print(f"Failed to connect to Baxter: {e}")
            return False

    def disconnect(self, keep_enabled: bool = False) -> bool:
        """Disconnect from Baxter.

        Args:
            keep_enabled: If True, keep robot enabled (prevents arm from falling)
        """
        try:
            if not keep_enabled and self._robot_enable and self._robot_enable.state().enabled:
                self.disable()
            self._connected = False
            return True
        except Exception as e:
            print(f"Error during disconnect: {e}")
            return False

    def enable(self) -> bool:
        """Enable Baxter robot."""
        if not self._connected:
            print("Not connected to robot")
            return False

        try:
            if not self._robot_enable.state().enabled:
                self._robot_enable.enable()
                time.sleep(0.5)  # Wait for enable to take effect
            return self._robot_enable.state().enabled
        except Exception as e:
            print(f"Failed to enable robot: {e}")
            return False

    def disable(self) -> bool:
        """Disable Baxter robot."""
        if not self._connected:
            return False

        try:
            if self._robot_enable.state().enabled:
                self._robot_enable.disable()
            return True
        except Exception as e:
            print(f"Failed to disable robot: {e}")
            return False

    def is_enabled(self) -> bool:
        """Check if Baxter is enabled."""
        if not self._connected or not self._robot_enable:
            return False
        return self._robot_enable.state().enabled

    def move_to_joint_positions(
        self, arm: str, positions: Dict[str, float], speed: float = 0.3, timeout: float = 15.0
    ) -> bool:
        """Move Baxter arm to joint positions."""
        if not self.is_enabled():
            print("Robot not enabled")
            return False

        if arm not in self._limbs:
            print(f"Invalid arm: {arm}")
            return False

        try:
            limb = self._limbs[arm]

            # Set joint position speed
            limb.set_joint_position_speed(speed)

            # Execute motion
            limb.move_to_joint_positions(positions, timeout=timeout)

            return True

        except Exception as e:
            print(f"Failed to move to joint positions: {e}")
            return False

    def check_pose_reachable(
        self, arm: str, pose: List[float], silent: bool = False
    ) -> bool:
        """Check if a pose is reachable by the specified arm without actually moving.

        Args:
            arm: 'left' or 'right'
            pose: [x, y, z, roll, pitch, yaw]
            silent: If True, suppress print output

        Returns:
            True if pose is reachable, False otherwise
        """
        if arm not in self._limbs:
            if not silent:
                print(f"Invalid arm: {arm}")
            return False

        try:
            # Try enhanced IK solver first if available
            if self._ik_solver:
                joint_angles = self._ik_solver.solve_ik_with_fallback(
                    arm, pose, max_attempts=5, silent=silent
                )
            else:
                # Fallback to basic IK using ROS service
                joint_angles = self._solve_basic_ik(arm, pose)

            return joint_angles is not None

        except Exception as e:
            if not silent:
                print(f"Reachability check failed: {e}")
            return False

    def select_best_arm_for_position(
        self, position: List[float], orientation: Optional[List[float]] = None
    ) -> Optional[str]:
        """Automatically select the best arm (left or right) for a target position.

        Selection criteria:
        1. Reachability: Can the arm reach the position?
        2. Y-coordinate preference:
           - Y > 0 (left side) → prefer left arm
           - Y < 0 (right side) → prefer right arm
        3. Distance: Choose arm closer to target

        Args:
            position: Target position [x, y, z]
            orientation: Optional orientation [roll, pitch, yaw], defaults to pointing down

        Returns:
            'left', 'right', or None if neither arm can reach
        """
        if orientation is None:
            orientation = [np.pi, 0.0, 0.0]  # Default: pointing down

        pose = position + orientation

        print(f"[ArmSelection] Selecting arm for position {position}")
        print(f"  Y-coordinate: {position[1]:.3f}m ({'left side' if position[1] > 0 else 'right side'})")

        # Check reachability for both arms
        left_reachable = self.check_pose_reachable('left', pose, silent=True)
        right_reachable = self.check_pose_reachable('right', pose, silent=True)

        print(f"  Left arm reachable: {left_reachable}")
        print(f"  Right arm reachable: {right_reachable}")

        # If only one arm can reach, use it
        if left_reachable and not right_reachable:
            print(f"  → Selected: left (only reachable arm)")
            return 'left'
        elif right_reachable and not left_reachable:
            print(f"  → Selected: right (only reachable arm)")
            return 'right'
        elif not left_reachable and not right_reachable:
            print(f"  → Selected: None (unreachable by both arms)")
            return None

        # Both arms can reach - use Y-coordinate preference
        if position[1] > 0.05:  # Left side (Y > 5cm)
            print(f"  → Selected: left (Y > 0, left side of workspace)")
            return 'left'
        elif position[1] < -0.05:  # Right side (Y < -5cm)
            print(f"  → Selected: right (Y < 0, right side of workspace)")
            return 'right'
        else:
            # Center region (-5cm < Y < 5cm) - choose based on distance
            left_pose = self.get_endpoint_pose('left')
            right_pose = self.get_endpoint_pose('right')

            if left_pose and right_pose:
                left_dist = np.linalg.norm(np.array(left_pose[:3]) - np.array(position))
                right_dist = np.linalg.norm(np.array(right_pose[:3]) - np.array(position))

                if left_dist < right_dist:
                    print(f"  → Selected: left (closer, dist={left_dist:.3f}m)")
                    return 'left'
                else:
                    print(f"  → Selected: right (closer, dist={right_dist:.3f}m)")
                    return 'right'

            # Fallback: prefer right arm for center
            print(f"  → Selected: right (center region, default)")
            return 'right'

    def check_pose_reachable(
        self, arm: str, pose: List[float], silent: bool = False
    ) -> bool:
        """Check if a pose is reachable by the specified arm without actually moving.

        This performs IK solving without executing motion, providing fast reachability check.

        Args:
            arm: 'left' or 'right'
            pose: [x, y, z, roll, pitch, yaw]
            silent: If True, suppress print output

        Returns:
            True if pose is reachable (IK solution exists), False otherwise
        """
        if arm not in self._limbs:
            if not silent:
                print(f"Invalid arm: {arm}")
            return False

        try:
            # Try enhanced IK solver first if available
            if self._ik_solver:
                # Note: solve_ik_with_fallback doesn't have silent parameter
                # We'll suppress output by temporarily redirecting stdout if silent=True
                if silent:
                    import os
                    import sys
                    # Redirect stdout to devnull
                    old_stdout = sys.stdout
                    sys.stdout = open(os.devnull, 'w')

                try:
                    joint_angles = self._ik_solver.solve_ik_with_fallback(
                        arm, pose, max_attempts=5
                    )
                finally:
                    if silent:
                        sys.stdout.close()
                        sys.stdout = old_stdout
            else:
                # Fallback to basic IK using ROS service
                joint_angles = self._solve_basic_ik(arm, pose)

            return joint_angles is not None

        except Exception as e:
            if not silent:
                print(f"Reachability check failed: {e}")
            return False

    def select_arm_by_y_coordinate(
        self, position: List[float], y_threshold: float = 0.0
    ) -> str:
        """Select arm based on Y-coordinate with a threshold.

        Simple rule:
        - Y < y_threshold → right arm
        - Y >= y_threshold → left arm

        Args:
            position: Target position [x, y, z]
            y_threshold: Y-coordinate threshold (default: 0.0m)

        Returns:
            'left' or 'right'
        """
        y = position[1]

        if y < y_threshold:
            return 'right'
        else:
            return 'left'

    def move_to_pose(
        self, arm: str, pose: List[float], speed: float = 0.3, timeout: float = 15.0,
        retry_with_perturbation: bool = True
    ) -> bool:
        """Move Baxter arm to Cartesian pose using IK.

        Uses enhanced IK solver with fallback strategies if available.

        Args:
            arm: 'left' or 'right'
            pose: [x, y, z, roll, pitch, yaw]
            speed: Motion speed (0-1)
            timeout: Timeout in seconds
            retry_with_perturbation: If True, retry with position perturbations on failure
        """
        if not self.is_enabled():
            print("Robot not enabled")
            return False

        if arm not in self._limbs:
            print(f"Invalid arm: {arm}")
            return False

        try:
            limb = self._limbs[arm]

            # Set joint position speed
            limb.set_joint_position_speed(speed)

            # Try enhanced IK solver first if available
            if self._ik_solver:
                print(f"Using enhanced IK solver for {arm} arm...")
                joint_angles = self._ik_solver.solve_ik_with_fallback(arm, pose, max_attempts=10)
            else:
                # Fallback to basic IK using ROS service
                print(f"Using basic IK solver for {arm} arm...")
                joint_angles = self._solve_basic_ik(arm, pose)

            # If IK failed and retry is enabled, try with perturbations
            if joint_angles is None and retry_with_perturbation:
                print("  Initial IK failed, trying with position perturbations...")
                joint_angles = self._solve_ik_with_perturbations(arm, pose)

            if joint_angles is None:
                print("  ✗ IK solution not found after all attempts")
                return False

            # Move to joint angles
            return self.move_to_joint_positions(arm, joint_angles, speed, timeout)

        except Exception as e:
            print(f"Failed to move to pose: {e}")
            return False

    def _solve_basic_ik(self, arm: str, pose: List[float]):
        """Solve IK using basic ROS service."""
        from geometry_msgs.msg import Pose, Point, Quaternion, PoseStamped
        from std_msgs.msg import Header
        from baxter_core_msgs.srv import SolvePositionIK, SolvePositionIKRequest
        from tf.transformations import quaternion_from_euler

        try:
            # Create IK service proxy
            ns = f"ExternalTools/{arm}/PositionKinematicsNode/IKService"
            iksvc = rospy.ServiceProxy(ns, SolvePositionIK)

            # Create pose
            target_pose = Pose()
            target_pose.position = Point(x=pose[0], y=pose[1], z=pose[2])
            quat = quaternion_from_euler(pose[3], pose[4], pose[5])
            target_pose.orientation = Quaternion(x=quat[0], y=quat[1], z=quat[2], w=quat[3])

            # Create IK request
            hdr = Header(stamp=rospy.Time.now(), frame_id='base')
            ikreq = SolvePositionIKRequest()
            ikreq.pose_stamp.append(PoseStamped(header=hdr, pose=target_pose))

            resp = iksvc(ikreq)
            if resp.result_type[0] != resp.RESULT_INVALID:
                # Convert response to joint angles dict
                return dict(zip(resp.joints[0].name, resp.joints[0].position))
            else:
                return None
        except Exception as e:
            print(f"  ✗ IK service call failed: {e}")
            return None

    def _solve_ik_with_perturbations(self, arm: str, pose: List[float], max_attempts: int = 20):
        """Try to solve IK with small position perturbations.

        Strategy:
        1. Try small perturbations in X, Y, Z (±1cm, ±2cm)
        2. Try small orientation adjustments (±5°, ±10°)
        3. Try combinations of position and orientation changes
        """
        import numpy as np

        print(f"  Attempting IK with perturbations (max {max_attempts} attempts)...")

        # Perturbation strategies (in order of preference)
        perturbations = [
            # Small position adjustments
            ([0.01, 0, 0], [0, 0, 0]),      # +1cm X
            ([-0.01, 0, 0], [0, 0, 0]),     # -1cm X
            ([0, 0.01, 0], [0, 0, 0]),      # +1cm Y
            ([0, -0.01, 0], [0, 0, 0]),     # -1cm Y
            ([0, 0, 0.01], [0, 0, 0]),      # +1cm Z
            ([0, 0, -0.01], [0, 0, 0]),     # -1cm Z

            # Larger position adjustments
            ([0.02, 0, 0], [0, 0, 0]),      # +2cm X
            ([-0.02, 0, 0], [0, 0, 0]),     # -2cm X
            ([0, 0.02, 0], [0, 0, 0]),      # +2cm Y
            ([0, -0.02, 0], [0, 0, 0]),     # -2cm Y

            # Orientation adjustments (5 degrees)
            ([0, 0, 0], [np.radians(5), 0, 0]),
            ([0, 0, 0], [-np.radians(5), 0, 0]),
            ([0, 0, 0], [0, np.radians(5), 0]),
            ([0, 0, 0], [0, -np.radians(5), 0]),

            # Combined adjustments
            ([0.01, 0.01, 0], [0, 0, 0]),
            ([-0.01, 0.01, 0], [0, 0, 0]),
            ([0.01, -0.01, 0], [0, 0, 0]),
            ([0, 0, 0.02], [np.radians(5), 0, 0]),
            ([0.01, 0, 0.01], [0, 0, 0]),
            ([0, 0.01, 0.01], [0, 0, 0]),
        ]

        for i, (pos_delta, ori_delta) in enumerate(perturbations[:max_attempts]):
            perturbed_pose = pose.copy()
            perturbed_pose[0] += pos_delta[0]
            perturbed_pose[1] += pos_delta[1]
            perturbed_pose[2] += pos_delta[2]
            perturbed_pose[3] += ori_delta[0]
            perturbed_pose[4] += ori_delta[1]
            perturbed_pose[5] += ori_delta[2]

            # Try IK with perturbed pose
            if self._ik_solver:
                joint_angles = self._ik_solver.solve_ik_with_fallback(arm, perturbed_pose, max_attempts=3)
            else:
                joint_angles = self._solve_basic_ik(arm, perturbed_pose)

            if joint_angles is not None:
                print(f"  ✓ IK solved with perturbation #{i+1}")
                print(f"    Position delta: [{pos_delta[0]*100:+.1f}, {pos_delta[1]*100:+.1f}, {pos_delta[2]*100:+.1f}]cm")
                if any(ori_delta):
                    print(f"    Orientation delta: [{np.degrees(ori_delta[0]):+.1f}, {np.degrees(ori_delta[1]):+.1f}, {np.degrees(ori_delta[2]):+.1f}]°")
                return joint_angles

        return None

    def get_joint_angles(self, arm: str) -> Dict[str, float]:
        """Get current joint angles."""
        if arm not in self._limbs:
            return {}

        try:
            return self._limbs[arm].joint_angles()
        except Exception as e:
            print(f"Failed to get joint angles: {e}")
            return {}

    def get_endpoint_pose(self, arm: str) -> List[float]:
        """Get current end-effector pose."""
        if arm not in self._limbs:
            return [0.0] * 6

        try:
            limb = self._limbs[arm]
            pose = limb.endpoint_pose()

            # Extract position
            pos = pose['position']
            x, y, z = pos.x, pos.y, pos.z

            # Extract orientation (quaternion) and convert to RPY
            ori = pose['orientation']
            from tf.transformations import euler_from_quaternion
            roll, pitch, yaw = euler_from_quaternion([ori.x, ori.y, ori.z, ori.w])

            return [x, y, z, roll, pitch, yaw]

        except Exception as e:
            print(f"Failed to get endpoint pose: {e}")
            return [0.0] * 6

    def gripper_command(self, arm: str, action: str, force: float = 30.0) -> bool:
        """Control Baxter gripper."""
        if arm not in self._grippers:
            print(f"Invalid arm: {arm}")
            return False

        try:
            gripper = self._grippers[arm]

            if action == "calibrate":
                gripper.calibrate()
                return True
            elif action == "open":
                gripper.open()
                return True
            elif action == "close":
                gripper.close()
                # Optionally set holding force
                # Note: Baxter grippers have limited force control
                return True
            else:
                print(f"Unknown gripper action: {action}")
                return False

        except Exception as e:
            print(f"Failed to execute gripper command: {e}")
            return False

    def get_gripper_state(self, arm: str) -> Tuple[float, float]:
        """Get gripper position and force."""
        if arm not in self._grippers:
            return (0.0, 0.0)

        try:
            gripper = self._grippers[arm]
            position = gripper.position()  # Returns position in mm
            force = gripper.force()  # Returns force reading

            # Normalize position to 0-100 scale (0=closed, 100=open)
            # Baxter gripper range is approximately 0-100mm
            position_normalized = min(100.0, max(0.0, position))

            return (position_normalized, force)

        except Exception as e:
            print(f"Failed to get gripper state: {e}")
            return (0.0, 0.0)

    def capture_image(self, camera: str) -> bytes:
        """Capture image from Baxter camera.

        Args:
            camera: Camera name ('left_hand', 'right_hand', 'head')

        Returns:
            JPEG image data as bytes
        """
        try:
            from sensor_msgs.msg import Image
            import rospy
            import numpy as np

            # Import cv2 from conda environment
            import cv2

            # Map camera names to ROS topics
            camera_topics = {
                'left_hand': '/cameras/left_hand_camera/image',
                'right_hand': '/cameras/right_hand_camera/image',
                'head': '/cameras/head_camera/image',
            }

            if camera not in camera_topics:
                print(f"Unknown camera: {camera}. Valid options: {list(camera_topics.keys())}")
                return b""

            topic = camera_topics[camera]

            # Wait for image message (timeout 5 seconds)
            print(f"Capturing image from {camera}...")
            image_msg = rospy.wait_for_message(topic, Image, timeout=5.0)

            # Convert ROS Image to numpy array manually (avoid cv_bridge GDAL conflict)
            if image_msg.encoding == 'bgr8':
                dtype = np.uint8
                channels = 3
            elif image_msg.encoding == 'rgb8':
                dtype = np.uint8
                channels = 3
            elif image_msg.encoding == 'bgra8':
                dtype = np.uint8
                channels = 4
            elif image_msg.encoding == 'rgba8':
                dtype = np.uint8
                channels = 4
            elif image_msg.encoding == 'mono8':
                dtype = np.uint8
                channels = 1
            else:
                print(f"Unsupported encoding: {image_msg.encoding}")
                return b""

            # Reshape raw data to image
            cv_image = np.frombuffer(image_msg.data, dtype=dtype).reshape(
                image_msg.height, image_msg.width, channels
            )

            # Convert to BGR for JPEG encoding
            if image_msg.encoding == 'rgb8':
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
            elif image_msg.encoding == 'rgba8':
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGBA2BGR)
            elif image_msg.encoding == 'bgra8':
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGRA2BGR)
            elif image_msg.encoding == 'mono8':
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2BGR)

            # Encode as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
            success, jpeg_buffer = cv2.imencode('.jpg', cv_image, encode_param)

            if not success:
                print("Failed to encode image as JPEG")
                return b""

            print(f"Successfully captured image from {camera} ({len(jpeg_buffer.tobytes())} bytes)")
            return jpeg_buffer.tobytes()

        except Exception as e:
            print(f"Failed to capture image from {camera}: {e}")
            return b""

    def capture_rgbd(self):
        """Capture RGB + Depth images from depth camera.

        Returns:
            Tuple of (rgb_image, depth_image) or (None, None) if unavailable
        """
        if not self._depth_camera:
            print("Depth camera not available")
            return None, None

        try:
            return self._depth_camera.capture_rgbd()
        except Exception as e:
            print(f"Failed to capture RGBD: {e}")
            return None, None

    def get_depth_camera_driver(self):
        """Get the depth camera driver instance.

        Returns:
            RealSenseDriver instance or None
        """
        return self._depth_camera

    def has_depth_camera(self) -> bool:
        """Check if depth camera is available.

        Returns:
            True if depth camera is initialized and available
        """
        return self._depth_camera is not None

    def emergency_stop(self) -> bool:
        """Execute emergency stop."""
        try:
            if self._robot_enable:
                self._robot_enable.stop()
            return True
        except Exception as e:
            print(f"Failed to execute emergency stop: {e}")
            return False
