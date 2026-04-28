"""High-level action primitives for Baxter robot."""

from typing import Dict, List, Optional
import time
import threading
import asyncio
import numpy as np

from .drivers.base import ArmDriver
from .safety import SafetyValidator
from .vlm_client import VLMClient
from .multi_view_vlm import MultiViewVLMCoordinator


class BaxterPrimitives:
    """High-level action primitives for intuitive robot control.

    These primitives abstract low-level motion control into semantic
    actions that can be easily invoked by LLM agents.
    """

    def __init__(
        self,
        driver: ArmDriver,
        safety: SafetyValidator,
        vlm_client: Optional[VLMClient] = None,
        grasp_verifier: Optional['GraspVerifier'] = None,
        collision_detector: Optional['CollisionDetector'] = None
    ):
        """Initialize primitives.

        Args:
            driver: Robot driver instance
            safety: Safety validator instance
            vlm_client: Optional VLM client for vision features
            grasp_verifier: Optional grasp verifier for post-pick validation
            collision_detector: Optional collision detector for motion safety
        """
        self.driver = driver
        self.safety = safety
        self.vlm_client = vlm_client
        self.grasp_verifier = grasp_verifier
        self.collision_detector = collision_detector

        # Initialize multi-view VLM coordinator if VLM is available
        self.multi_view_vlm = None
        if vlm_client and driver.has_depth_camera():
            try:
                self.multi_view_vlm = MultiViewVLMCoordinator(driver, vlm_client, safety)
                print("[Primitives] Multi-view VLM coordinator initialized")
            except Exception as e:
                print(f"[Primitives] Warning: Could not initialize multi-view VLM: {e}")

        # Predefined home positions for each arm
        # Updated to current ideal positions (2026-04-21)
        # Read from actual robot pose and mirrored for symmetry
        self.home_positions = {
            'right': {
                'right_s0': -0.456743,
                'right_s1': -1.424685,
                'right_e0': -0.282252,
                'right_e1': 2.226190,
                'right_w0': -0.052922,
                'right_w1': 1.343000,
                'right_w2': -0.008820,
            },
            'left': {
                'left_s0': 0.456743,   # Mirror of right_s0
                'left_s1': -1.424685,  # Same as right_s1
                'left_e0': 0.282252,   # Mirror of right_e0
                'left_e1': 2.226190,   # Same as right_e1
                'left_w0': 0.052922,   # Mirror of right_w0
                'left_w1': 1.343000,   # Same as right_w1
                'left_w2': 0.008820,   # Mirror of right_w2
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
            # Roll=pi means gripper pointing down
            orientation = [np.pi, 0.0, 0.0]

            # Step 0: Check reachability BEFORE attempting motion
            pre_grasp_pose = position.copy()
            pre_grasp_pose[2] += approach_height

            print(f"  Pre-grasp pose: {pre_grasp_pose}")
            print(f"  Orientation (RPY): {orientation}")

            print(f"  Checking reachability for {arm} arm...")
            is_reachable = self.driver.check_pose_reachable(
                arm,
                pre_grasp_pose + orientation
            )

            if not is_reachable:
                print(f"  ✗ Target unreachable by {arm} arm")

                # Suggest alternative arm
                other_arm = 'right' if arm == 'left' else 'left'
                other_reachable = self.driver.check_pose_reachable(
                    other_arm,
                    pre_grasp_pose + orientation,
                    silent=True
                )

                if other_reachable:
                    return {
                        "success": False,
                        "message": f"Target unreachable by {arm} arm. Try using {other_arm} arm instead.",
                        "position": position,
                        "suggested_arm": other_arm
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Target position {position} is unreachable by both arms",
                        "position": position
                    }

            print(f"  ✓ Target is reachable by {arm} arm")

            # Step 1: Move to pre-grasp pose
            is_safe, msg = self.safety.check_workspace(arm, pre_grasp_pose + orientation)
            if not is_safe:
                print(f"  ERROR: Pre-grasp pose failed safety check: {msg}")
                return {"success": False, "message": f"Pre-grasp pose unsafe: {msg}"}

            print(f"  Moving to pre-grasp pose: {pre_grasp_pose}")
            success = self.driver.move_to_pose(arm, pre_grasp_pose + orientation, speed)
            if not success:
                print(f"  ERROR: Failed to reach pre-grasp pose")
                print(f"  This could be due to:")
                print(f"    - IK solver cannot find solution")
                print(f"    - Position out of reach")
                print(f"    - Joint limits exceeded")
                return {"success": False, "message": "Failed to reach pre-grasp pose (IK failed or unreachable)"}

            # Step 2: Open gripper
            print("  Opening gripper")
            self.driver.gripper_command(arm, "open")
            time.sleep(0.5)

            # Step 3: Descend to target
            # Override Z coordinate to fixed depth for reliable grasping
            grasp_position = position.copy()
            grasp_position[2] = -0.16  # Fixed Z depth to ensure gripper reaches table level

            target_pose = grasp_position + orientation
            is_safe, msg = self.safety.check_workspace(arm, target_pose)
            if not is_safe:
                return {"success": False, "message": f"Target pose unsafe: {msg}"}

            print(f"  Descending to target: {grasp_position} (Z fixed at -0.16)")
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
        1. Lift to safe height (avoid obstacles during horizontal movement)
        2. Move horizontally to above target position
        3. Descend to target position
        4. Open gripper
        5. Retract upward

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

            # Use same orientation as pick (gripper pointing down)
            orientation = [np.pi, 0.0, 0.0]

            # Step 1: Lift to safe height first (avoid obstacles during horizontal movement)
            # Get current position
            current_pose = self.driver.get_endpoint_pose(arm)
            if current_pose is None:
                return {"success": False, "message": "Failed to get current pose"}

            current_position = current_pose[:3]

            # Calculate safe lift height (higher of: current height + 0.05m, or target + approach_height)
            safe_height = max(current_position[2] + 0.05, position[2] + approach_height)

            lift_pose = current_position.copy()
            lift_pose[2] = safe_height

            is_safe, msg = self.safety.check_workspace(arm, lift_pose + orientation)
            if not is_safe:
                return {"success": False, "message": f"Lift pose unsafe: {msg}"}

            print(f"  Lifting to safe height: Z={safe_height:.3f}m")
            success = self.driver.move_to_pose(arm, lift_pose + orientation, speed)
            if not success:
                return {"success": False, "message": "Failed to lift to safe height"}

            # Step 2: Move horizontally to above target position
            pre_place_pose = position.copy()
            pre_place_pose[2] = safe_height

            is_safe, msg = self.safety.check_workspace(arm, pre_place_pose + orientation)
            if not is_safe:
                return {"success": False, "message": f"Pre-place pose unsafe: {msg}"}

            print(f"  Moving to above target: {pre_place_pose}")
            success = self.driver.move_to_pose(arm, pre_place_pose + orientation, speed)
            if not success:
                return {"success": False, "message": "Failed to reach pre-place pose"}

            # Step 3: Descend to target
            target_pose = position + orientation
            is_safe, msg = self.safety.check_workspace(arm, target_pose)
            if not is_safe:
                return {"success": False, "message": f"Target pose unsafe: {msg}"}

            print(f"  Descending to target: {position}")
            success = self.driver.move_to_pose(arm, target_pose, speed * 0.5)
            if not success:
                return {"success": False, "message": "Failed to reach target"}

            # Step 4: Open gripper
            print("  Opening gripper")
            self.driver.gripper_command(arm, "open")
            time.sleep(0.8)

            # Step 5: Retract upward
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

    async def place_by_name(
        self,
        arm: str,
        target_object_name: str,
        relative_position: str = "next_to",
        approach_height: float = 0.1,
        speed: float = 0.3
    ) -> Dict:
        """Place held object relative to another object using vision.

        Args:
            arm: 'left' or 'right'
            target_object_name: Name of reference object (e.g., "yellow block")
            relative_position: Where to place relative to target:
                - "next_to": 15cm to the side
                - "on_top": On top of the object
                - "behind": 15cm behind
                - "in_front": 15cm in front
            approach_height: Height offset for pre-place pose
            speed: Motion speed ratio (0-1)

        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        try:
            print(f"[Primitive] PlaceByName: arm={arm}, target={target_object_name}, position={relative_position}")

            # Step 1: Locate target object using multi-view
            if self.multi_view_vlm:
                print(f"  Locating target object: {target_object_name}...")
                target_result = await self.locate_object_multiview(
                    target_object_name,
                    arm=arm,
                    use_wrist_refinement=False
                )

                if not target_result.get('success') or not target_result.get('found'):
                    return {
                        "success": False,
                        "message": f"Could not locate target object: {target_object_name}"
                    }

                target_position = target_result['position']
                print(f"  Target object at: {target_position}")
            else:
                return {
                    "success": False,
                    "message": "Multi-view VLM not available (required for place_by_name)"
                }

            # Step 2: Calculate place position relative to target
            place_position = target_position.copy()

            if relative_position == "next_to":
                # 15cm to the right side
                place_position[1] += 0.15
                # Use target object height with small offset (place at same level)
                place_position[2] -= 0.05  # 5cm below target object top
            elif relative_position == "on_top":
                # On top (add small offset above object)
                place_position[2] += 0.03  # 5cm below detected position (on top of object)
            elif relative_position == "behind":
                # 15cm behind (negative X)
                place_position[0] -= 0.15
                # Use target object height with small offset
                place_position[2] -= 0.05
            elif relative_position == "in_front":
                # 15cm in front (positive X)
                place_position[0] += 0.15
                # Use target object height with small offset
                place_position[2] -= 0.05
            else:
                return {
                    "success": False,
                    "message": f"Unknown relative position: {relative_position}"
                }

            print(f"  Calculated place position: {place_position}")

            # Step 3: Execute place
            result = self.place(arm, place_position, approach_height, speed)

            # Add vision info to result
            result['target_object'] = target_object_name
            result['relative_position'] = relative_position
            result['target_location'] = target_position

            return result

        except Exception as e:
            return {"success": False, "message": f"PlaceByName failed: {str(e)}"}

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
        """Return arm(s) to predefined home position.

        Args:
            arm: 'left', 'right', or 'both'
            speed: Motion speed ratio (0-1)

        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        try:
            print(f"[Primitive] Home: arm={arm}")

            # Handle 'both' arms
            if arm == 'both':
                results = []
                for single_arm in ['left', 'right']:
                    result = self.home(single_arm, speed)
                    results.append(result)

                # Check if both succeeded
                all_success = all(r['success'] for r in results)
                if all_success:
                    return {
                        "success": True,
                        "message": "Both arms returned to home position",
                        "arm": "both"
                    }
                else:
                    failed_arms = [r.get('arm', 'unknown') for r in results if not r['success']]
                    return {
                        "success": False,
                        "message": f"Failed to home arms: {', '.join(failed_arms)}",
                        "arm": "both"
                    }

            # Single arm
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

    async def locate_object_multiview(
        self,
        object_name: str,
        arm: str = "right",
        use_wrist_refinement: bool = True
    ) -> Dict:
        """Locate object using multi-view VLM approach.

        Complete pipeline:
        1. Phase 1: D455 + head camera for initial detection
           - Retract arm to avoid occlusion
           - Capture and process images from both cameras
           - Cross-validate results
        2. Phase 2: Wrist camera refinement (optional)
           - Move wrist above estimated location
           - Capture close-up view
           - Fuse all views for final position

        Args:
            object_name: Name of object to locate
            arm: Which arm to use for wrist camera ("left" or "right")
            use_wrist_refinement: Whether to use wrist camera for refinement

        Returns:
            Dict with 'success', 'found', 'position', 'confidence', etc.
        """
        try:
            if not self.multi_view_vlm:
                return {
                    "success": False,
                    "message": "Multi-view VLM not available (requires VLM client and depth camera)"
                }

            print(f"[Primitive] LocateObjectMultiview: object={object_name}, arm={arm}")

            # Use multi-view coordinator
            result = await self.multi_view_vlm.locate_object_multiview(
                object_name,
                arm=arm,
                use_wrist_refinement=use_wrist_refinement
            )

            # Check if object was found
            # Smart detection: if we have valid position and confidence, consider it found
            found = result.get('found', False)
            confidence = result.get('confidence', 0)
            position = result.get('position', [0, 0, 0])

            # Override found=false if we have valid detection data
            if not found and confidence > 50 and any(p != 0 for p in position):
                print(f"[Primitive] ⚠ Overriding found=false: confidence={confidence}%, position={position}")
                found = True

            if result and found:
                return {
                    "success": True,
                    "found": True,
                    "position": result['position'],
                    "confidence": result['confidence'],
                    "description": result.get('description', ''),
                    "multi_view_validated": result.get('multi_view_validated', False),
                    "wrist_validated": result.get('wrist_validated', False),
                    "message": f"Object '{object_name}' located using multi-view approach"
                }
            else:
                return {
                    "success": True,
                    "found": False,
                    "message": f"Object '{object_name}' not found"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Multi-view localization failed: {str(e)}"
            }

    async def pick_by_name(
        self,
        arm: str,
        object_name: str,
        use_d455: bool = True,
        approach_height: float = 0.1,
        speed: float = 0.3
    ) -> Dict:
        """Pick up an object by name using vision.

        Args:
            arm: 'left', 'right', or 'auto' (auto-select based on Y-coordinate)
            object_name: Name of object to pick (e.g., "red cup", "blue box")
            use_d455: Use D455 depth camera (True) or wrist camera (False)
            approach_height: Height offset for pre-grasp pose
            speed: Motion speed ratio (0-1)

        Returns:
            Dict with 'success' (bool) and 'message' (str)
        """
        try:
            if not self.vlm_client:
                return {"success": False, "message": "VLM client not configured"}

            print(f"[Primitive] PickByName: arm={arm}, object={object_name}, use_d455={use_d455}")

            # Use multi-view localization if available (recommended)
            if use_d455 and self.multi_view_vlm:
                print(f"  Using multi-view localization (complete pipeline)...")

                # Use complete multi-view pipeline with:
                # - Arm retraction to avoid occlusion
                # - Coordinate transformation
                # - Calibration offset
                # Note: Use 'right' for retraction if arm is 'auto'
                retract_arm = 'right' if arm == 'auto' else arm

                location_result = await self.locate_object_multiview(
                    object_name,
                    arm=retract_arm,
                    use_wrist_refinement=False  # Only Phase 1 for speed
                )

                if not location_result.get('success') or not location_result.get('found'):
                    return {
                        "success": False,
                        "message": f"Could not locate {object_name}",
                        "vlm_response": location_result
                    }

                position = location_result['position']
                confidence = location_result['confidence']

                print(f"  Found {object_name} at position {position} (confidence: {confidence}%)")

                # Auto-select arm based on Y-coordinate if requested
                if arm == 'auto':
                    selected_arm = self.driver.select_arm_by_y_coordinate(position, y_threshold=0.0)
                    print(f"  Auto-selected {selected_arm} arm (Y={position[1]:.3f}m, threshold=0.0m)")
                    arm = selected_arm

            else:
                # Fallback to simple VLM localization (less accurate)
                print(f"  Using simple VLM localization (fallback)...")

                workspace_bounds = {
                    'x': self.safety.workspace_limits['x'],
                    'y': self.safety.workspace_limits['y'],
                    'z': self.safety.workspace_limits['z'],
                }

                # Capture image and locate based on camera choice
                if use_d455 and self.driver.has_depth_camera():
                    print(f"  Using D455 depth camera...")
                    rgb, depth = self.driver.capture_rgbd()
                    if rgb is not None and depth is not None:
                        # Convert RGB to JPEG
                        import cv2
                        success, jpeg_buffer = cv2.imencode('.jpg', rgb)
                        if success:
                            image_bytes = jpeg_buffer.tobytes()

                            # Use depth-enhanced localization (VLM + depth)
                            depth_camera = self.driver.get_depth_camera_driver()
                            location = await self.vlm_client.locate_object_with_depth(
                                image_bytes,
                                depth,
                                object_name,
                                depth_camera,
                                workspace_bounds
                            )
                        else:
                            return {"success": False, "message": "Failed to encode D455 image"}
                    else:
                        return {"success": False, "message": "Failed to capture from D455"}
                else:
                    # Fallback to wrist camera (VLM-only, less accurate)
                    camera = f"{arm}_hand"
                    print(f"  Using wrist camera: {camera}...")
                    image_bytes = self.driver.capture_image(camera)
                    if not image_bytes:
                        return {"success": False, "message": "Failed to capture image"}

                    # VLM-only localization (less accurate)
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
                confidence = location['confidence']
                print(f"  Found {object_name} at position {position} (confidence: {confidence}%)")

                location_result = location

            # Execute pick
            result = self.pick(arm, position, approach_height, speed)

            # Add vision info to result
            result['vlm_response'] = location_result
            result['object_name'] = object_name
            result['confidence'] = confidence

            # EXPERIMENTAL: Post-grasp verification with retry
            if self.grasp_verifier and result.get('success'):
                print(f"[Primitive] Running post-grasp verification...")

                try:
                    # Verify grasp and retry if needed
                    verification_result = await self.grasp_verifier.verify_and_retry_if_needed(
                        arm=arm,
                        object_name=object_name,
                        pick_function=lambda: self.pick(arm, position, approach_height, speed),
                        pick_params={}
                    )

                    # Update result with verification info
                    result['grasp_verified'] = verification_result['success']
                    result['verification_attempts'] = verification_result['attempts']
                    result['verification_details'] = verification_result.get('verification_result')

                    if not verification_result['success']:
                        # Verification failed after retries
                        result['success'] = False
                        result['message'] = (
                            f"Pick executed but grasp verification failed after "
                            f"{verification_result['attempts']} attempts. "
                            f"Reason: {verification_result.get('verification_result', {}).get('reasoning', 'Unknown')}"
                        )
                        print(f"[Primitive] ✗ Grasp verification failed")
                    else:
                        print(f"[Primitive] ✓ Grasp verified successfully")

                except Exception as e:
                    # Verification error - don't fail the pick, just log
                    print(f"[Primitive] Warning: Grasp verification error: {e}")
                    result['grasp_verified'] = None
                    result['verification_error'] = str(e)

            return result

        except Exception as e:
            return {"success": False, "message": f"PickByName failed: {str(e)}"}

    async def locate_object(
        self,
        object_name: str,
        use_d455: bool = True
    ) -> Dict:
        """Locate an object using vision without moving the robot.

        Args:
            object_name: Name of object to locate
            use_d455: Use D455 depth camera (True) or wrist camera (False)

        Returns:
            Dict with object location information
        """
        try:
            if not self.vlm_client:
                return {"success": False, "message": "VLM client not configured"}

            print(f"[Primitive] LocateObject: object={object_name}, use_d455={use_d455}")

            workspace_bounds = {
                'x': self.safety.workspace_limits['x'],
                'y': self.safety.workspace_limits['y'],
                'z': self.safety.workspace_limits['z'],
            }

            # Capture image and locate based on camera choice
            if use_d455 and self.driver.has_depth_camera():
                print(f"  Using D455 depth camera with depth enhancement...")
                rgb, depth = self.driver.capture_rgbd()
                if rgb is not None and depth is not None:
                    import cv2
                    success, jpeg_buffer = cv2.imencode('.jpg', rgb)
                    if success:
                        image_bytes = jpeg_buffer.tobytes()

                        # Use depth-enhanced localization (VLM + depth)
                        depth_camera = self.driver.get_depth_camera_driver()
                        location = await self.vlm_client.locate_object_with_depth(
                            image_bytes,
                            depth,
                            object_name,
                            depth_camera,
                            workspace_bounds
                        )
                    else:
                        return {"success": False, "message": "Failed to encode D455 image"}
                else:
                    return {"success": False, "message": "Failed to capture from D455"}
            else:
                # Fallback to right wrist camera (VLM-only, less accurate)
                print(f"  Using right wrist camera (VLM-only estimation)...")
                image_bytes = self.driver.capture_image("right_hand")
                if not image_bytes:
                    return {"success": False, "message": "Failed to capture image"}

                # VLM-only localization (less accurate)
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
                "bounding_box": location['bounding_box'],
                "depth_enhanced": location.get('depth_enhanced', False)
            }

        except Exception as e:
            return {"success": False, "message": f"LocateObject failed: {str(e)}"}

    async def describe_scene(self, use_d455: bool = True, language: str = "zh") -> Dict:
        """Get a description of the current scene.

        Args:
            use_d455: Use D455 depth camera (True) or wrist camera (False)
            language: Response language ('zh' for Chinese, 'en' for English)

        Returns:
            Dict with scene description
        """
        try:
            if not self.vlm_client:
                return {"success": False, "message": "VLM client not configured"}

            print(f"[Primitive] DescribeScene: use_d455={use_d455}, language={language}")

            # Capture image based on camera choice
            if use_d455 and self.driver.has_depth_camera():
                print(f"  Using D455 depth camera...")
                rgb, depth = self.driver.capture_rgbd()
                if rgb is not None:
                    import cv2
                    success, jpeg_buffer = cv2.imencode('.jpg', rgb)
                    if success:
                        image_bytes = jpeg_buffer.tobytes()
                    else:
                        return {"success": False, "message": "Failed to encode D455 image"}
                else:
                    return {"success": False, "message": "Failed to capture from D455"}
            else:
                # Fallback to right wrist camera
                print(f"  Using right wrist camera...")
                image_bytes = self.driver.capture_image("right_hand")
                if not image_bytes:
                    return {"success": False, "message": "Failed to capture image"}

            # Get scene description in specified language
            description = await self.vlm_client.describe_scene(image_bytes, language=language)

            return {
                "success": True,
                "message": "Scene described successfully",
                "description": description
            }

        except Exception as e:
            return {"success": False, "message": f"DescribeScene failed: {str(e)}"}

    async def identify_objects(self, use_d455: bool = True) -> Dict:
        """Identify all objects in the scene.

        Args:
            use_d455: Use D455 depth camera (True) or wrist camera (False)

        Returns:
            Dict with list of identified objects
        """
        try:
            if not self.vlm_client:
                return {"success": False, "message": "VLM client not configured"}

            print(f"[Primitive] IdentifyObjects: use_d455={use_d455}")

            # Capture image based on camera choice
            if use_d455 and self.driver.has_depth_camera():
                print(f"  Using D455 depth camera...")
                rgb, depth = self.driver.capture_rgbd()
                if rgb is not None:
                    import cv2
                    success, jpeg_buffer = cv2.imencode('.jpg', rgb)
                    if success:
                        image_bytes = jpeg_buffer.tobytes()
                    else:
                        return {"success": False, "message": "Failed to encode D455 image"}
                else:
                    return {"success": False, "message": "Failed to capture from D455"}
            else:
                # Fallback to right wrist camera
                print(f"  Using right wrist camera...")
                image_bytes = self.driver.capture_image("right_hand")
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

            # Move simultaneously using threading for true parallelism
            left_result = [False]
            right_result = [False]

            def move_left():
                left_result[0] = self.driver.move_to_pose('left', left_pre + orientation, speed)

            def move_right():
                right_result[0] = self.driver.move_to_pose('right', right_pre + orientation, speed)

            left_thread = threading.Thread(target=move_left)
            right_thread = threading.Thread(target=move_right)

            left_thread.start()
            right_thread.start()

            left_thread.join()
            right_thread.join()

            if not (left_result[0] and right_result[0]):
                return {"success": False, "message": "Failed to reach pre-grasp positions"}

            # Step 2: Open both grippers
            print("  Opening both grippers...")
            self.driver.gripper_command('left', 'open')
            self.driver.gripper_command('right', 'open')
            time.sleep(0.5)

            # Step 3: Descend both arms simultaneously
            print("  Descending to grasp positions...")

            left_result = [False]
            right_result = [False]

            def move_left():
                left_result[0] = self.driver.move_to_pose('left', left_pos + orientation, speed * 0.5)

            def move_right():
                right_result[0] = self.driver.move_to_pose('right', right_pos + orientation, speed * 0.5)

            left_thread = threading.Thread(target=move_left)
            right_thread = threading.Thread(target=move_right)

            left_thread.start()
            right_thread.start()

            left_thread.join()
            right_thread.join()

            if not (left_result[0] and right_result[0]):
                return {"success": False, "message": "Failed to reach grasp positions"}

            # Step 4: Close both grippers
            print("  Closing both grippers...")
            self.driver.gripper_command('left', 'close', force=30.0)
            self.driver.gripper_command('right', 'close', force=30.0)
            time.sleep(0.8)

            # Step 5: Lift both arms simultaneously
            print("  Lifting object...")

            left_result = [False]
            right_result = [False]

            def move_left():
                left_result[0] = self.driver.move_to_pose('left', left_pre + orientation, speed * 0.5)

            def move_right():
                right_result[0] = self.driver.move_to_pose('right', right_pre + orientation, speed * 0.5)

            left_thread = threading.Thread(target=move_left)
            right_thread = threading.Thread(target=move_right)

            left_thread.start()
            right_thread.start()

            left_thread.join()
            right_thread.join()

            if not (left_result[0] and right_result[0]):
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

    async def parallel_pick_two_objects(
        self,
        left_object_name: str,
        right_object_name: str,
        approach_height: float = 0.1,
        speed: float = 0.3
    ) -> Dict:
        """Pick two different objects simultaneously with both arms.

        This is different from bimanual_pick (which picks ONE large object with both arms).
        This picks TWO separate objects at the same time.

        Strategy:
        1. Locate both objects first (sequential, uses camera)
        2. Move both arms to pre-grasp positions simultaneously
        3. Descend both arms simultaneously
        4. Close both grippers simultaneously
        5. Lift both arms simultaneously

        Args:
            left_object_name: Object for left arm to pick
            right_object_name: Object for right arm to pick
            approach_height: Height offset for pre-grasp
            speed: Motion speed

        Returns:
            Dict with success status and positions
        """
        try:
            print(f"[Primitive] ParallelPickTwo: left={left_object_name}, right={right_object_name}")

            if not self.multi_view_vlm:
                return {"success": False, "message": "Multi-view VLM not available"}

            # Phase 1: Locate both objects (sequential to avoid camera conflicts)
            print(f"  [Phase 1] Locating objects...")

            print(f"    Locating {left_object_name}...")
            left_result = await self.locate_object_multiview(
                left_object_name,
                arm='left',
                use_wrist_refinement=False
            )

            if not left_result.get('success') or not left_result.get('found'):
                return {"success": False, "message": f"Could not locate {left_object_name}"}

            left_position = left_result['position']
            print(f"    ✓ Found {left_object_name} at {left_position}")

            print(f"    Locating {right_object_name}...")
            right_result = await self.locate_object_multiview(
                right_object_name,
                arm='right',
                use_wrist_refinement=False
            )

            if not right_result.get('success') or not right_result.get('found'):
                return {"success": False, "message": f"Could not locate {right_object_name}"}

            right_position = right_result['position']
            print(f"    ✓ Found {right_object_name} at {right_position}")

            # Phase 2: Execute parallel pick motions
            print(f"  [Phase 2] Executing parallel pick motions...")

            orientation = [3.14159, 0.0, 0.0]  # Downward facing

            # Calculate poses
            left_pre = [left_position[0], left_position[1], left_position[2] + approach_height]
            left_grasp = [left_position[0], left_position[1], -0.16]  # Fixed Z

            right_pre = [right_position[0], right_position[1], right_position[2] + approach_height]
            right_grasp = [right_position[0], right_position[1], -0.16]  # Fixed Z

            # Step 1: Move to pre-grasp (parallel)
            print("    Moving to pre-grasp positions (parallel)...")
            left_result = [False]
            right_result = [False]

            def move_left_pre():
                left_result[0] = self.driver.move_to_pose('left', left_pre + orientation, speed)

            def move_right_pre():
                right_result[0] = self.driver.move_to_pose('right', right_pre + orientation, speed)

            left_thread = threading.Thread(target=move_left_pre)
            right_thread = threading.Thread(target=move_right_pre)
            left_thread.start()
            right_thread.start()
            left_thread.join()
            right_thread.join()

            if not (left_result[0] and right_result[0]):
                return {"success": False, "message": "Failed to reach pre-grasp positions"}

            # Step 2: Open grippers
            print("    Opening grippers...")
            self.driver.gripper_command('left', 'open')
            self.driver.gripper_command('right', 'open')
            time.sleep(0.5)

            # Step 3: Descend (parallel)
            print("    Descending to grasp (parallel)...")
            left_result = [False]
            right_result = [False]

            def move_left_grasp():
                left_result[0] = self.driver.move_to_pose('left', left_grasp + orientation, speed * 0.5)

            def move_right_grasp():
                right_result[0] = self.driver.move_to_pose('right', right_grasp + orientation, speed * 0.5)

            left_thread = threading.Thread(target=move_left_grasp)
            right_thread = threading.Thread(target=move_right_grasp)
            left_thread.start()
            right_thread.start()
            left_thread.join()
            right_thread.join()

            if not (left_result[0] and right_result[0]):
                return {"success": False, "message": "Failed to reach grasp positions"}

            # Step 4: Close grippers
            print("    Closing grippers...")
            self.driver.gripper_command('left', 'close', force=30.0)
            self.driver.gripper_command('right', 'close', force=30.0)
            time.sleep(0.8)

            # Step 5: Lift (parallel)
            print("    Lifting objects (parallel)...")
            left_result = [False]
            right_result = [False]

            def move_left_lift():
                left_result[0] = self.driver.move_to_pose('left', left_pre + orientation, speed * 0.5)

            def move_right_lift():
                right_result[0] = self.driver.move_to_pose('right', right_pre + orientation, speed * 0.5)

            left_thread = threading.Thread(target=move_left_lift)
            right_thread = threading.Thread(target=move_right_lift)
            left_thread.start()
            right_thread.start()
            left_thread.join()
            right_thread.join()

            if not (left_result[0] and right_result[0]):
                return {"success": False, "message": "Failed to lift objects"}

            return {
                "success": True,
                "message": f"Successfully picked {left_object_name} and {right_object_name} in parallel",
                "left_object": left_object_name,
                "right_object": right_object_name,
                "left_position": left_position,
                "right_position": right_position
            }

        except Exception as e:
            return {"success": False, "message": f"ParallelPickTwo failed: {str(e)}"}

    async def parallel_place_two_objects(
        self,
        left_target_name: str,
        left_relative_position: str,
        right_target_name: str,
        right_relative_position: str,
        approach_height: float = 0.1,
        speed: float = 0.3
    ) -> Dict:
        """Place two held objects simultaneously to different targets.

        Strategy:
        1. Locate both target objects first (sequential, uses D455)
        2. Calculate place positions for both arms
        3. Move both arms to pre-place positions simultaneously
        4. Descend both arms simultaneously
        5. Open both grippers simultaneously
        6. Retract both arms simultaneously

        Args:
            left_target_name: Target object for left arm placement
            left_relative_position: Where to place left object
            right_target_name: Target object for right arm placement
            right_relative_position: Where to place right object
            approach_height: Height offset for pre-place
            speed: Motion speed

        Returns:
            Dict with success status
        """
        try:
            print(f"[Primitive] ParallelPlaceTwo:")
            print(f"  Left: place relative to {left_target_name} ({left_relative_position})")
            print(f"  Right: place relative to {right_target_name} ({right_relative_position})")

            if not self.multi_view_vlm:
                return {"success": False, "message": "Multi-view VLM not available"}

            # Phase 1: Locate both target objects (sequential to avoid D455 conflicts)
            print(f"  [Phase 1] Locating target objects...")

            print(f"    Locating {left_target_name}...")
            left_result = await self.locate_object_multiview(
                left_target_name,
                arm='left',
                use_wrist_refinement=False
            )

            if not left_result.get('success') or not left_result.get('found'):
                return {"success": False, "message": f"Could not locate {left_target_name}"}

            left_target_pos = left_result['position']
            print(f"    ✓ Found {left_target_name} at {left_target_pos}")

            print(f"    Locating {right_target_name}...")
            right_result = await self.locate_object_multiview(
                right_target_name,
                arm='right',
                use_wrist_refinement=False
            )

            if not right_result.get('success') or not right_result.get('found'):
                return {"success": False, "message": f"Could not locate {right_target_name}"}

            right_target_pos = right_result['position']
            print(f"    ✓ Found {right_target_name} at {right_target_pos}")

            # Phase 2: Calculate place positions
            print(f"  [Phase 2] Calculating place positions...")

            def calculate_relative_position(target_pos, relative_pos):
                if relative_pos == "on_top":
                    return [target_pos[0], target_pos[1], target_pos[2] + 0.05]
                elif relative_pos == "next_to":
                    return [target_pos[0], target_pos[1] + 0.15, target_pos[2]]
                elif relative_pos == "behind":
                    return [target_pos[0] - 0.15, target_pos[1], target_pos[2]]
                elif relative_pos == "in_front":
                    return [target_pos[0] + 0.15, target_pos[1], target_pos[2]]
                else:
                    return [target_pos[0], target_pos[1] + 0.15, target_pos[2]]

            left_place_pos = calculate_relative_position(left_target_pos, left_relative_position)
            right_place_pos = calculate_relative_position(right_target_pos, right_relative_position)

            orientation = [3.14159, 0.0, 0.0]

            left_pre = [left_place_pos[0], left_place_pos[1], left_place_pos[2] + approach_height]
            left_place = [left_place_pos[0], left_place_pos[1], -0.16]

            right_pre = [right_place_pos[0], right_place_pos[1], right_place_pos[2] + approach_height]
            right_place = [right_place_pos[0], right_place_pos[1], -0.16]

            # Phase 3: Execute parallel place motions
            print(f"  [Phase 3] Executing parallel place motions...")

            # Step 1: Lift to pre-place (parallel)
            print("    Lifting to pre-place positions (parallel)...")
            left_result = [False]
            right_result = [False]

            def move_left_pre():
                left_result[0] = self.driver.move_to_pose('left', left_pre + orientation, speed)

            def move_right_pre():
                right_result[0] = self.driver.move_to_pose('right', right_pre + orientation, speed)

            left_thread = threading.Thread(target=move_left_pre)
            right_thread = threading.Thread(target=move_right_pre)
            left_thread.start()
            right_thread.start()
            left_thread.join()
            right_thread.join()

            if not (left_result[0] and right_result[0]):
                return {"success": False, "message": "Failed to reach pre-place positions"}

            # Step 2: Descend (parallel)
            print("    Descending to place (parallel)...")
            left_result = [False]
            right_result = [False]

            def move_left_place():
                left_result[0] = self.driver.move_to_pose('left', left_place + orientation, speed * 0.5)

            def move_right_place():
                right_result[0] = self.driver.move_to_pose('right', right_place + orientation, speed * 0.5)

            left_thread = threading.Thread(target=move_left_place)
            right_thread = threading.Thread(target=move_right_place)
            left_thread.start()
            right_thread.start()
            left_thread.join()
            right_thread.join()

            if not (left_result[0] and right_result[0]):
                return {"success": False, "message": "Failed to reach place positions"}

            # Step 3: Open grippers
            print("    Opening grippers...")
            self.driver.gripper_command('left', 'open')
            self.driver.gripper_command('right', 'open')
            time.sleep(0.8)

            # Step 4: Retract (parallel)
            print("    Retracting (parallel)...")
            left_result = [False]
            right_result = [False]

            def move_left_retract():
                left_result[0] = self.driver.move_to_pose('left', left_pre + orientation, speed * 0.5)

            def move_right_retract():
                right_result[0] = self.driver.move_to_pose('right', right_pre + orientation, speed * 0.5)

            left_thread = threading.Thread(target=move_left_retract)
            right_thread = threading.Thread(target=move_right_retract)
            left_thread.start()
            right_thread.start()
            left_thread.join()
            right_thread.join()

            if not (left_result[0] and right_result[0]):
                return {"success": False, "message": "Failed to retract"}

            return {
                "success": True,
                "message": f"Successfully placed both objects in parallel",
                "left_target": left_target_name,
                "right_target": right_target_name,
                "left_position": left_place_pos,
                "right_position": right_place_pos
            }

        except Exception as e:
            return {"success": False, "message": f"ParallelPlaceTwo failed: {str(e)}"}

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

            # Execute synchronized motion using threading
            print("  Moving both arms simultaneously...")

            left_result = [False]
            right_result = [False]

            def move_left():
                left_result[0] = self.driver.move_to_pose('left', left_position + left_orientation, speed)

            def move_right():
                right_result[0] = self.driver.move_to_pose('right', right_position + right_orientation, speed)

            left_thread = threading.Thread(target=move_left)
            right_thread = threading.Thread(target=move_right)

            left_thread.start()
            right_thread.start()

            left_thread.join()
            right_thread.join()

            if not (left_result[0] and right_result[0]):
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


