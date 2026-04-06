"""High-level action primitives for Baxter robot."""

from typing import Dict, List, Optional
import time

from .drivers.base import ArmDriver
from .safety import SafetyValidator
from .vlm_client import VLMClient


class BaxterPrimitives:
    """High-level action primitives for intuitive robot control.

    These primitives abstract low-level motion control into semantic
    actions that can be easily invoked by LLM agents.
    """

    def __init__(self, driver: ArmDriver, safety: SafetyValidator, vlm_client: Optional[VLMClient] = None):
        """Initialize primitives.

        Args:
            driver: Robot driver instance
            safety: Safety validator instance
            vlm_client: Optional VLM client for vision features
        """
        self.driver = driver
        self.safety = safety
        self.vlm_client = vlm_client

        # Predefined home positions for each arm
        self.home_positions = {
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

    def pick(
        self,
        arm: str,
        position: List[float],
        approach_height: float = 0.1,
        speed: float = 0.3
    ) -> Dict:
        """Pick up an object at the specified position.

        Execution sequence:
        1. Move to pre-grasp pose (above target)
        2. Open gripper
        3. Descend to target position
        4. Close gripper
        5. Lift object

        Args:
            arm: 'left' or 'right'
            position: Target position [x, y, z] in meters
            approach_height: Height offset for pre-grasp pose (meters)
            speed: Motion speed ratio (0-1)

        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        try:
            print(f"[Primitive] Pick: arm={arm}, position={position}")

            # Validate inputs
            if len(position) != 3:
                return {"success": False, "message": "Position must be [x, y, z]"}

            # Default orientation (gripper pointing down)
            orientation = [0.0, 0.0, 0.0]

            # Step 1: Move to pre-grasp pose
            pre_grasp_pose = position.copy()
            pre_grasp_pose[2] += approach_height

            is_safe, msg = self.safety.check_workspace(arm, pre_grasp_pose + orientation)
            if not is_safe:
                return {"success": False, "message": f"Pre-grasp pose unsafe: {msg}"}

            print(f"  Moving to pre-grasp pose: {pre_grasp_pose}")
            success = self.driver.move_to_pose(arm, pre_grasp_pose + orientation, speed)
            if not success:
                return {"success": False, "message": "Failed to reach pre-grasp pose"}

            # Step 2: Open gripper
            print("  Opening gripper")
            self.driver.gripper_command(arm, "open")
            time.sleep(0.5)

            # Step 3: Descend to target
            target_pose = position + orientation
            is_safe, msg = self.safety.check_workspace(arm, target_pose)
            if not is_safe:
                return {"success": False, "message": f"Target pose unsafe: {msg}"}

            print(f"  Descending to target: {position}")
            success = self.driver.move_to_pose(arm, target_pose, speed * 0.5)
            if not success:
                return {"success": False, "message": "Failed to reach target"}

            # Step 4: Close gripper
            print("  Closing gripper")
            self.driver.gripper_command(arm, "close", force=30.0)
            time.sleep(0.8)

            # Step 5: Lift
            print("  Lifting object")
            success = self.driver.move_to_pose(arm, pre_grasp_pose + orientation, speed * 0.5)
            if not success:
                return {"success": False, "message": "Failed to lift object"}

            return {
                "success": True,
                "message": f"Successfully picked object at {position}",
                "arm": arm,
                "final_position": pre_grasp_pose
            }

        except Exception as e:
            return {"success": False, "message": f"Pick failed: {str(e)}"}

    def place(
        self,
        arm: str,
        position: List[float],
        approach_height: float = 0.1,
        speed: float = 0.3
    ) -> Dict:
        """Place the held object at the specified position.

        Execution sequence:
        1. Move to pre-place pose (above target)
        2. Descend to target position
        3. Open gripper
        4. Retract upward

        Args:
            arm: 'left' or 'right'
            position: Target position [x, y, z] in meters
            approach_height: Height offset for pre-place pose (meters)
            speed: Motion speed ratio (0-1)

        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        try:
            print(f"[Primitive] Place: arm={arm}, position={position}")

            if len(position) != 3:
                return {"success": False, "message": "Position must be [x, y, z]"}

            orientation = [0.0, 0.0, 0.0]

            # Step 1: Move to pre-place pose
            pre_place_pose = position.copy()
            pre_place_pose[2] += approach_height

            is_safe, msg = self.safety.check_workspace(arm, pre_place_pose + orientation)
            if not is_safe:
                return {"success": False, "message": f"Pre-place pose unsafe: {msg}"}

            print(f"  Moving to pre-place pose: {pre_place_pose}")
            success = self.driver.move_to_pose(arm, pre_place_pose + orientation, speed)
            if not success:
                return {"success": False, "message": "Failed to reach pre-place pose"}

            # Step 2: Descend to target
            target_pose = position + orientation
            is_safe, msg = self.safety.check_workspace(arm, target_pose)
            if not is_safe:
                return {"success": False, "message": f"Target pose unsafe: {msg}"}

            print(f"  Descending to target: {position}")
            success = self.driver.move_to_pose(arm, target_pose, speed * 0.5)
            if not success:
                return {"success": False, "message": "Failed to reach target"}

            # Step 3: Open gripper
            print("  Opening gripper")
            self.driver.gripper_command(arm, "open")
            time.sleep(0.8)

            # Step 4: Retract
            print("  Retracting")
            success = self.driver.move_to_pose(arm, pre_place_pose + orientation, speed * 0.5)
            if not success:
                return {"success": False, "message": "Failed to retract"}

            return {
                "success": True,
                "message": f"Successfully placed object at {position}",
                "arm": arm,
                "final_position": pre_place_pose
            }

        except Exception as e:
            return {"success": False, "message": f"Place failed: {str(e)}"}

    def move_to(
        self,
        arm: str,
        position: List[float],
        orientation: Optional[List[float]] = None,
        speed: float = 0.3
    ) -> Dict:
        """Move end-effector to specified pose.

        Args:
            arm: 'left' or 'right'
            position: Target position [x, y, z] in meters
            orientation: Target orientation [roll, pitch, yaw] in radians
                        If None, uses default (gripper pointing down)
            speed: Motion speed ratio (0-1)

        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        try:
            print(f"[Primitive] MoveTo: arm={arm}, position={position}")

            if len(position) != 3:
                return {"success": False, "message": "Position must be [x, y, z]"}

            if orientation is None:
                orientation = [0.0, 0.0, 0.0]
            elif len(orientation) != 3:
                return {"success": False, "message": "Orientation must be [roll, pitch, yaw]"}

            pose = position + orientation

            # Safety check
            is_safe, msg = self.safety.check_workspace(arm, pose)
            if not is_safe:
                return {"success": False, "message": f"Target pose unsafe: {msg}"}

            # Execute motion
            success = self.driver.move_to_pose(arm, pose, speed)
            if not success:
                return {"success": False, "message": "Failed to reach target pose"}

            return {
                "success": True,
                "message": f"Successfully moved to {position}",
                "arm": arm,
                "final_position": position
            }

        except Exception as e:
            return {"success": False, "message": f"MoveTo failed: {str(e)}"}

    def home(self, arm: str, speed: float = 0.3) -> Dict:
        """Return arm to predefined home position.

        Args:
            arm: 'left' or 'right'
            speed: Motion speed ratio (0-1)

        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        try:
            print(f"[Primitive] Home: arm={arm}")

            if arm not in self.home_positions:
                return {"success": False, "message": f"Unknown arm: {arm}"}

            positions = self.home_positions[arm]

            # Safety check
            is_safe, msg = self.safety.check_joint_limits(arm, positions)
            if not is_safe:
                return {"success": False, "message": f"Home position unsafe: {msg}"}

            # Execute motion
            success = self.driver.move_to_joint_positions(arm, positions, speed)
            if not success:
                return {"success": False, "message": "Failed to reach home position"}

            return {
                "success": True,
                "message": f"{arm.capitalize()} arm returned to home position",
                "arm": arm
            }

        except Exception as e:
            return {"success": False, "message": f"Home failed: {str(e)}"}

    async def pick_by_name(
        self,
        arm: str,
        object_name: str,
        camera: str = "right_hand",
        approach_height: float = 0.1,
        speed: float = 0.3
    ) -> Dict:
        """Pick up an object by name using vision.

        Args:
            arm: 'left' or 'right'
            object_name: Name of object to pick (e.g., "red cup", "blue box")
            camera: Camera to use for vision
            approach_height: Height offset for pre-grasp pose
            speed: Motion speed ratio (0-1)

        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        try:
            if not self.vlm_client:
                return {"success": False, "message": "VLM client not configured"}

            print(f"[Primitive] PickByName: arm={arm}, object={object_name}")

            # Capture image
            print(f"  Capturing image from {camera}...")
            image_bytes = self.driver.capture_image(camera)
            if not image_bytes:
                return {"success": False, "message": "Failed to capture image"}

            # Locate object using VLM
            print(f"  Locating {object_name} in image...")
            workspace_bounds = {
                'x': self.safety.workspace_limits['x'],
                'y': self.safety.workspace_limits['y'],
                'z': self.safety.workspace_limits['z'],
            }

            location = await self.vlm_client.locate_object(
                image_bytes,
                object_name,
                workspace_bounds
            )

            if not location or not location['found']:
                return {
                    "success": False,
                    "message": f"Could not locate {object_name} in image",
                    "vlm_response": location
                }

            if location['confidence'] < 50:
                return {
                    "success": False,
                    "message": f"Low confidence ({location['confidence']}%) in object location",
                    "vlm_response": location
                }

            # Extract position
            position = location['position']
            print(f"  Found {object_name} at position {position} (confidence: {location['confidence']}%)")

            # Execute pick
            result = self.pick(arm, position, approach_height, speed)

            # Add vision info to result
            result['vlm_response'] = location
            result['object_name'] = object_name

            return result

        except Exception as e:
            return {"success": False, "message": f"PickByName failed: {str(e)}"}

    async def locate_object(
        self,
        object_name: str,
        camera: str = "right_hand"
    ) -> Dict:
        """Locate an object using vision without moving the robot.

        Args:
            object_name: Name of object to locate
            camera: Camera to use for vision

        Returns:
            Dict with object location information
        """
        try:
            if not self.vlm_client:
                return {"success": False, "message": "VLM client not configured"}

            print(f"[Primitive] LocateObject: object={object_name}")

            # Capture image
            print(f"  Capturing image from {camera}...")
            image_bytes = self.driver.capture_image(camera)
            if not image_bytes:
                return {"success": False, "message": "Failed to capture image"}

            # Locate object using VLM
            print(f"  Locating {object_name} in image...")
            workspace_bounds = {
                'x': self.safety.workspace_limits['x'],
                'y': self.safety.workspace_limits['y'],
                'z': self.safety.workspace_limits['z'],
            }

            location = await self.vlm_client.locate_object(
                image_bytes,
                object_name,
                workspace_bounds
            )

            if not location:
                return {"success": False, "message": "VLM request failed"}

            return {
                "success": location['found'],
                "message": f"Object {'found' if location['found'] else 'not found'}",
                "object_name": object_name,
                "position": location['position'],
                "confidence": location['confidence'],
                "description": location['description'],
                "bounding_box": location['bounding_box']
            }

        except Exception as e:
            return {"success": False, "message": f"LocateObject failed: {str(e)}"}

    async def describe_scene(self, camera: str = "right_hand") -> Dict:
        """Get a description of the current scene.

        Args:
            camera: Camera to use for vision

        Returns:
            Dict with scene description
        """
        try:
            if not self.vlm_client:
                return {"success": False, "message": "VLM client not configured"}

            print(f"[Primitive] DescribeScene: camera={camera}")

            # Capture image
            image_bytes = self.driver.capture_image(camera)
            if not image_bytes:
                return {"success": False, "message": "Failed to capture image"}

            # Get scene description
            description = await self.vlm_client.describe_scene(image_bytes)

            return {
                "success": True,
                "message": "Scene described successfully",
                "description": description
            }

        except Exception as e:
            return {"success": False, "message": f"DescribeScene failed: {str(e)}"}

    async def identify_objects(self, camera: str = "right_hand") -> Dict:
        """Identify all objects in the scene.

        Args:
            camera: Camera to use for vision

        Returns:
            Dict with list of identified objects
        """
        try:
            if not self.vlm_client:
                return {"success": False, "message": "VLM client not configured"}

            print(f"[Primitive] IdentifyObjects: camera={camera}")

            # Capture image
            image_bytes = self.driver.capture_image(camera)
            if not image_bytes:
                return {"success": False, "message": "Failed to capture image"}

            # Identify objects
            objects = await self.vlm_client.identify_objects(image_bytes)

            return {
                "success": True,
                "message": f"Identified {len(objects)} objects",
                "objects": objects
            }

        except Exception as e:
            return {"success": False, "message": f"IdentifyObjects failed: {str(e)}"}

    # Dual-arm coordination primitives

    def bimanual_pick(
        self,
        object_position: List[float],
        left_offset: List[float] = [-0.05, 0.0, 0.0],
        right_offset: List[float] = [0.05, 0.0, 0.0],
        approach_height: float = 0.1,
        speed: float = 0.2
    ) -> Dict:
        """Pick up a large object using both arms simultaneously.

        Args:
            object_position: Center position of object [x, y, z]
            left_offset: Offset for left gripper from center
            right_offset: Offset for right gripper from center
            approach_height: Height offset for pre-grasp
            speed: Motion speed (slower for coordination)

        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        try:
            print(f"[Primitive] BimanualPick: center={object_position}")

            if len(object_position) != 3:
                return {"success": False, "message": "Position must be [x, y, z]"}

            # Calculate grasp positions for each arm
            left_pos = [
                object_position[0] + left_offset[0],
                object_position[1] + left_offset[1],
                object_position[2] + left_offset[2]
            ]
            right_pos = [
                object_position[0] + right_offset[0],
                object_position[1] + right_offset[1],
                object_position[2] + right_offset[2]
            ]

            # Check collision between arms
            if not self._check_arm_collision(left_pos, right_pos):
                return {"success": False, "message": "Arms would collide at target positions"}

            # Pre-grasp positions
            left_pre = left_pos.copy()
            left_pre[2] += approach_height
            right_pre = right_pos.copy()
            right_pre[2] += approach_height

            orientation = [0.0, 0.0, 0.0]

            # Step 1: Move both arms to pre-grasp positions simultaneously
            print("  Moving both arms to pre-grasp positions...")
            left_safe, msg = self.safety.check_workspace('left', left_pre + orientation)
            if not left_safe:
                return {"success": False, "message": f"Left pre-grasp unsafe: {msg}"}

            right_safe, msg = self.safety.check_workspace('right', right_pre + orientation)
            if not right_safe:
                return {"success": False, "message": f"Right pre-grasp unsafe: {msg}"}

            # Move simultaneously (in real implementation, use threading or async)
            success_left = self.driver.move_to_pose('left', left_pre + orientation, speed)
            success_right = self.driver.move_to_pose('right', right_pre + orientation, speed)

            if not (success_left and success_right):
                return {"success": False, "message": "Failed to reach pre-grasp positions"}

            # Step 2: Open both grippers
            print("  Opening both grippers...")
            self.driver.gripper_command('left', 'open')
            self.driver.gripper_command('right', 'open')
            time.sleep(0.5)

            # Step 3: Descend both arms simultaneously
            print("  Descending to grasp positions...")
            success_left = self.driver.move_to_pose('left', left_pos + orientation, speed * 0.5)
            success_right = self.driver.move_to_pose('right', right_pos + orientation, speed * 0.5)

            if not (success_left and success_right):
                return {"success": False, "message": "Failed to reach grasp positions"}

            # Step 4: Close both grippers
            print("  Closing both grippers...")
            self.driver.gripper_command('left', 'close', force=30.0)
            self.driver.gripper_command('right', 'close', force=30.0)
            time.sleep(0.8)

            # Step 5: Lift both arms simultaneously
            print("  Lifting object...")
            success_left = self.driver.move_to_pose('left', left_pre + orientation, speed * 0.5)
            success_right = self.driver.move_to_pose('right', right_pre + orientation, speed * 0.5)

            if not (success_left and success_right):
                return {"success": False, "message": "Failed to lift object"}

            return {
                "success": True,
                "message": f"Successfully picked object with both arms",
                "left_position": left_pos,
                "right_position": right_pos
            }

        except Exception as e:
            return {"success": False, "message": f"BimanualPick failed: {str(e)}"}

    def handover(
        self,
        from_arm: str,
        to_arm: str,
        handover_position: Optional[List[float]] = None,
        speed: float = 0.3
    ) -> Dict:
        """Hand over an object from one arm to the other.

        Args:
            from_arm: Arm currently holding object ('left' or 'right')
            to_arm: Arm to receive object ('left' or 'right')
            handover_position: Optional handover position, auto-calculated if None
            speed: Motion speed

        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        try:
            print(f"[Primitive] Handover: {from_arm} → {to_arm}")

            if from_arm == to_arm:
                return {"success": False, "message": "Cannot handover to same arm"}

            if from_arm not in ['left', 'right'] or to_arm not in ['left', 'right']:
                return {"success": False, "message": "Invalid arm specification"}

            # Calculate handover position if not provided
            if handover_position is None:
                # Use center position between arms
                handover_position = [0.6, 0.0, 0.3]  # Center front position

            orientation = [0.0, 0.0, 0.0]

            # Safety check
            is_safe, msg = self.safety.check_workspace(from_arm, handover_position + orientation)
            if not is_safe:
                return {"success": False, "message": f"Handover position unsafe for {from_arm}: {msg}"}

            is_safe, msg = self.safety.check_workspace(to_arm, handover_position + orientation)
            if not is_safe:
                return {"success": False, "message": f"Handover position unsafe for {to_arm}: {msg}"}

            # Step 1: Move from_arm to handover position
            print(f"  Moving {from_arm} arm to handover position...")
            success = self.driver.move_to_pose(from_arm, handover_position + orientation, speed)
            if not success:
                return {"success": False, "message": f"Failed to move {from_arm} to handover position"}

            # Step 2: Move to_arm to handover position (slightly offset to avoid collision)
            to_offset = handover_position.copy()
            to_offset[2] -= 0.05  # Slightly below to grasp from underneath

            print(f"  Moving {to_arm} arm to receive position...")
            success = self.driver.move_to_pose(to_arm, to_offset + orientation, speed)
            if not success:
                return {"success": False, "message": f"Failed to move {to_arm} to receive position"}

            # Step 3: Close receiving gripper
            print(f"  Closing {to_arm} gripper...")
            self.driver.gripper_command(to_arm, 'close', force=30.0)
            time.sleep(0.5)

            # Step 4: Open giving gripper
            print(f"  Opening {from_arm} gripper...")
            self.driver.gripper_command(from_arm, 'open')
            time.sleep(0.5)

            # Step 5: Retract giving arm
            print(f"  Retracting {from_arm} arm...")
            retract_pos = handover_position.copy()
            retract_pos[2] += 0.1
            self.driver.move_to_pose(from_arm, retract_pos + orientation, speed)

            return {
                "success": True,
                "message": f"Successfully handed over object from {from_arm} to {to_arm}",
                "handover_position": handover_position
            }

        except Exception as e:
            return {"success": False, "message": f"Handover failed: {str(e)}"}

    def synchronized_move(
        self,
        left_position: List[float],
        right_position: List[float],
        left_orientation: Optional[List[float]] = None,
        right_orientation: Optional[List[float]] = None,
        speed: float = 0.3
    ) -> Dict:
        """Move both arms simultaneously to specified positions.

        Args:
            left_position: Target position for left arm [x, y, z]
            right_position: Target position for right arm [x, y, z]
            left_orientation: Optional orientation for left arm
            right_orientation: Optional orientation for right arm
            speed: Motion speed

        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        try:
            print(f"[Primitive] SynchronizedMove: left={left_position}, right={right_position}")

            if len(left_position) != 3 or len(right_position) != 3:
                return {"success": False, "message": "Positions must be [x, y, z]"}

            # Check collision
            if not self._check_arm_collision(left_position, right_position):
                return {"success": False, "message": "Arms would collide at target positions"}

            # Default orientations
            if left_orientation is None:
                left_orientation = [0.0, 0.0, 0.0]
            if right_orientation is None:
                right_orientation = [0.0, 0.0, 0.0]

            # Safety checks
            left_safe, msg = self.safety.check_workspace('left', left_position + left_orientation)
            if not left_safe:
                return {"success": False, "message": f"Left position unsafe: {msg}"}

            right_safe, msg = self.safety.check_workspace('right', right_position + right_orientation)
            if not right_safe:
                return {"success": False, "message": f"Right position unsafe: {msg}"}

            # Execute synchronized motion
            print("  Moving both arms simultaneously...")
            success_left = self.driver.move_to_pose('left', left_position + left_orientation, speed)
            success_right = self.driver.move_to_pose('right', right_position + right_orientation, speed)

            if not (success_left and success_right):
                return {"success": False, "message": "Failed to reach target positions"}

            return {
                "success": True,
                "message": "Successfully moved both arms",
                "left_position": left_position,
                "right_position": right_position
            }

        except Exception as e:
            return {"success": False, "message": f"SynchronizedMove failed: {str(e)}"}

    def _check_arm_collision(self, left_pos: List[float], right_pos: List[float], min_distance: float = 0.15) -> bool:
        """Check if two arm positions would result in collision.

        Args:
            left_pos: Left arm position [x, y, z]
            right_pos: Right arm position [x, y, z]
            min_distance: Minimum safe distance between arms (meters)

        Returns:
            True if safe, False if collision detected
        """
        import math

        # Calculate Euclidean distance
        distance = math.sqrt(
            (left_pos[0] - right_pos[0]) ** 2 +
            (left_pos[1] - right_pos[1]) ** 2 +
            (left_pos[2] - right_pos[2]) ** 2
        )

        return distance >= min_distance


