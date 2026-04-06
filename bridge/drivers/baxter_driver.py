"""Baxter robot driver using baxter_interface SDK."""

import time
from typing import Dict, List, Tuple
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

    def __init__(self):
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

            # Initialize enhanced IK solver
            try:
                from ..ik_solver import EnhancedIKSolver
                self._ik_solver = EnhancedIKSolver(self)
                print("Enhanced IK solver initialized")
            except Exception as e:
                print(f"Warning: Could not initialize enhanced IK solver: {e}")
                self._ik_solver = None

            self._connected = True
            print("Successfully connected to Baxter robot")
            return True

        except Exception as e:
            print(f"Failed to connect to Baxter: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from Baxter."""
        try:
            if self._robot_enable and self._robot_enable.state().enabled:
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

    def move_to_pose(
        self, arm: str, pose: List[float], speed: float = 0.3, timeout: float = 15.0
    ) -> bool:
        """Move Baxter arm to Cartesian pose using IK.

        Uses enhanced IK solver with fallback strategies if available.
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
                joint_angles = self._ik_solver.solve_ik_with_fallback(arm, pose, max_attempts=5)
            else:
                # Fallback to basic IK
                print(f"Using basic IK solver for {arm} arm...")
                from geometry_msgs.msg import Pose, Point, Quaternion
                from tf.transformations import quaternion_from_euler

                target_pose = Pose()
                target_pose.position = Point(x=pose[0], y=pose[1], z=pose[2])

                quat = quaternion_from_euler(pose[3], pose[4], pose[5])
                target_pose.orientation = Quaternion(x=quat[0], y=quat[1], z=quat[2], w=quat[3])

                joint_angles = limb.ik_request(target_pose, limb.name + "_gripper")

            if joint_angles is None:
                print("IK solution not found")
                return False

            # Move to joint angles
            return self.move_to_joint_positions(arm, joint_angles, speed, timeout)

        except Exception as e:
            print(f"Failed to move to pose: {e}")
            return False

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
            from cv_bridge import CvBridge
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

            # Convert ROS Image to OpenCV format
            bridge = CvBridge()
            cv_image = bridge.imgmsg_to_cv2(image_msg, desired_encoding='bgr8')

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

    def emergency_stop(self) -> bool:
        """Execute emergency stop."""
        try:
            if self._robot_enable:
                self._robot_enable.stop()
            return True
        except Exception as e:
            print(f"Failed to execute emergency stop: {e}")
            return False
