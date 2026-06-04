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
                self.multi_view_vlm = MultiViewVLMCoordinator(
                    driver, vlm_client, safety, debug=True  # Enable debug to save annotated images
                )
                print("[Primitives] Multi-view VLM coordinator initialized (debug mode enabled)")
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
                place_position[2] -= 0.01  # 5cm below target object top
            elif relative_position == "on_top":
                # On top (add small offset above object)
                place_position[2] += 0.04  # 5cm below detected position (on top of object)
            elif relative_position == "behind":
                # 15cm behind (negative X)
                place_position[0] -= 0.15
                # Use target object height with small offset
                place_position[2] -= 0.01
            elif relative_position == "in_front":
                # 15cm in front (positive X)
                place_position[0] += 0.15
                # Use target object height with small offset
                place_position[2] -= 0.01
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
            result['position'] = position  # Add position for downstream tasks (e.g., sequential_handover)

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
                    return [target_pos[0], target_pos[1], target_pos[2] + 0]
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
            left_place = [left_place_pos[0], left_place_pos[1], left_place_pos[2]]

            right_pre = [right_place_pos[0], right_place_pos[1], right_place_pos[2] + approach_height]
            right_place = [right_place_pos[0], right_place_pos[1], right_place_pos[2]]

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

    async def sequential_relay_pick_place(
        self,
        object_name: str,
        final_target_name: Optional[str] = None,
        final_relative_position: str = "next_to",
        relay_offset_y: float = 0.0,
        final_offset_x: float = 0.20,
        approach_height: float = 0.1,
        speed: float = 0.3
    ) -> Dict:
        """Sequential relay: left arm picks from left, places at center; right arm picks from center, places at right.

        Scenario: Object A is on the left side of the table. Robot uses left arm to pick it and place
        at center (y=0), then retracts left arm to home. Then right arm picks from center and places
        at right side.

        Args:
            object_name: Name of the object to relay (e.g., "blue cube")
            final_target_name: Optional reference object for final placement (if None, use offset)
            final_relative_position: Relative position to final target ("next_to", "on_top", etc.)
            relay_offset_y: Y offset for relay position (default 0.0 = center)
            final_offset_x: X offset for final position from relay (default 0.20m to the right)
            approach_height: Height offset for approach movements
            speed: Motion speed

        Returns:
            Dict with success status and execution details

        Execution flow:
        1. Left arm picks object from left side
        2. Left arm places at center (relay position)
        3. Left arm retracts to home
        4. Right arm picks object from center
        5. Right arm places at right side (final position)
        6. Right arm retracts
        """
        try:
            print(f"\n{'='*70}")
            print(f"[Sequential Relay] Starting relay pick-place for '{object_name}'")
            print(f"{'='*70}")

            orientation = [np.pi, 0.0, 0.0]  # Downward gripper

            # ============================================================
            # PHASE 1: Left arm picks from left side
            # ============================================================
            print(f"\n[Phase 1] Left arm: Pick '{object_name}' from left side")

            # Locate object
            print(f"  Locating '{object_name}'...")
            left_result = await self.locate_object_multiview(
                object_name,
                arm="left",
                use_wrist_refinement=False
            )

            if not left_result or not left_result.get('found'):
                return {
                    "success": False,
                    "message": f"Failed to locate {object_name}",
                    "phase": "left_pick_locate"
                }

            left_pick_pos = left_result['position']
            print(f"  ✓ Located at: {left_pick_pos}")

            # Pick with left arm
            print(f"  Picking with left arm...")
            left_pre = [left_pick_pos[0], left_pick_pos[1], left_pick_pos[2] + approach_height]

            # Move to pre-pick
            if not self.driver.move_to_pose('left', left_pre + orientation, speed):
                return {"success": False, "message": "Left arm failed to reach pre-pick", "phase": "left_pick_approach"}

            # Descend
            if not self.driver.move_to_pose('left', left_pick_pos + orientation, speed * 0.5):
                return {"success": False, "message": "Left arm failed to descend", "phase": "left_pick_descend"}

            # Grasp
            self.driver.gripper_command('left', 'close', force=30.0)
            time.sleep(0.8)

            # Lift
            if not self.driver.move_to_pose('left', left_pre + orientation, speed * 0.5):
                return {"success": False, "message": "Left arm failed to lift", "phase": "left_pick_lift"}

            print(f"  ✓ Left arm picked object")

            # ============================================================
            # PHASE 2: Left arm places at center (relay position)
            # ============================================================
            print(f"\n[Phase 2] Left arm: Place at center (relay position)")

            # Calculate relay position: same X and Z as pick, but Y = relay_offset_y (default 0)
            relay_pos = [left_pick_pos[0], relay_offset_y, left_pick_pos[2]]
            relay_pre = [relay_pos[0], relay_pos[1], relay_pos[2] + approach_height]

            print(f"  Relay position: {relay_pos}")

            # Move to pre-place
            if not self.driver.move_to_pose('left', relay_pre + orientation, speed):
                return {"success": False, "message": "Left arm failed to reach relay pre-place", "phase": "left_place_approach"}

            # Descend
            if not self.driver.move_to_pose('left', relay_pos + orientation, speed * 0.5):
                return {"success": False, "message": "Left arm failed to descend to relay", "phase": "left_place_descend"}

            # Release
            self.driver.gripper_command('left', 'open')
            time.sleep(0.8)

            # Retract
            if not self.driver.move_to_pose('left', relay_pre + orientation, speed * 0.5):
                return {"success": False, "message": "Left arm failed to retract from relay", "phase": "left_place_retract"}

            print(f"  ✓ Left arm placed at relay position")

            # ============================================================
            # PHASE 3: Left arm returns to home
            # ============================================================
            print(f"\n[Phase 3] Left arm: Return to home")

            if not self.driver.move_to_home('left'):
                print(f"  ⚠ Warning: Left arm failed to return home (continuing anyway)")
            else:
                print(f"  ✓ Left arm at home")

            # ============================================================
            # PHASE 4: Right arm picks from center (relay position)
            # ============================================================
            print(f"\n[Phase 4] Right arm: Pick from center (relay position)")

            # Right arm picks from relay position
            print(f"  Moving to relay position: {relay_pos}")

            # Move to pre-pick
            if not self.driver.move_to_pose('right', relay_pre + orientation, speed):
                return {"success": False, "message": "Right arm failed to reach relay pre-pick", "phase": "right_pick_approach"}

            # Open gripper
            self.driver.gripper_command('right', 'open')
            time.sleep(0.5)

            # Descend
            if not self.driver.move_to_pose('right', relay_pos + orientation, speed * 0.5):
                return {"success": False, "message": "Right arm failed to descend to relay", "phase": "right_pick_descend"}

            # Grasp
            self.driver.gripper_command('right', 'close', force=30.0)
            time.sleep(0.8)

            # Lift
            if not self.driver.move_to_pose('right', relay_pre + orientation, speed * 0.5):
                return {"success": False, "message": "Right arm failed to lift from relay", "phase": "right_pick_lift"}

            print(f"  ✓ Right arm picked from relay")

            # ============================================================
            # PHASE 5: Right arm places at right side (final position)
            # ============================================================
            print(f"\n[Phase 5] Right arm: Place at right side (final position)")

            # Calculate final position
            if final_target_name:
                # Locate target and place relative to it
                print(f"  Locating final target '{final_target_name}'...")
                target_result = await self.locate_object_multiview(
                    final_target_name,
                    arm="right",
                    use_wrist_refinement=False
                )

                if not target_result or not target_result.get('found'):
                    print(f"  ⚠ Warning: Failed to locate target, using offset instead")
                    final_pos = [relay_pos[0] + final_offset_x, relay_pos[1], relay_pos[2]]
                else:
                    target_pos = target_result['position']
                    print(f"  ✓ Target at: {target_pos}")

                    # Calculate relative position
                    if final_relative_position == "next_to":
                        final_pos = [target_pos[0], target_pos[1] + 0.15, target_pos[2]]
                    elif final_relative_position == "on_top":
                        final_pos = [target_pos[0], target_pos[1], target_pos[2] + 0.05]
                    elif final_relative_position == "behind":
                        final_pos = [target_pos[0] - 0.15, target_pos[1], target_pos[2]]
                    elif final_relative_position == "in_front":
                        final_pos = [target_pos[0] + 0.15, target_pos[1], target_pos[2]]
                    else:
                        final_pos = [target_pos[0], target_pos[1] + 0.15, target_pos[2]]
            else:
                # Use offset from relay position
                final_pos = [relay_pos[0] + final_offset_x, relay_pos[1], relay_pos[2]]

            final_pre = [final_pos[0], final_pos[1], final_pos[2] + approach_height]

            print(f"  Final position: {final_pos}")

            # Move to pre-place
            if not self.driver.move_to_pose('right', final_pre + orientation, speed):
                return {"success": False, "message": "Right arm failed to reach final pre-place", "phase": "right_place_approach"}

            # Descend
            if not self.driver.move_to_pose('right', final_pos + orientation, speed * 0.5):
                return {"success": False, "message": "Right arm failed to descend to final", "phase": "right_place_descend"}

            # Release
            self.driver.gripper_command('right', 'open')
            time.sleep(0.8)

            # Retract
            if not self.driver.move_to_pose('right', final_pre + orientation, speed * 0.5):
                return {"success": False, "message": "Right arm failed to retract from final", "phase": "right_place_retract"}

            print(f"  ✓ Right arm placed at final position")

            # ============================================================
            # PHASE 6: Right arm returns to home
            # ============================================================
            print(f"\n[Phase 6] Right arm: Return to home")

            if not self.driver.move_to_home('right'):
                print(f"  ⚠ Warning: Right arm failed to return home")
            else:
                print(f"  ✓ Right arm at home")

            # Done
            print(f"\n{'='*70}")
            print(f"[Sequential Relay] ✓ Task complete")
            print(f"{'='*70}\n")

            return {
                "success": True,
                "message": f"Successfully relayed {object_name} from left to right",
                "object_name": object_name,
                "left_pick_position": left_pick_pos,
                "relay_position": relay_pos,
                "final_position": final_pos,
                "final_target": final_target_name
            }

        except Exception as e:
            return {"success": False, "message": f"SequentialRelay failed: {str(e)}"}

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



    # ============================================================
    # Bimanual Hold and Rotate: Geometry Helpers
    # ============================================================

    def rotate_point_around_center_xy(
        self,
        point: List[float],
        center: List[float],
        angle_degrees: float,
        direction: str
    ) -> List[float]:
        """Rotate a point around a center in XY plane.
        
        Args:
            point: Point to rotate [x, y, z]
            center: Center of rotation [x, y, z]
            angle_degrees: Rotation angle in degrees
            direction: 'clockwise' or 'counterclockwise'
            
        Returns:
            Rotated point [x, y, z] with Z unchanged
            
        Convention:
            - Looking down from +Z (top view)
            - counterclockwise = positive angle
            - clockwise = negative angle
        """
        # Determine signed angle
        if direction == "counterclockwise":
            signed_angle = angle_degrees
        elif direction == "clockwise":
            signed_angle = -angle_degrees
        else:
            raise ValueError(f"Invalid direction: {direction}. Must be 'clockwise' or 'counterclockwise'")
        
        # Convert to radians
        theta = np.radians(signed_angle)
        
        # Compute relative position
        dx = point[0] - center[0]
        dy = point[1] - center[1]
        
        # Apply 2D rotation matrix
        target_x = center[0] + np.cos(theta) * dx - np.sin(theta) * dy
        target_y = center[1] + np.sin(theta) * dx + np.cos(theta) * dy
        target_z = point[2]  # Keep Z unchanged
        
        return [target_x, target_y, target_z]

    def plan_arc_waypoints_xy(
        self,
        start_point: List[float],
        center: List[float],
        angle_degrees: float,
        direction: str,
        waypoint_angle_step_degrees: float = 10.0
    ) -> List[List[float]]:
        """Plan waypoints along a circular arc in XY plane.
        
        Args:
            start_point: Starting point [x, y, z]
            center: Center of rotation [x, y, z]
            angle_degrees: Total rotation angle in degrees
            direction: 'clockwise' or 'counterclockwise'
            waypoint_angle_step_degrees: Angle step between waypoints
            
        Returns:
            List of waypoints including start and end points
        """
        # Ensure at least 5 waypoints
        num_steps = max(5, int(np.ceil(angle_degrees / waypoint_angle_step_degrees)))
        angle_step = angle_degrees / num_steps
        
        waypoints = []
        
        # Generate waypoints
        for i in range(num_steps + 1):
            current_angle = i * angle_step
            waypoint = self.rotate_point_around_center_xy(
                start_point, center, current_angle, direction
            )
            waypoints.append(waypoint)
        
        print(f"[Geometry] Generated {len(waypoints)} waypoints for {angle_degrees}° rotation")
        print(f"[Geometry] Angle step: {angle_step:.1f}°")
        
        return waypoints

    def estimate_hinge_center_from_two_midpoints_and_observed_joint(
        self,
        midpoint_a: List[float],
        midpoint_b: List[float],
        observed_hinge: List[float],
        segment_length: float,
        tolerance: float = 0.02
    ) -> Dict:
        """Estimate hinge center from two segment midpoints and observed joint position.
        
        Theory:
            - Each ruler segment has length L = segment_length (e.g., 0.15m)
            - Distance from segment midpoint to hinge = r = L/2 (e.g., 0.075m)
            - Two adjacent segments share a common hinge point H
            - H must satisfy: distance(H, A) = r AND distance(H, B) = r
            - This gives two candidate points (circle-circle intersection)
            - Use VLM-observed hinge position to disambiguate
        
        Args:
            midpoint_a: Midpoint of first segment [x, y, z]
            midpoint_b: Midpoint of second segment [x, y, z]
            observed_hinge: VLM-observed hinge position [x, y, z]
            segment_length: Length of each segment in meters
            tolerance: Tolerance for geometric validation in meters
            
        Returns:
            Dict with:
                - selected_hinge: Chosen hinge position
                - candidate_hinges: Both candidate positions
                - observed_hinge: Input observed position
                - distance_to_observed: Distance from selected to observed
                - selection_reason: Explanation of choice
                - warnings: List of warnings
        """
        warnings = []
        
        # Extract XY coordinates (ignore Z for now)
        ax, ay = midpoint_a[0], midpoint_a[1]
        bx, by = midpoint_b[0], midpoint_b[1]
        
        # Radius from midpoint to hinge
        r = segment_length / 2.0
        
        # Distance between midpoints
        d = np.sqrt((bx - ax)**2 + (by - ay)**2)
        
        print(f"[Hinge] Midpoint A: [{ax:.3f}, {ay:.3f}]")
        print(f"[Hinge] Midpoint B: [{bx:.3f}, {by:.3f}]")
        print(f"[Hinge] Distance between midpoints: {d:.3f}m")
        print(f"[Hinge] Required radius: {r:.3f}m")
        print(f"[Hinge] Theoretical max distance: {2*r:.3f}m")
        
        # Check if circles can intersect
        if d > 2 * r + tolerance:
            error_msg = f"Midpoints too far apart: {d:.3f}m > {2*r + tolerance:.3f}m. Segments may not be adjacent."
            print(f"[Hinge] ERROR: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "midpoint_distance": d,
                "max_distance": 2 * r
            }
        
        if d < 0.01:  # Very small distance
            error_msg = f"Midpoints too close: {d:.3f}m. VLM localization may have failed."
            print(f"[Hinge] ERROR: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        
        # Handle case where d slightly exceeds 2r (visual noise)
        if d > 2 * r:
            warnings.append(f"Midpoint distance {d:.3f}m slightly exceeds 2r={2*r:.3f}m. Clamping for circle intersection.")
            d = 2 * r  # Clamp to make intersection possible
        
        # Compute circle-circle intersection
        # Midpoint of AB
        mx = (ax + bx) / 2.0
        my = (ay + by) / 2.0
        
        # Distance from midpoint of AB to intersection points
        if d < 2 * r:
            h = np.sqrt(r**2 - (d/2.0)**2)
        else:
            h = 0.0  # Circles just touch
        
        # Unit vector from A to B
        if d > 0.001:
            ux = (bx - ax) / d
            uy = (by - ay) / d
        else:
            # Degenerate case
            ux, uy = 1.0, 0.0
        
        # Perpendicular unit vector
        px = -uy
        py = ux
        
        # Two candidate hinge positions
        h1_x = mx + h * px
        h1_y = my + h * py
        
        h2_x = mx - h * px
        h2_y = my - h * py
        
        # Use average Z or observed Z
        hz = observed_hinge[2]
        
        candidate1 = [h1_x, h1_y, hz]
        candidate2 = [h2_x, h2_y, hz]
        
        print(f"[Hinge] Candidate 1: [{h1_x:.3f}, {h1_y:.3f}, {hz:.3f}]")
        print(f"[Hinge] Candidate 2: [{h2_x:.3f}, {h2_y:.3f}, {hz:.3f}]")
        
        # Compute distances to observed hinge (XY only)
        obs_x, obs_y = observed_hinge[0], observed_hinge[1]
        
        dist1 = np.sqrt((h1_x - obs_x)**2 + (h1_y - obs_y)**2)
        dist2 = np.sqrt((h2_x - obs_x)**2 + (h2_y - obs_y)**2)
        
        print(f"[Hinge] Distance candidate 1 to observed: {dist1:.3f}m")
        print(f"[Hinge] Distance candidate 2 to observed: {dist2:.3f}m")
        
        # Select closer candidate
        if dist1 <= dist2:
            selected_hinge = candidate1
            distance_to_observed = dist1
            selection_reason = f"Candidate 1 closer to VLM-observed hinge ({dist1:.3f}m vs {dist2:.3f}m)"
        else:
            selected_hinge = candidate2
            distance_to_observed = dist2
            selection_reason = f"Candidate 2 closer to VLM-observed hinge ({dist2:.3f}m vs {dist1:.3f}m)"
        
        print(f"[Hinge] Selected: {selected_hinge}")
        print(f"[Hinge] Reason: {selection_reason}")
        
        # Validation: check distances from selected hinge to midpoints
        dist_to_a = np.sqrt((selected_hinge[0] - ax)**2 + (selected_hinge[1] - ay)**2)
        dist_to_b = np.sqrt((selected_hinge[0] - bx)**2 + (selected_hinge[1] - by)**2)
        
        print(f"[Hinge] Validation: distance to midpoint A: {dist_to_a:.3f}m (expected {r:.3f}m)")
        print(f"[Hinge] Validation: distance to midpoint B: {dist_to_b:.3f}m (expected {r:.3f}m)")
        
        if abs(dist_to_a - r) > tolerance:
            warnings.append(f"Distance from hinge to midpoint A ({dist_to_a:.3f}m) deviates from expected {r:.3f}m")
        
        if abs(dist_to_b - r) > tolerance:
            warnings.append(f"Distance from hinge to midpoint B ({dist_to_b:.3f}m) deviates from expected {r:.3f}m")
        
        if distance_to_observed > 0.03:
            warnings.append(f"Selected hinge is {distance_to_observed:.3f}m away from VLM-observed position (>3cm)")
        
        return {
            "success": True,
            "selected_hinge": selected_hinge,
            "candidate_hinges": [candidate1, candidate2],
            "observed_hinge": observed_hinge,
            "distance_to_observed": distance_to_observed,
            "selection_reason": selection_reason,
            "warnings": warnings,
            "validation": {
                "distance_to_midpoint_a": dist_to_a,
                "distance_to_midpoint_b": dist_to_b,
                "expected_distance": r
            }
        }


    # ============================================================
    # Bimanual Hold and Rotate: VLM Localization Helper
    # ============================================================

    async def locate_named_point(
        self,
        description: str,
        use_d455: bool = True
    ) -> Dict:
        """Locate a named point using VLM + depth camera.

        This is a wrapper around existing VLM localization that can handle
        specific point descriptions like:
        - "blue segment midpoint"
        - "yellow segment grasp block center"
        - "connection point between blue and yellow segments"

        Args:
            description: Natural language description of the point to locate
            use_d455: Use D455 depth camera

        Returns:
            Dict with 'success', 'found', 'position', 'confidence'
        """
        if not self.multi_view_vlm:
            return {
                "success": False,
                "found": False,
                "message": "Multi-view VLM not available"
            }

        print(f"\n\033[96m[LocatePoint]\033[0m Locating: \033[93m{description}\033[0m")

        # Use multi-view localization with the description as object name
        result = await self.multi_view_vlm.locate_object_multiview(
            object_name=description,
            arm='right',
            use_wrist_refinement=False
        )

        # Check if result is valid
        if result is None:
            print(f"\033[91m[LocatePoint] ✗ Not found: No result returned\033[0m")
            return {
                "success": False,
                "found": False,
                "message": "No result returned from VLM"
            }

        # Check if object was found
        if result.get('found'):
            position = result.get('position')
            confidence = result.get('confidence', 0)
            print(f"\033[92m[LocatePoint] ✓ Found at {position}\033[0m")
            print(f"  Confidence: {confidence}%")

            return {
                "success": True,
                "found": True,
                "position": position,
                "confidence": confidence,
                "raw_result": result
            }
        else:
            msg = result.get('message', 'Object not found')
            print(f"\033[91m[LocatePoint] ✗ Not found: {msg}\033[0m")
            return {
                "success": False,
                "found": False,
                "message": msg
            }

    # ============================================================
    # Bimanual Hold and Rotate: Low-level Motion Primitives
    # ============================================================

    def follow_arc_waypoints(
        self,
        arm: str,
        waypoints: List[List[float]],
        orientation: Optional[List[float]] = None,
        speed: float = 0.10
    ) -> Dict:
        """Move arm along a series of waypoints (arc trajectory).
        
        Args:
            arm: 'left' or 'right'
            waypoints: List of [x, y, z] positions
            orientation: Optional [roll, pitch, yaw], defaults to downward
            speed: Motion speed ratio (kept low for safety)
            
        Returns:
            Dict with 'success', 'message', 'completed_waypoints'
        """
        if orientation is None:
            orientation = [3.14159, 0.0, 0.0]  # Downward facing
        
        print(f"[FollowArc] {arm} arm following {len(waypoints)} waypoints at speed {speed}")
        
        completed = 0
        for i, waypoint in enumerate(waypoints):
            print(f"[FollowArc] Waypoint {i+1}/{len(waypoints)}: {waypoint}")
            
            pose = waypoint + orientation
            success = self.driver.move_to_pose(arm, pose, speed)
            
            if not success:
                print(f"[FollowArc] ✗ Failed at waypoint {i+1}")
                return {
                    "success": False,
                    "message": f"Failed to reach waypoint {i+1}/{len(waypoints)}",
                    "completed_waypoints": completed,
                    "failed_waypoint_index": i
                }
            
            completed += 1
            time.sleep(0.1)  # Small pause between waypoints
        
        print(f"[FollowArc] ✓ Completed all {completed} waypoints")
        return {
            "success": True,
            "message": f"Successfully followed {completed} waypoints",
            "completed_waypoints": completed
        }


    # ============================================================
    # Bimanual Hold and Rotate: Main Method
    # ============================================================

    async def bimanual_hold_and_rotate(
        self,
        fixed_arm: str,
        moving_arm: str,
        fixed_segment_color: str,
        moving_segment_color: str,
        angle_degrees: float,
        direction: str,
        fixed_grasp_name: Optional[str] = None,
        moving_grasp_name: Optional[str] = None,
        segment_length: float = 0.15,
        use_d455: bool = True,
        approach_height: float = 0.10,
        speed: float = 0.10,
        waypoint_angle_step_degrees: float = 10.0,
        keep_z_constant: bool = True,
        dry_run: bool = False
    ) -> Dict:
        """Execute bimanual hold-and-rotate task on articulated ruler object.
        
        This method:
        1. Locates all necessary points using VLM before any motion
        2. Computes hinge center from geometry + VLM observation
        3. Plans circular arc trajectory
        4. Validates all waypoints
        5. Executes: fixed arm grasps and holds, moving arm grasps and rotates
        
        Args:
            fixed_arm: Arm to hold fixed segment ('left' or 'right')
            moving_arm: Arm to rotate moving segment ('left' or 'right')
            fixed_segment_color: Color of segment to hold (e.g., 'blue')
            moving_segment_color: Color of segment to rotate (e.g., 'yellow')
            angle_degrees: Rotation angle in degrees
            direction: 'clockwise' or 'counterclockwise'
            fixed_grasp_name: Optional specific grasp point description
            moving_grasp_name: Optional specific grasp point description
            segment_length: Length of each segment in meters (default 0.15m)
            use_d455: Use D455 depth camera
            approach_height: Height offset for pre-grasp
            speed: Motion speed (kept low for safety)
            waypoint_angle_step_degrees: Angle between waypoints
            keep_z_constant: Keep Z constant during rotation
            dry_run: If True, only compute plan without executing
            
        Returns:
            HoldAndRotateResponse dict with full execution details
        """
        print("\n" + "="*70)
        print("BIMANUAL HOLD AND ROTATE")
        print("="*70)
        print(f"Fixed arm: {fixed_arm}, segment: {fixed_segment_color}")
        print(f"Moving arm: {moving_arm}, segment: {moving_segment_color}")
        print(f"Rotation: {angle_degrees}° {direction}")
        print(f"Segment length: {segment_length}m")
        print(f"Dry run: {dry_run}")
        print("="*70 + "\n")
        
        warnings = []
        
        # ============================================================
        # STAGE 1: Parameter Validation
        # ============================================================
        print("[Stage 1] Parameter Validation")
        
        if fixed_arm == moving_arm:
            return {
                "success": False,
                "message": "Fixed arm and moving arm must be different",
                "failed_stage": "parameter_validation"
            }
        
        if fixed_segment_color == moving_segment_color:
            return {
                "success": False,
                "message": "Fixed and moving segments must have different colors",
                "failed_stage": "parameter_validation"
            }
        
        print(f"  ✓ Parameters valid")
        
        # ============================================================
        # STAGE 2: Pre-localization (all points before any motion)
        # ============================================================
        print("\n[Stage 2] Pre-localization")
        print("  Locating all points before robot motion...")
        
        # Generate grasp point descriptions if not provided
        if not fixed_grasp_name:
            fixed_grasp_name = f"{fixed_segment_color} segment grasp block center away from {moving_segment_color} segment"
        
        if not moving_grasp_name:
            moving_grasp_name = f"{moving_segment_color} segment grasp block center away from {fixed_segment_color} segment"
        
        # Locate fixed grasp position
        print(f"\n  [2.1] Locating fixed grasp: {fixed_grasp_name}")
        fixed_grasp_result = await self.locate_named_point(fixed_grasp_name, use_d455)
        if not fixed_grasp_result.get('success') or not fixed_grasp_result.get('found'):
            return {
                "success": False,
                "message": f"Could not locate fixed grasp point: {fixed_grasp_name}",
                "failed_stage": "localization_fixed_grasp"
            }
        fixed_grasp_position = fixed_grasp_result['position']
        print(f"  ✓ Fixed grasp at: {fixed_grasp_position}")
        
        # Locate moving grasp position
        print(f"\n  [2.2] Locating moving grasp: {moving_grasp_name}")
        moving_grasp_result = await self.locate_named_point(moving_grasp_name, use_d455)
        if not moving_grasp_result.get('success') or not moving_grasp_result.get('found'):
            return {
                "success": False,
                "message": f"Could not locate moving grasp point: {moving_grasp_name}",
                "failed_stage": "localization_moving_grasp"
            }
        moving_grasp_position = moving_grasp_result['position']
        print(f"  ✓ Moving grasp at: {moving_grasp_position}")
        
        # Locate fixed segment midpoint
        fixed_midpoint_desc = f"{fixed_segment_color} segment geometric midpoint"
        print(f"\n  [2.3] Locating: {fixed_midpoint_desc}")
        fixed_mid_result = await self.locate_named_point(fixed_midpoint_desc, use_d455)
        if not fixed_mid_result.get('success') or not fixed_mid_result.get('found'):
            return {
                "success": False,
                "message": f"Could not locate fixed segment midpoint",
                "failed_stage": "localization_fixed_midpoint"
            }
        fixed_segment_midpoint = fixed_mid_result['position']
        print(f"  ✓ Fixed midpoint at: {fixed_segment_midpoint}")
        
        # Locate moving segment midpoint
        moving_midpoint_desc = f"{moving_segment_color} segment geometric midpoint"
        print(f"\n  [2.4] Locating: {moving_midpoint_desc}")
        moving_mid_result = await self.locate_named_point(moving_midpoint_desc, use_d455)
        if not moving_mid_result.get('success') or not moving_mid_result.get('found'):
            return {
                "success": False,
                "message": f"Could not locate moving segment midpoint",
                "failed_stage": "localization_moving_midpoint"
            }
        moving_segment_midpoint = moving_mid_result['position']
        print(f"  ✓ Moving midpoint at: {moving_segment_midpoint}")
        
        # Locate hinge (connection point between the two specified segments)
        hinge_desc = f"connection point between {fixed_segment_color} segment and {moving_segment_color} segment"
        print(f"\n  [2.5] Locating: {hinge_desc}")
        hinge_result = await self.locate_named_point(hinge_desc, use_d455)
        if not hinge_result.get('success') or not hinge_result.get('found'):
            return {
                "success": False,
                "message": f"Could not locate hinge between {fixed_segment_color} and {moving_segment_color} segments",
                "failed_stage": "localization_hinge"
            }
        hinge_observed_position = hinge_result['position']
        print(f"  ✓ Observed hinge at: {hinge_observed_position}")
        
        if hinge_result.get('confidence', 100) < 70:
            warnings.append(f"Low confidence ({hinge_result.get('confidence')}%) for hinge localization")
        
        print(f"\n  ✓ All localization complete")

        
        # ============================================================
        # STAGE 3: Geometric Computation
        # ============================================================
        print("\n[Stage 3] Geometric Computation")
        
        # Compute hinge center from two midpoints and observed position
        print("  Computing hinge center from geometry...")
        hinge_result = self.estimate_hinge_center_from_two_midpoints_and_observed_joint(
            midpoint_a=fixed_segment_midpoint,
            midpoint_b=moving_segment_midpoint,
            observed_hinge=hinge_observed_position,
            segment_length=segment_length,
            tolerance=0.02
        )
        
        if not hinge_result.get('success'):
            return {
                "success": False,
                "message": f"Hinge computation failed: {hinge_result.get('error', 'Unknown error')}",
                "failed_stage": "hinge_computation",
                "hinge_computation_result": hinge_result
            }
        
        hinge_position = hinge_result['selected_hinge']
        candidate_hinges = hinge_result['candidate_hinges']
        hinge_selection_reason = hinge_result['selection_reason']
        warnings.extend(hinge_result.get('warnings', []))
        
        print(f"  ✓ Hinge position: {hinge_position}")
        print(f"  ✓ Selection reason: {hinge_selection_reason}")
        
        # Compute target position for moving grasp
        print(f"\n  Computing target position ({angle_degrees}° {direction})...")
        target_position = self.rotate_point_around_center_xy(
            point=moving_grasp_position,
            center=hinge_position,
            angle_degrees=angle_degrees,
            direction=direction
        )
        print(f"  ✓ Target position: {target_position}")
        
        # Plan arc waypoints
        print(f"\n  Planning arc waypoints...")
        waypoints = self.plan_arc_waypoints_xy(
            start_point=moving_grasp_position,
            center=hinge_position,
            angle_degrees=angle_degrees,
            direction=direction,
            waypoint_angle_step_degrees=waypoint_angle_step_degrees
        )
        print(f"  ✓ Generated {len(waypoints)} waypoints")
        
        # ============================================================
        # STAGE 4: Pre-execution Validation
        # ============================================================
        print("\n[Stage 4] Pre-execution Validation")
        
        # Check fixed grasp position
        print(f"  Checking fixed grasp workspace...")
        is_safe, msg = self.safety.check_workspace(fixed_arm, fixed_grasp_position)
        if not is_safe:
            return {
                "success": False,
                "message": f"Fixed grasp position unsafe: {msg}",
                "failed_stage": "validation_fixed_grasp"
            }
        print(f"  ✓ Fixed grasp position safe")
        
        # Check moving grasp position
        print(f"  Checking moving grasp workspace...")
        is_safe, msg = self.safety.check_workspace(moving_arm, moving_grasp_position)
        if not is_safe:
            return {
                "success": False,
                "message": f"Moving grasp position unsafe: {msg}",
                "failed_stage": "validation_moving_grasp"
            }
        print(f"  ✓ Moving grasp position safe")
        
        # Check all waypoints
        print(f"  Checking all {len(waypoints)} waypoints...")
        for i, waypoint in enumerate(waypoints):
            is_safe, msg = self.safety.check_workspace(moving_arm, waypoint)
            if not is_safe:
                return {
                    "success": False,
                    "message": f"Waypoint {i+1} unsafe: {msg}",
                    "failed_stage": "validation_waypoints",
                    "failed_waypoint_index": i
                }
        print(f"  ✓ All waypoints safe")
        
        # If dry_run, return plan without executing
        if dry_run:
            print("\n[Dry Run] Returning plan without execution")
            return {
                "success": True,
                "message": "Dry run complete - plan computed successfully",
                "dry_run": True,
                "fixed_arm": fixed_arm,
                "moving_arm": moving_arm,
                "fixed_segment_color": fixed_segment_color,
                "moving_segment_color": moving_segment_color,
                "fixed_grasp_position": fixed_grasp_position,
                "moving_grasp_position": moving_grasp_position,
                "fixed_segment_midpoint": fixed_segment_midpoint,
                "moving_segment_midpoint": moving_segment_midpoint,
                "hinge_observed_position": hinge_observed_position,
                "candidate_hinges": candidate_hinges,
                "hinge_position": hinge_position,
                "hinge_selection_reason": hinge_selection_reason,
                "target_position": target_position,
                "waypoints": waypoints,
                "angle_degrees": angle_degrees,
                "direction": direction,
                "warnings": warnings
            }

        
        # ============================================================
        # STAGE 5: Robot Execution
        # ============================================================
        print("\n[Stage 5] Robot Execution")
        print("  WARNING: Robot will now move. Ensure workspace is clear.")
        
        orientation = [3.14159, 0.0, 0.0]  # Downward facing
        
        # Step 1: Fixed arm approaches fixed grasp
        print(f"\n  [5.1] {fixed_arm} arm approaching fixed grasp...")
        fixed_pre_grasp = [
            fixed_grasp_position[0],
            fixed_grasp_position[1],
            fixed_grasp_position[2] + approach_height
        ]
        success = self.driver.move_to_pose(fixed_arm, fixed_pre_grasp + orientation, speed)
        if not success:
            return {
                "success": False,
                "message": f"{fixed_arm} arm failed to reach pre-grasp position",
                "failed_stage": "execution_fixed_approach"
            }
        print(f"  ✓ {fixed_arm} at pre-grasp")
        
        # Step 2: Fixed arm descends and grasps
        print(f"\n  [5.2] {fixed_arm} arm descending to grasp...")
        self.driver.gripper_command(fixed_arm, 'open')
        time.sleep(0.5)
        
        success = self.driver.move_to_pose(
            fixed_arm,
            fixed_grasp_position + orientation,
            speed * 0.5
        )
        if not success:
            return {
                "success": False,
                "message": f"{fixed_arm} arm failed to reach grasp position",
                "failed_stage": "execution_fixed_descend"
            }
        
        print(f"  [5.3] {fixed_arm} arm closing gripper...")
        self.driver.gripper_command(fixed_arm, 'close', force=30.0)
        time.sleep(0.8)
        print(f"  ✓ {fixed_arm} holding fixed segment")
        
        # Step 3: Moving arm approaches moving grasp
        print(f"\n  [5.4] {moving_arm} arm approaching moving grasp...")
        moving_pre_grasp = [
            moving_grasp_position[0],
            moving_grasp_position[1],
            moving_grasp_position[2] + approach_height
        ]
        success = self.driver.move_to_pose(moving_arm, moving_pre_grasp + orientation, speed)
        if not success:
            # Release fixed arm before returning
            self.driver.gripper_command(fixed_arm, 'open')
            return {
                "success": False,
                "message": f"{moving_arm} arm failed to reach pre-grasp position",
                "failed_stage": "execution_moving_approach"
            }
        print(f"  ✓ {moving_arm} at pre-grasp")
        
        # Step 4: Moving arm descends and grasps
        print(f"\n  [5.5] {moving_arm} arm descending to grasp...")
        self.driver.gripper_command(moving_arm, 'open')
        time.sleep(0.5)
        
        success = self.driver.move_to_pose(
            moving_arm,
            moving_grasp_position + orientation,
            speed * 0.5
        )
        if not success:
            # Release fixed arm before returning
            self.driver.gripper_command(fixed_arm, 'open')
            return {
                "success": False,
                "message": f"{moving_arm} arm failed to reach grasp position",
                "failed_stage": "execution_moving_descend"
            }
        
        print(f"  [5.6] {moving_arm} arm closing gripper...")
        self.driver.gripper_command(moving_arm, 'close', force=30.0)
        time.sleep(0.8)
        print(f"  ✓ {moving_arm} holding moving segment")
        
        # Step 5: Moving arm follows arc trajectory
        print(f"\n  [5.7] {moving_arm} arm following arc trajectory...")
        print(f"  Rotating {angle_degrees}° {direction} around hinge at {hinge_position}")
        
        arc_result = self.follow_arc_waypoints(
            arm=moving_arm,
            waypoints=waypoints,
            orientation=orientation,
            speed=speed
        )
        
        if not arc_result['success']:
            # Release both arms before returning
            self.driver.gripper_command(moving_arm, 'open')
            time.sleep(0.3)
            self.driver.gripper_command(fixed_arm, 'open')
            return {
                "success": False,
                "message": f"Arc trajectory failed: {arc_result['message']}",
                "failed_stage": "execution_arc_trajectory",
                "failed_waypoint_index": arc_result.get('failed_waypoint_index'),
                "completed_waypoints": arc_result.get('completed_waypoints', 0)
            }
        
        print(f"  ✓ Arc trajectory complete")
        
        # Step 6: Release moving arm
        print(f"\n  [5.8] Releasing {moving_arm} arm...")
        self.driver.gripper_command(moving_arm, 'open')
        time.sleep(0.5)
        print(f"  ✓ {moving_arm} released")
        
        # Step 7: Release fixed arm
        print(f"\n  [5.9] Releasing {fixed_arm} arm...")
        self.driver.gripper_command(fixed_arm, 'open')
        time.sleep(0.5)
        print(f"  ✓ {fixed_arm} released")
        
        # ============================================================
        # STAGE 6: Return Results
        # ============================================================
        print("\n[Stage 6] Task Complete")
        print("="*70)
        print(f"✓ Successfully rotated {moving_segment_color} segment")
        print(f"  {angle_degrees}° {direction} around hinge at {hinge_position}")
        print("="*70 + "\n")
        
        return {
            "success": True,
            "message": f"Successfully rotated {moving_segment_color} segment {angle_degrees}° {direction}",
            "fixed_arm": fixed_arm,
            "moving_arm": moving_arm,
            "fixed_segment_color": fixed_segment_color,
            "moving_segment_color": moving_segment_color,
            "fixed_grasp_position": fixed_grasp_position,
            "moving_grasp_position": moving_grasp_position,
            "fixed_segment_midpoint": fixed_segment_midpoint,
            "moving_segment_midpoint": moving_segment_midpoint,
            "hinge_observed_position": hinge_observed_position,
            "candidate_hinges": candidate_hinges,
            "hinge_position": hinge_position,
            "hinge_selection_reason": hinge_selection_reason,
            "target_position": target_position,
            "waypoints": waypoints,
            "angle_degrees": angle_degrees,
            "direction": direction,
            "warnings": warnings,
            "dry_run": False
        }


    # ============================================================
    # Bimanual Shape Ruler: Geometry Helpers
    # ============================================================

    def distance_xy(self, point_a: List[float], point_b: List[float]) -> float:
        """Calculate XY distance between two points."""
        return np.sqrt((point_a[0] - point_b[0])**2 + (point_a[1] - point_b[1])**2)

    def normalize_xy(self, vec: List[float]) -> List[float]:
        """Normalize 2D vector."""
        length = np.sqrt(vec[0]**2 + vec[1]**2)
        if length < 1e-6:
            return [1.0, 0.0]
        return [vec[0] / length, vec[1] / length]

    def rotate_vector_2d(self, vec: List[float], angle_rad: float) -> List[float]:
        """Rotate 2D vector by angle (radians)."""
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        return [
            cos_a * vec[0] - sin_a * vec[1],
            sin_a * vec[0] + cos_a * vec[1]
        ]

    def line_intersection_2d(
        self,
        p1: List[float],
        p2: List[float],
        q1: List[float],
        q2: List[float],
        eps: float = 1e-6
    ) -> Optional[List[float]]:
        """Calculate intersection of two infinite 2D lines.

        Args:
            p1: First point on line 1 (x, y)
            p2: Second point on line 1 (x, y)
            q1: First point on line 2 (x, y)
            q2: Second point on line 2 (x, y)
            eps: Threshold for detecting parallel lines

        Returns:
            Intersection point [x, y] or None if lines are parallel
        """
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]
        x3, y3 = q1[0], q1[1]
        x4, y4 = q2[0], q2[1]

        # Calculate denominator
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

        # Check if lines are parallel
        if abs(denom) < eps:
            return None

        # Calculate intersection point
        px = ((x1*y2 - y1*x2) * (x3 - x4) - (x1 - x2) * (x3*y4 - y3*x4)) / denom
        py = ((x1*y2 - y1*x2) * (y3 - y4) - (y1 - y2) * (x3*y4 - y3*x4)) / denom

        return [px, py]

    def midpoint_2d(self, p1: List[float], p2: List[float]) -> List[float]:
        """Calculate midpoint of two 2D points.

        Args:
            p1: First point (x, y) or (x, y, z)
            p2: Second point (x, y) or (x, y, z)

        Returns:
            Midpoint [x, y]
        """
        return [(p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0]

    def generate_arc_waypoints(
        self,
        center_xy: List[float],
        start_xy: List[float],
        angle_degrees: float,
        direction: str,
        num_waypoints: int,
        z: float,
        orientation: List[float]
    ) -> Dict:
        """Generate waypoints along a circular arc for pushing motion.

        Args:
            center_xy: Arc center [x, y] (red grasp position)
            start_xy: Arc start point [x, y] (blue push position)
            angle_degrees: Arc angle in degrees (e.g., 90)
            direction: "clockwise" or "counterclockwise"
            num_waypoints: Number of waypoints along the arc
            z: Fixed Z coordinate for all waypoints
            orientation: Fixed end-effector orientation [roll, pitch, yaw]

        Returns:
            Dict with 'success', 'waypoints', 'radius', 'angle_rad'
        """
        # Calculate vector from center to start
        vx = start_xy[0] - center_xy[0]
        vy = start_xy[1] - center_xy[1]

        # Calculate radius
        radius = np.sqrt(vx**2 + vy**2)

        # Convert angle to radians
        angle_rad = np.deg2rad(angle_degrees)

        # Determine direction sign
        if direction == "clockwise":
            direction_sign = -1
        elif direction == "counterclockwise":
            direction_sign = 1
        else:
            return {
                "success": False,
                "message": f"Invalid direction: {direction}. Must be 'clockwise' or 'counterclockwise'"
            }

        # Generate waypoints
        waypoints = []
        for i in range(num_waypoints + 1):  # Include endpoint
            # Calculate rotation angle for this waypoint
            alpha = direction_sign * angle_rad * i / num_waypoints

            # Apply 2D rotation
            x_i = center_xy[0] + np.cos(alpha) * vx - np.sin(alpha) * vy
            y_i = center_xy[1] + np.sin(alpha) * vx + np.cos(alpha) * vy

            # Create full pose (position + orientation)
            waypoint = [x_i, y_i, z] + orientation
            waypoints.append(waypoint)

        return {
            "success": True,
            "waypoints": waypoints,
            "radius": radius,
            "angle_rad": angle_rad,
            "num_waypoints": len(waypoints)
        }

    def interpolate_angle(
        self,
        theta_start: float,
        theta_end: float,
        ratio: float,
        direction: str = "auto"
    ) -> float:
        """Interpolate angle with direction control.
        
        Args:
            theta_start: Start angle in radians
            theta_end: End angle in radians
            ratio: Interpolation ratio [0, 1]
            direction: 'auto' (shortest), 'clockwise', 'counterclockwise'
        
        Returns:
            Interpolated angle in radians
        """
        # Normalize angles to [-pi, pi]
        theta_start = np.arctan2(np.sin(theta_start), np.cos(theta_start))
        theta_end = np.arctan2(np.sin(theta_end), np.cos(theta_end))
        
        if direction == "auto":
            # Shortest path
            delta = theta_end - theta_start
            if delta > np.pi:
                delta -= 2 * np.pi
            elif delta < -np.pi:
                delta += 2 * np.pi
        elif direction == "clockwise":
            # Force clockwise (negative direction)
            delta = theta_end - theta_start
            if delta > 0:
                delta -= 2 * np.pi
        elif direction == "counterclockwise":
            # Force counterclockwise (positive direction)
            delta = theta_end - theta_start
            if delta < 0:
                delta += 2 * np.pi
        else:
            raise ValueError(f"Invalid direction: {direction}")
        
        return theta_start + ratio * delta

    def convert_to_motion_coordinates(
        self,
        raw_positions: Dict[str, List[float]],
        motion_z: float
    ) -> Dict[str, List[float]]:
        """Convert raw VLM positions to motion coordinates.
        
        Keep XY from raw, override Z with motion_z.
        
        Args:
            raw_positions: Dict of raw positions from VLM
            motion_z: Fixed Z coordinate for motion
            
        Returns:
            Dict of motion coordinates
        """
        motion_positions = {}
        for key, raw_pos in raw_positions.items():
            motion_positions[key] = [raw_pos[0], raw_pos[1], motion_z]
        return motion_positions


    def calculate_two_link_target_L_shape(
        self,
        motion_R: List[float],
        motion_G: List[float],
        motion_O: List[float],
        motion_B: List[float],
        l_shape_blue_turn_direction: str,
        red_yellow_target_angle_deg: float,
        red_yellow_bend_direction: str,
        blue_yellow_target_angle_deg: float
    ) -> Dict:
        """Calculate L-shape target configuration with configurable joint angles.
        
        Args:
            motion_R: Red grasp position (motion coordinates)
            motion_G: Green joint position (motion coordinates)
            motion_O: Orange joint position (motion coordinates)
            motion_B: Blue push position (motion coordinates)
            l_shape_blue_turn_direction: 'clockwise' or 'counterclockwise'
            red_yellow_target_angle_deg: Target angle at green joint (degrees)
            red_yellow_bend_direction: 'clockwise' or 'counterclockwise'
            blue_yellow_target_angle_deg: Target angle at orange joint (degrees)
            
        Returns:
            Dict with L1, L2, target positions, and direction vectors
        """
        print(f"[L-Shape] Calculating target configuration...")
        
        # 1. Calculate actual link lengths (XY only)
        L1 = self.distance_xy(motion_G, motion_O)
        L2 = self.distance_xy(motion_O, motion_B)
        
        print(f"[L-Shape] L1 (G-O): {L1:.3f}m")
        print(f"[L-Shape] L2 (O-B): {L2:.3f}m")
        
        # 2. Red segment direction (from R to G)
        u_red_RtoG = self.normalize_xy([
            motion_G[0] - motion_R[0],
            motion_G[1] - motion_R[1]
        ])
        
        print(f"[L-Shape] Red segment direction (R→G): [{u_red_RtoG[0]:.3f}, {u_red_RtoG[1]:.3f}]")
        
        # 3. Calculate yellow segment target direction
        # Physical joint angle = 180° means fully extended (collinear)
        # Physical joint angle = 165° means 15° bend
        
        u_red_extension = u_red_RtoG  # Extension direction
        
        # Calculate bend angle
        bend_angle_deg = 180.0 - red_yellow_target_angle_deg
        bend_angle_rad = np.radians(bend_angle_deg)
        
        print(f"[L-Shape] Target green joint angle: {red_yellow_target_angle_deg}°")
        print(f"[L-Shape] Bend angle from extension: {bend_angle_deg}°")
        
        # Apply bend direction
        if red_yellow_bend_direction == "clockwise":
            u_yellow_target = self.rotate_vector_2d(u_red_extension, -bend_angle_rad)
        else:
            u_yellow_target = self.rotate_vector_2d(u_red_extension, +bend_angle_rad)
        
        print(f"[L-Shape] Yellow target direction: [{u_yellow_target[0]:.3f}, {u_yellow_target[1]:.3f}]")
        
        # 4. Calculate blue segment target direction
        # Use configurable angle instead of hardcoded 90°
        blue_bend_angle_deg = 180.0 - blue_yellow_target_angle_deg
        blue_bend_angle_rad = np.radians(blue_bend_angle_deg)
        
        print(f"[L-Shape] Target orange joint angle: {blue_yellow_target_angle_deg}°")
        
        if l_shape_blue_turn_direction == "clockwise":
            u_blue_target = self.rotate_vector_2d(u_yellow_target, -blue_bend_angle_rad)
        else:
            u_blue_target = self.rotate_vector_2d(u_yellow_target, +blue_bend_angle_rad)
        
        print(f"[L-Shape] Blue target direction: [{u_blue_target[0]:.3f}, {u_blue_target[1]:.3f}]")
        
        # 5. Calculate target positions
        O_target = [
            motion_G[0] + L1 * u_yellow_target[0],
            motion_G[1] + L1 * u_yellow_target[1],
            motion_G[2]
        ]
        
        B_target = [
            O_target[0] + L2 * u_blue_target[0],
            O_target[1] + L2 * u_blue_target[1],
            motion_B[2]
        ]
        
        print(f"[L-Shape] O_target: {O_target}")
        print(f"[L-Shape] B_target: {B_target}")
        
        return {
            "L1": L1,
            "L2": L2,
            "u_red_RtoG": u_red_RtoG,
            "u_red_extension": u_red_extension,
            "u_yellow_target": u_yellow_target,
            "u_blue_target": u_blue_target,
            "O_target": O_target,
            "B_target": B_target,
            "red_yellow_target_angle_deg": red_yellow_target_angle_deg,
            "blue_yellow_target_angle_deg": blue_yellow_target_angle_deg,
            "bend_angle_deg": bend_angle_deg
        }


    def plan_two_link_waypoints(
        self,
        motion_R: List[float],
        motion_G: List[float],
        motion_O: List[float],
        motion_B: List[float],
        O_target: List[float],
        B_target: List[float],
        L1: float,
        L2: float,
        config: Dict
    ) -> Dict:
        """Plan waypoints using two-link angle interpolation with full validation.
        
        Args:
            motion_R: Red grasp position
            motion_G: Green joint position
            motion_O: Orange joint position (current)
            motion_B: Blue push position (current)
            O_target: Target orange joint position
            B_target: Target blue push position
            L1: Yellow segment length (G-O)
            L2: Blue segment length (O-B)
            config: Planning configuration dict
            
        Returns:
            Dict with waypoints, joint angle checks, and validation results
        """
        print(f"\n[Planning] Generating two-link waypoints...")
        
        waypoint_count = config['waypoint_count']
        theta1_dir = config['theta1_interpolation_direction']
        theta2_dir = config['theta2_interpolation_direction']
        green_min = config['green_joint_min_angle_deg']
        green_max = config['green_joint_max_angle_deg']
        orange_min = config['orange_joint_min_angle_deg']
        orange_max = config['orange_joint_max_angle_deg']
        push_offset = config['push_contact_offset_xy']
        skip_first = config['skip_first_waypoint']
        
        warnings = []
        
        # Current angles
        theta1_current = np.arctan2(
            motion_O[1] - motion_G[1],
            motion_O[0] - motion_G[0]
        )
        theta2_current = np.arctan2(
            motion_B[1] - motion_O[1],
            motion_B[0] - motion_O[0]
        )
        
        print(f"[Planning] Current theta1 (G→O): {np.degrees(theta1_current):.1f}°")
        print(f"[Planning] Current theta2 (O→B): {np.degrees(theta2_current):.1f}°")
        
        # Target angles
        theta1_target = np.arctan2(
            O_target[1] - motion_G[1],
            O_target[0] - motion_G[0]
        )
        theta2_target = np.arctan2(
            B_target[1] - O_target[1],
            B_target[0] - O_target[0]
        )
        
        print(f"[Planning] Target theta1 (G→O): {np.degrees(theta1_target):.1f}°")
        print(f"[Planning] Target theta2 (O→B): {np.degrees(theta2_target):.1f}°")
        
        # Red segment direction (for green joint angle calculation)
        theta_red_at_green = np.arctan2(
            motion_R[1] - motion_G[1],
            motion_R[0] - motion_G[0]
        )
        
        all_model_waypoints = []
        waypoint_yaws = []
        green_joint_checks = []
        orange_joint_checks = []
        joint_limit_violation = False
        
        print(f"[Planning] Generating {waypoint_count} waypoints...")
        
        for k in range(waypoint_count):
            ratio = k / (waypoint_count - 1)
            
            # Angle interpolation with direction control
            theta1_k = self.interpolate_angle(
                theta1_current, theta1_target, ratio, theta1_dir
            )
            theta2_k = self.interpolate_angle(
                theta2_current, theta2_target, ratio, theta2_dir
            )
            
            # Forward kinematics
            O_k = [
                motion_G[0] + L1 * np.cos(theta1_k),
                motion_G[1] + L1 * np.sin(theta1_k),
                motion_G[2]
            ]
            
            B_k = [
                O_k[0] + L2 * np.cos(theta2_k),
                O_k[1] + L2 * np.sin(theta2_k),
                motion_B[2]
            ]
            
            all_model_waypoints.append(B_k)
            waypoint_yaws.append(theta2_k)
            
            # Green joint angle check (angle between G→R and G→O)
            theta_yellow_at_green = theta1_k
            green_angle_rad = abs(theta_yellow_at_green - theta_red_at_green)
            green_angle_deg = np.degrees(green_angle_rad)
            
            # Normalize to [0, 180]
            if green_angle_deg > 180:
                green_angle_deg = 360 - green_angle_deg
            
            green_pass = green_min <= green_angle_deg <= green_max
            
            green_joint_checks.append({
                "model_waypoint_index": k,
                "execution_waypoint_index": k - 1 if skip_first and k > 0 else k,
                "joint_angle_deg": green_angle_deg,
                "check_pass": green_pass,
                "joint_name": "green_joint",
                "description": "Angle between G→R and G→O"
            })
            
            if not green_pass:
                joint_limit_violation = True
                warnings.append(
                    f"Model waypoint {k}: GREEN joint angle {green_angle_deg:.1f}° "
                    f"outside range [{green_min}, {green_max}]"
                )
            
            # Orange joint angle check (angle between O→G and O→B)
            theta_yellow_at_orange = np.arctan2(
                motion_G[1] - O_k[1],
                motion_G[0] - O_k[0]
            )
            theta_blue_at_orange = theta2_k
            
            orange_angle_rad = abs(theta_blue_at_orange - theta_yellow_at_orange)
            orange_angle_deg = np.degrees(orange_angle_rad)
            
            # Normalize to [0, 180]
            if orange_angle_deg > 180:
                orange_angle_deg = 360 - orange_angle_deg
            
            orange_pass = orange_min <= orange_angle_deg <= orange_max
            
            orange_joint_checks.append({
                "model_waypoint_index": k,
                "execution_waypoint_index": k - 1 if skip_first and k > 0 else k,
                "joint_angle_deg": orange_angle_deg,
                "check_pass": orange_pass,
                "joint_name": "orange_joint",
                "description": "Angle between O→G and O→B"
            })
            
            if not orange_pass:
                joint_limit_violation = True
                warnings.append(
                    f"Model waypoint {k}: ORANGE joint angle {orange_angle_deg:.1f}° "
                    f"outside range [{orange_min}, {orange_max}]"
                )
        
        print(f"[Planning] Generated {len(all_model_waypoints)} model waypoints")
        
        # Generate execution waypoints (skip first if configured)
        if skip_first and len(all_model_waypoints) > 1:
            execution_waypoints = all_model_waypoints[1:]
            warnings.append("Skipped first waypoint (current position) to avoid jitter")
            print(f"[Planning] Skipping first waypoint, execution waypoints: {len(execution_waypoints)}")
        else:
            execution_waypoints = all_model_waypoints.copy()
            print(f"[Planning] Using all waypoints for execution: {len(execution_waypoints)}")
        
        # Generate push execution waypoints (add offset)
        push_execution_waypoints = []
        for wp in execution_waypoints:
            push_wp = [
                wp[0] + push_offset[0],
                wp[1] + push_offset[1],
                wp[2]
            ]
            push_execution_waypoints.append(push_wp)
        
        if push_offset[0] != 0 or push_offset[1] != 0:
            print(f"[Planning] Applied push contact offset: {push_offset}")
        
        return {
            "all_model_waypoints": all_model_waypoints,
            "execution_waypoints": execution_waypoints,
            "push_execution_waypoints": push_execution_waypoints,
            "waypoint_yaws": waypoint_yaws,
            "green_joint_angle_checks": green_joint_checks,
            "orange_joint_angle_checks": orange_joint_checks,
            "joint_limit_violation": joint_limit_violation,
            "warnings": warnings
        }


    def validate_all_execution_poses(
        self,
        fixed_arm: str,
        moving_arm: str,
        motion_R: List[float],
        approach_R: List[float],
        push_start_approach: List[float],
        push_start_contact: List[float],
        push_execution_waypoints: List[List[float]],
        retreat_pose: Optional[List[float]],
        orientation: List[float]
    ) -> Dict:
        """Validate all poses for safety and IK reachability.
        
        Uses complete pose (position + orientation) for validation.
        
        Args:
            fixed_arm: Fixed arm name
            moving_arm: Moving arm name
            motion_R: Red grasp position
            approach_R: Red approach position
            push_start_approach: Push start approach position
            push_start_contact: Push start contact position
            push_execution_waypoints: All push waypoints
            retreat_pose: Optional retreat position
            orientation: End-effector orientation [roll, pitch, yaw]
            
        Returns:
            Dict with validation results and failed pose info
        """
        print(f"\n[Validation] Checking all execution poses...")
        
        poses_to_check = [
            ("fixed_arm_approach_R", fixed_arm, approach_R + orientation),
            ("fixed_arm_motion_R", fixed_arm, motion_R + orientation),
            ("moving_arm_push_start_approach", moving_arm, push_start_approach + orientation),
            ("moving_arm_push_start_contact", moving_arm, push_start_contact + orientation),
        ]
        
        # Add all push waypoints
        for i, wp in enumerate(push_execution_waypoints):
            poses_to_check.append((
                f"moving_arm_push_waypoint_{i}",
                moving_arm,
                wp + orientation
            ))
        
        # Add retreat pose
        if retreat_pose:
            poses_to_check.append((
                "moving_arm_retreat",
                moving_arm,
                retreat_pose + orientation
            ))
        
        print(f"[Validation] Total poses to check: {len(poses_to_check)}")
        
        validation_results = []
        
        for pose_name, arm, full_pose in poses_to_check:
            # Extract position for safety check
            position = full_pose[:3]
            
            # Safety check (position only)
            is_safe, safety_msg = self.safety.check_workspace(arm, position)
            
            # IK check using FULL pose (position + orientation)
            is_reachable = self.driver.check_pose_reachable(arm, full_pose, silent=True)
            
            check_pass = is_safe and is_reachable
            
            validation_results.append({
                "pose_name": pose_name,
                "arm": arm,
                "position": position,
                "orientation": full_pose[3:],
                "full_pose": full_pose,
                "safety_check": is_safe,
                "safety_message": safety_msg if not is_safe else "OK",
                "ik_check": is_reachable,
                "ik_message": "Reachable" if is_reachable else "Unreachable",
                "check_pass": check_pass
            })
            
            if not check_pass:
                print(f"[Validation] ✗ Failed at {pose_name}")
                if not is_safe:
                    print(f"  Safety: {safety_msg}")
                if not is_reachable:
                    print(f"  IK: Unreachable")
                
                return {
                    "success": False,
                    "failed_pose": pose_name,
                    "validation_results": validation_results
                }
        
        print(f"[Validation] ✓ All {len(poses_to_check)} poses validated successfully")
        
        return {
            "success": True,
            "validation_results": validation_results
        }


    # ============================================================
    # Bimanual Shape Ruler: Main Method
    # ============================================================

    async def locate_ruler_endpoints_and_calculate_joints(
        self,
        segments_config: Dict,
        joints_config: Dict,
        motion_z: float
    ) -> Dict:
        """Locate 6 segment endpoints via VLM and calculate joint positions.

        This method implements the centerline intersection approach:
        1. Locate 6 endpoints (2 per segment) using VLM
        2. Calculate centerlines from endpoints
        3. Calculate joint positions as centerline intersections
        4. Calculate grasp/push positions as segment midpoints

        Args:
            segments_config: Segment configuration from YAML
            joints_config: Joint calculation parameters from YAML
            motion_z: Fixed Z coordinate for motion

        Returns:
            Dict with all calculated positions and debug info
        """
        # ANSI colors
        GREEN = '\033[92m'
        RED = '\033[91m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        RESET = '\033[0m'

        print(f"\n{CYAN}[Endpoint Localization]{RESET} Locating 6 segment endpoints...")

        endpoints_raw = {}
        endpoints_motion = {}

        # ============================================================
        # Step 1: Locate 6 endpoints via VLM
        # ============================================================

        # Red segment endpoints
        print(f"\n  {BLUE}[1/6]{RESET} Locating red segment endpoint (near yellow)...")
        prompt = segments_config['red']['endpoint_near_prompt']
        print(f"       Prompt: {YELLOW}{prompt}{RESET}")
        result = await self.locate_named_point(prompt, use_d455=True)
        if not result.get('success') or not result.get('found'):
            return {
                "success": False,
                "message": "Failed to locate red segment endpoint (near yellow)",
                "failed_point": "red_endpoint_near"
            }
        endpoints_raw['red_near'] = result['position']
        print(f"       {GREEN}✓ Red near:{RESET} {endpoints_raw['red_near']}")

        print(f"\n  {BLUE}[2/6]{RESET} Locating red segment endpoint (far from yellow)...")
        prompt = segments_config['red']['endpoint_far_prompt']
        print(f"       Prompt: {YELLOW}{prompt}{RESET}")
        result = await self.locate_named_point(prompt, use_d455=True)
        if not result.get('success') or not result.get('found'):
            return {
                "success": False,
                "message": "Failed to locate red segment endpoint (far from yellow)",
                "failed_point": "red_endpoint_far"
            }
        endpoints_raw['red_far'] = result['position']
        print(f"       {GREEN}✓ Red far:{RESET} {endpoints_raw['red_far']}")

        # Yellow segment endpoints
        print(f"\n  {BLUE}[3/6]{RESET} Locating yellow segment endpoint (near red)...")
        prompt = segments_config['yellow']['endpoint_near_red_prompt']
        print(f"       Prompt: {YELLOW}{prompt}{RESET}")
        result = await self.locate_named_point(prompt, use_d455=True)
        if not result.get('success') or not result.get('found'):
            return {
                "success": False,
                "message": "Failed to locate yellow segment endpoint (near red)",
                "failed_point": "yellow_endpoint_near_red"
            }
        endpoints_raw['yellow_near_red'] = result['position']
        print(f"       {GREEN}✓ Yellow near red:{RESET} {endpoints_raw['yellow_near_red']}")

        print(f"\n  {BLUE}[4/6]{RESET} Locating yellow segment endpoint (near blue)...")
        prompt = segments_config['yellow']['endpoint_near_blue_prompt']
        print(f"       Prompt: {YELLOW}{prompt}{RESET}")
        result = await self.locate_named_point(prompt, use_d455=True)
        if not result.get('success') or not result.get('found'):
            return {
                "success": False,
                "message": "Failed to locate yellow segment endpoint (near blue)",
                "failed_point": "yellow_endpoint_near_blue"
            }
        endpoints_raw['yellow_near_blue'] = result['position']
        print(f"       {GREEN}✓ Yellow near blue:{RESET} {endpoints_raw['yellow_near_blue']}")

        # Blue segment endpoints
        print(f"\n  {BLUE}[5/6]{RESET} Locating blue segment endpoint (near yellow)...")
        prompt = segments_config['blue']['endpoint_near_prompt']
        print(f"       Prompt: {YELLOW}{prompt}{RESET}")
        result = await self.locate_named_point(prompt, use_d455=True)
        if not result.get('success') or not result.get('found'):
            return {
                "success": False,
                "message": "Failed to locate blue segment endpoint (near yellow)",
                "failed_point": "blue_endpoint_near"
            }
        endpoints_raw['blue_near'] = result['position']
        print(f"       {GREEN}✓ Blue near:{RESET} {endpoints_raw['blue_near']}")

        print(f"\n  {BLUE}[6/6]{RESET} Locating blue segment endpoint (far from yellow)...")
        prompt = segments_config['blue']['endpoint_far_prompt']
        print(f"       Prompt: {YELLOW}{prompt}{RESET}")
        result = await self.locate_named_point(prompt, use_d455=True)
        if not result.get('success') or not result.get('found'):
            return {
                "success": False,
                "message": "Failed to locate blue segment endpoint (far from yellow)",
                "failed_point": "blue_endpoint_far"
            }
        endpoints_raw['blue_far'] = result['position']
        print(f"       {GREEN}✓ Blue far:{RESET} {endpoints_raw['blue_far']}")

        print(f"\n  {GREEN}✓ All 6 endpoints located{RESET}")

        # ============================================================
        # Step 2: Convert to motion coordinates (fixed Z)
        # ============================================================
        print(f"\n{CYAN}[Coordinate Conversion]{RESET} Converting to motion coordinates (Z={motion_z})...")

        for key, raw_pos in endpoints_raw.items():
            endpoints_motion[key] = [raw_pos[0], raw_pos[1], motion_z]

        # ============================================================
        # Step 3: Validate segment lengths
        # ============================================================
        print(f"\n{CYAN}[Validation]{RESET} Checking segment lengths...")

        min_length = joints_config['min_segment_length']

        red_length = self.distance_xy(endpoints_motion['red_near'], endpoints_motion['red_far'])
        yellow_length = self.distance_xy(endpoints_motion['yellow_near_red'], endpoints_motion['yellow_near_blue'])
        blue_length = self.distance_xy(endpoints_motion['blue_near'], endpoints_motion['blue_far'])

        print(f"  Red segment length: {red_length:.3f}m")
        print(f"  Yellow segment length: {yellow_length:.3f}m")
        print(f"  Blue segment length: {blue_length:.3f}m")
        print(f"  Minimum required: {min_length:.3f}m")

        if red_length < min_length:
            return {
                "success": False,
                "message": f"Red segment too short: {red_length:.3f}m < {min_length:.3f}m",
                "failed_check": "red_segment_length"
            }
        if yellow_length < min_length:
            return {
                "success": False,
                "message": f"Yellow segment too short: {yellow_length:.3f}m < {min_length:.3f}m",
                "failed_check": "yellow_segment_length"
            }
        if blue_length < min_length:
            return {
                "success": False,
                "message": f"Blue segment too short: {blue_length:.3f}m < {min_length:.3f}m",
                "failed_check": "blue_segment_length"
            }

        print(f"  {GREEN}✓ All segments valid{RESET}")

        # ============================================================
        # Step 4: Calculate centerline intersections
        # ============================================================
        print(f"\n{CYAN}[Centerline Intersection]{RESET} Calculating joint positions...")

        # Calculate green joint (red-yellow intersection)
        green_joint_xy = self.line_intersection_2d(
            endpoints_motion['red_near'], endpoints_motion['red_far'],
            endpoints_motion['yellow_near_red'], endpoints_motion['yellow_near_blue']
        )

        if green_joint_xy is None:
            return {
                "success": False,
                "message": "Red and yellow centerlines are parallel",
                "failed_check": "green_joint_parallel"
            }

        green_joint = [green_joint_xy[0], green_joint_xy[1], motion_z]
        print(f"  {GREEN}✓ Green joint:{RESET} {green_joint}")

        # Calculate orange joint (blue-yellow intersection)
        orange_joint_xy = self.line_intersection_2d(
            endpoints_motion['blue_near'], endpoints_motion['blue_far'],
            endpoints_motion['yellow_near_red'], endpoints_motion['yellow_near_blue']
        )

        if orange_joint_xy is None:
            return {
                "success": False,
                "message": "Blue and yellow centerlines are parallel",
                "failed_check": "orange_joint_parallel"
            }

        orange_joint = [orange_joint_xy[0], orange_joint_xy[1], motion_z]
        print(f"  {GREEN}✓ Orange joint:{RESET} {orange_joint}")

        # ============================================================
        # Step 5: Validate intersection distances
        # ============================================================
        print(f"\n{CYAN}[Intersection Validation]{RESET} Checking joint positions...")

        max_dist = joints_config['max_intersection_distance']

        # Check green joint distance to nearby endpoints
        dist_green_to_red_near = self.distance_xy(green_joint, endpoints_motion['red_near'])
        dist_green_to_yellow_near_red = self.distance_xy(green_joint, endpoints_motion['yellow_near_red'])

        print(f"  Green joint to red_near: {dist_green_to_red_near:.3f}m")
        print(f"  Green joint to yellow_near_red: {dist_green_to_yellow_near_red:.3f}m")

        if dist_green_to_red_near > max_dist and dist_green_to_yellow_near_red > max_dist:
            return {
                "success": False,
                "message": f"Green joint too far from connection endpoints (>{max_dist:.3f}m)",
                "failed_check": "green_joint_distance"
            }

        # Check orange joint distance to nearby endpoints
        dist_orange_to_blue_near = self.distance_xy(orange_joint, endpoints_motion['blue_near'])
        dist_orange_to_yellow_near_blue = self.distance_xy(orange_joint, endpoints_motion['yellow_near_blue'])

        print(f"  Orange joint to blue_near: {dist_orange_to_blue_near:.3f}m")
        print(f"  Orange joint to yellow_near_blue: {dist_orange_to_yellow_near_blue:.3f}m")

        if dist_orange_to_blue_near > max_dist and dist_orange_to_yellow_near_blue > max_dist:
            return {
                "success": False,
                "message": f"Orange joint too far from connection endpoints (>{max_dist:.3f}m)",
                "failed_check": "orange_joint_distance"
            }

        print(f"  {GREEN}✓ Joint positions valid{RESET}")

        # ============================================================
        # Step 6: Calculate grasp and push positions
        # ============================================================
        print(f"\n{CYAN}[Position Calculation]{RESET} Calculating grasp/push positions...")

        # Red grasp position = midpoint of red segment
        red_grasp_xy = self.midpoint_2d(endpoints_motion['red_near'], endpoints_motion['red_far'])
        red_grasp = [red_grasp_xy[0], red_grasp_xy[1], motion_z]
        print(f"  {GREEN}✓ Red grasp:{RESET} {red_grasp}")

        # Blue push position = midpoint of blue segment
        blue_push_xy = self.midpoint_2d(endpoints_motion['blue_near'], endpoints_motion['blue_far'])
        blue_push = [blue_push_xy[0], blue_push_xy[1], motion_z]
        print(f"  {GREEN}✓ Blue push:{RESET} {blue_push}")

        # ============================================================
        # Return all calculated positions
        # ============================================================
        return {
            "success": True,
            "message": "Successfully calculated all positions from endpoints",

            # Raw endpoints
            "endpoints_raw": endpoints_raw,
            "endpoints_motion": endpoints_motion,

            # Segment lengths
            "red_length": red_length,
            "yellow_length": yellow_length,
            "blue_length": blue_length,

            # Calculated positions
            "green_joint": green_joint,
            "orange_joint": orange_joint,
            "red_grasp": red_grasp,
            "blue_push": blue_push,

            # Validation info
            "green_joint_distances": {
                "to_red_near": dist_green_to_red_near,
                "to_yellow_near_red": dist_green_to_yellow_near_red
            },
            "orange_joint_distances": {
                "to_blue_near": dist_orange_to_blue_near,
                "to_yellow_near_blue": dist_orange_to_yellow_near_blue
            }
        }


    # ============================================================
    # Bimanual Shape Ruler: SIMPLIFIED Arc-Pushing Version
    # ============================================================

    async def bimanual_shape_ruler(
        self,
        fixed_arm: str = "left",
        moving_arm: str = "right",
        target_shape: str = "L",
        l_shape_blue_turn_direction: str = "clockwise",
        config_path: str = "config/ruler_task.yaml",
        dry_run: bool = False
    ) -> Dict:
        """Execute bimanual shape ruler task using SIMPLIFIED arc-pushing approach.

        SIMPLIFIED VERSION:
        - VLM locates only 2 points: red grasp position and blue push position
        - Left arm grasps and holds red segment
        - Right arm pushes blue segment along a 90-degree circular arc
        - Arc center = red grasp position
        - Arc start = blue push position
        - No joint localization, no endpoint localization, no complex geometry

        Args:
            fixed_arm: Arm to grasp red segment ('left' or 'right')
            moving_arm: Arm to push blue segment ('left' or 'right')
            target_shape: Target shape (kept for compatibility, not used)
            l_shape_blue_turn_direction: Arc direction ('clockwise'/'counterclockwise')
            config_path: Path to ruler task configuration file
            dry_run: If True, only compute plan without executing

        Returns:
            Dict with execution results
        """
        # ANSI color codes
        GREEN = '\033[92m'
        RED = '\033[91m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        BOLD = '\033[1m'
        RESET = '\033[0m'

        print(f"\n{CYAN}{BOLD}{'='*70}{RESET}")
        print(f"{CYAN}{BOLD}BIMANUAL SHAPE RULER - SIMPLIFIED ARC-PUSHING{RESET}")
        print(f"{CYAN}{BOLD}{'='*70}{RESET}")
        print(f"{BLUE}Fixed arm:{RESET} {fixed_arm} (grasp red segment)")
        print(f"{BLUE}Moving arm:{RESET} {moving_arm} {YELLOW}(push blue segment, gripper OPEN){RESET}")
        print(f"{BLUE}Arc direction:{RESET} {l_shape_blue_turn_direction}")
        print(f"{BLUE}Config:{RESET} {config_path}")
        print(f"{BLUE}Dry run:{RESET} {dry_run}")
        print(f"{CYAN}{BOLD}{'='*70}{RESET}\n")

        # ============================================================
        # STAGE 1: Load Configuration
        # ============================================================
        print(f"{CYAN}[Stage 1]{RESET} Loading configuration...")

        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            ruler_config = config['articulated_ruler']
            print(f"  {GREEN}✓{RESET} Configuration loaded")
        except Exception as e:
            print(f"  {RED}✗ Failed to load configuration: {str(e)}{RESET}")
            return {
                "success": False,
                "message": f"Failed to load configuration: {str(e)}",
                "failed_stage": "load_config"
            }

        # Extract configuration
        red_grasp_prompt = ruler_config['red_grasp_prompt']
        blue_push_prompt = ruler_config['blue_push_prompt']
        arc_config = ruler_config['arc_motion']
        grasp_config = ruler_config['grasp']

        # ============================================================
        # STAGE 2: VLM Localization (Only 2 Points)
        # ============================================================
        print(f"\n{CYAN}[Stage 2]{RESET} VLM Localization {YELLOW}(2 points only){RESET}...")

        if not self.multi_view_vlm:
            print(f"  {RED}✗ Multi-view VLM not available{RESET}")
            return {
                "success": False,
                "message": "Multi-view VLM not available",
                "failed_stage": "vlm_init"
            }

        # Locate red grasp position
        print(f"\n  {BLUE}[2.1]{RESET} Locating red grasp position...")
        print(f"       Prompt: {YELLOW}{red_grasp_prompt}{RESET}")
        red_result = await self.locate_named_point(red_grasp_prompt, use_d455=True)
        if not red_result.get('success') or not red_result.get('found'):
            print(f"  {RED}✗ Could not locate red grasp position{RESET}")
            return {
                "success": False,
                "message": "Could not locate red grasp position",
                "failed_stage": "localization_red_grasp"
            }
        red_grasp_raw = red_result['position']
        print(f"       {GREEN}✓ Red grasp (raw):{RESET} {red_grasp_raw}")

        # Locate blue push position
        print(f"\n  {BLUE}[2.2]{RESET} Locating blue push position...")
        print(f"       Prompt: {YELLOW}{blue_push_prompt}{RESET}")
        blue_result = await self.locate_named_point(blue_push_prompt, use_d455=True)
        if not blue_result.get('success') or not blue_result.get('found'):
            print(f"  {RED}✗ Could not locate blue push position{RESET}")
            return {
                "success": False,
                "message": "Could not locate blue push position",
                "failed_stage": "localization_blue_push"
            }
        blue_push_raw = blue_result['position']
        print(f"       {GREEN}✓ Blue push (raw):{RESET} {blue_push_raw}")

        print(f"\n  {GREEN}✓ All localization complete{RESET}")

        # ============================================================
        # STAGE 3: Prepare Motion Coordinates
        # ============================================================
        print(f"\n{CYAN}[Stage 3]{RESET} Preparing motion coordinates...")

        grasp_z = grasp_config['grasp_z']
        push_z = arc_config['push_z']
        grasp_approach_z = grasp_z + grasp_config['approach_z_offset']
        push_approach_z = push_z + arc_config['approach_z_offset']

        # Red grasp position (use XY from VLM, Z from config)
        red_grasp_pos = [red_grasp_raw[0], red_grasp_raw[1], grasp_z]
        red_grasp_approach = [red_grasp_raw[0], red_grasp_raw[1], grasp_approach_z]

        # Blue push position (use XY from VLM, Z from config)
        blue_push_pos = [blue_push_raw[0], blue_push_raw[1], push_z]
        blue_push_approach = [blue_push_raw[0], blue_push_raw[1], push_approach_z]

        print(f"  {GREEN}✓ Red grasp:{RESET} {red_grasp_pos}")
        print(f"  {GREEN}✓ Blue push:{RESET} {blue_push_pos}")
        print(f"  Grasp Z: {grasp_z}m, Push Z: {push_z}m")

        # ============================================================
        # STAGE 4: Generate Arc Waypoints
        # ============================================================
        print(f"\n{CYAN}[Stage 4]{RESET} Generating arc waypoints...")

        # Arc parameters
        center_xy = [red_grasp_pos[0], red_grasp_pos[1]]
        start_xy = [blue_push_pos[0], blue_push_pos[1]]
        angle_degrees = arc_config['angle_degrees']
        direction = l_shape_blue_turn_direction  # Use parameter, not config
        num_waypoints = arc_config['num_waypoints']

        # RULER-SPECIFIC end-effector orientations
        # These are ONLY for articulated ruler task, not for general pick/place
        # Orientation: [roll, pitch, yaw] in radians
        # These values are from actual robot measurements for ruler manipulation
        ruler_orientation_left = [3.1040000238083394, 0.00014792449510964584, 0.8658561918693138]
        ruler_orientation_right = [-3.1368464846966204, -0.011995394822134225, -2.4167418325046994]

        # Select orientation based on which arm is used
        if fixed_arm == 'left':
            fixed_arm_orientation = ruler_orientation_left
            moving_arm_orientation = ruler_orientation_right
        else:
            fixed_arm_orientation = ruler_orientation_right
            moving_arm_orientation = ruler_orientation_left

        print(f"  Using ruler-specific orientations:")
        print(f"    {fixed_arm} arm (fixed): {fixed_arm_orientation}")
        print(f"    {moving_arm} arm (moving): {moving_arm_orientation}")

        # Generate arc (using moving arm orientation for all waypoints)
        arc_result = self.generate_arc_waypoints(
            center_xy, start_xy, angle_degrees, direction,
            num_waypoints, push_z, moving_arm_orientation
        )

        if not arc_result['success']:
            print(f"  {RED}✗ {arc_result['message']}{RESET}")
            return {
                "success": False,
                "message": arc_result['message'],
                "failed_stage": "arc_generation"
            }

        arc_waypoints = arc_result['waypoints']
        arc_radius = arc_result['radius']

        print(f"  {GREEN}✓ Arc generated{RESET}")
        print(f"    Center: {center_xy}")
        print(f"    Start: {start_xy}")
        print(f"    Radius: {arc_radius:.3f}m")
        print(f"    Angle: {angle_degrees}°")
        print(f"    Direction: {direction}")
        print(f"    Waypoints: {len(arc_waypoints)}")

        # Validate radius
        min_radius = arc_config['min_radius']
        max_radius = arc_config['max_radius']
        if arc_radius < min_radius:
            print(f"  {RED}✗ Arc radius too small: {arc_radius:.3f}m < {min_radius:.3f}m{RESET}")
            return {
                "success": False,
                "message": f"Arc radius too small: {arc_radius:.3f}m",
                "failed_stage": "arc_validation"
            }
        if arc_radius > max_radius:
            print(f"  {RED}✗ Arc radius too large: {arc_radius:.3f}m > {max_radius:.3f}m{RESET}")
            return {
                "success": False,
                "message": f"Arc radius too large: {arc_radius:.3f}m",
                "failed_stage": "arc_validation"
            }

        # ============================================================
        # STAGE 5: Validate All Poses
        # ============================================================
        print(f"\n{CYAN}[Stage 5]{RESET} Validating all poses...")

        # Check workspace for all poses
        poses_to_check = [
            ("red_grasp_approach", fixed_arm, red_grasp_approach + fixed_arm_orientation),
            ("red_grasp", fixed_arm, red_grasp_pos + fixed_arm_orientation),
            ("blue_push_approach", moving_arm, blue_push_approach + moving_arm_orientation),
            ("blue_push_start", moving_arm, blue_push_pos + moving_arm_orientation),
        ]

        # Check first, middle, and last arc waypoints
        for i in [0, len(arc_waypoints)//2, -1]:
            poses_to_check.append((f"arc_waypoint_{i}", moving_arm, arc_waypoints[i]))

        validation_failed = False
        failed_pose_name = None
        for pose_name, arm, pose in poses_to_check:
            # Workspace safety check
            is_safe, message = self.safety.check_workspace(arm, pose)
            if not is_safe:
                print(f"  {RED}✗ {pose_name} outside workspace: {message}{RESET}")
                validation_failed = True
                failed_pose_name = pose_name
                break

        if validation_failed:
            return {
                "success": False,
                "message": f"Pose validation failed at {failed_pose_name}",
                "failed_stage": "pose_validation",
                "failed_pose": failed_pose_name
            }

        print(f"  {GREEN}✓ All poses validated (workspace check){RESET}")

        # ============================================================
        # STAGE 6: Dry Run Exit
        # ============================================================
        if dry_run:
            print(f"\n{CYAN}[Stage 6]{RESET} {YELLOW}Dry run - returning plan{RESET}")
            print(f"{CYAN}{BOLD}{'='*70}{RESET}")
            print(f"{GREEN}✓ DRY RUN COMPLETE{RESET}")
            print(f"{CYAN}{BOLD}{'='*70}{RESET}\n")

            return {
                "success": True,
                "message": "Dry run complete",
                "dry_run": True,
                "red_grasp_position": red_grasp_pos,
                "blue_push_position": blue_push_pos,
                "arc_center": center_xy,
                "arc_radius": arc_radius,
                "arc_angle_degrees": angle_degrees,
                "arc_direction": direction,
                "arc_waypoints": arc_waypoints,
                "num_waypoints": len(arc_waypoints)
            }

        # ============================================================
        # STAGE 7-12: Robot Execution
        # ============================================================
        print(f"\n{CYAN}[Stage 7]{RESET} {BOLD}Starting robot execution{RESET}...")
        print(f"  {YELLOW}⚠ Robot will now move{RESET}")

        speed = arc_config['push_speed_scale']

        # Stage 7: Move fixed arm to red grasp approach
        print(f"\n{CYAN}[Stage 8]{RESET} Moving {fixed_arm} arm to red grasp approach...")
        success = self.driver.move_to_pose(fixed_arm, red_grasp_approach + fixed_arm_orientation, speed=0.2)
        if not success:
            print(f"  {RED}✗ Failed to move to approach{RESET}")
            return {
                "success": False,
                "message": "Failed to move fixed arm to approach",
                "failed_stage": "fixed_arm_approach"
            }
        print(f"  {GREEN}✓ At approach position{RESET}")

        # Stage 8: Open fixed arm gripper
        print(f"\n{CYAN}[Stage 9]{RESET} Opening {fixed_arm} gripper...")
        self.driver.gripper_command(fixed_arm, 'open')
        time.sleep(0.5)

        # Stage 9: Move down to grasp
        print(f"\n{CYAN}[Stage 10]{RESET} Moving down to grasp red segment...")
        success = self.driver.move_to_pose(fixed_arm, red_grasp_pos + fixed_arm_orientation, speed=0.1)
        if not success:
            print(f"  {RED}✗ Failed to move to grasp{RESET}")
            return {
                "success": False,
                "message": "Failed to move to grasp position",
                "failed_stage": "fixed_arm_grasp"
            }

        # Stage 10: Close gripper to hold red segment
        print(f"\n{CYAN}[Stage 11]{RESET} Closing {fixed_arm} gripper to hold red segment...")
        self.driver.gripper_command(fixed_arm, 'close', force=grasp_config['grasp_force'])
        time.sleep(1.0)
        print(f"  {GREEN}✓ Red segment grasped and held{RESET}")

        # Stage 11: Open moving arm gripper (MUST stay open for pushing)
        print(f"\n{CYAN}[Stage 12]{RESET} Opening {moving_arm} gripper (for pushing)...")
        self.driver.gripper_command(moving_arm, 'open')
        time.sleep(0.5)
        print(f"  {GREEN}✓ {moving_arm} gripper open{RESET}")

        # Stage 12: Move moving arm to push approach
        print(f"\n{CYAN}[Stage 13]{RESET} Moving {moving_arm} arm to push approach...")
        success = self.driver.move_to_pose(moving_arm, blue_push_approach + moving_arm_orientation, speed=0.2)
        if not success:
            print(f"  {RED}✗ Failed to move to push approach{RESET}")
            return {
                "success": False,
                "message": "Failed to move to push approach",
                "failed_stage": "moving_arm_approach"
            }

        # Stage 13: Move down to push start
        print(f"\n{CYAN}[Stage 14]{RESET} Moving down to push start position...")
        success = self.driver.move_to_pose(moving_arm, blue_push_pos + moving_arm_orientation, speed=0.1)
        if not success:
            print(f"  {RED}✗ Failed to move to push start{RESET}")
            return {
                "success": False,
                "message": "Failed to move to push start",
                "failed_stage": "moving_arm_push_start"
            }
        print(f"  {GREEN}✓ At push start position{RESET}")

        # Stage 14: Execute arc pushing motion
        print(f"\n{CYAN}[Stage 15]{RESET} Executing arc pushing motion...")
        print(f"  Pushing along {len(arc_waypoints)} waypoints at speed {speed}")

        for i, waypoint in enumerate(arc_waypoints):
            if i % 5 == 0:  # Print progress every 5 waypoints
                print(f"  Waypoint {i+1}/{len(arc_waypoints)}")

            success = self.driver.move_to_pose(moving_arm, waypoint, speed=speed)
            if not success:
                print(f"  {RED}✗ Failed at waypoint {i+1}{RESET}")
                return {
                    "success": False,
                    "message": f"Failed at arc waypoint {i+1}",
                    "failed_stage": "arc_execution",
                    "failed_waypoint": i
                }

            time.sleep(0.05)  # Small pause between waypoints

        print(f"  {GREEN}✓ Arc pushing complete{RESET}")

        # Stage 15: Retreat moving arm
        print(f"\n{CYAN}[Stage 16]{RESET} Retreating {moving_arm} arm...")
        final_pos = arc_waypoints[-1]
        retreat_pos = [final_pos[0], final_pos[1], push_approach_z] + moving_arm_orientation
        success = self.driver.move_to_pose(moving_arm, retreat_pos, speed=0.2)
        if not success:
            print(f"  {YELLOW}⚠ Failed to retreat (non-critical){RESET}")

        # Stage 16: Release fixed arm (optional)
        print(f"\n{CYAN}[Stage 17]{RESET} Releasing {fixed_arm} gripper...")
        self.driver.gripper_command(fixed_arm, 'open')
        time.sleep(0.5)

        # Done
        print(f"\n{CYAN}{BOLD}{'='*70}{RESET}")
        print(f"{GREEN}{BOLD}✓ TASK COMPLETE{RESET}")
        print(f"{CYAN}{BOLD}{'='*70}{RESET}")
        print(f"  Arc pushing executed successfully")
        print(f"  {fixed_arm} arm held red segment")
        print(f"  {moving_arm} arm pushed blue segment along {angle_degrees}° arc")
        print(f"{CYAN}{BOLD}{'='*70}{RESET}\n")

        return {
            "success": True,
            "message": "Arc pushing task completed successfully",
            "dry_run": False,
            "red_grasp_position": red_grasp_pos,
            "blue_push_position": blue_push_pos,
            "arc_center": center_xy,
            "arc_radius": arc_radius,
            "arc_angle_degrees": angle_degrees,
            "arc_direction": direction,
            "arc_waypoints": arc_waypoints,
            "num_waypoints": len(arc_waypoints)
        }

    async def flatten_articulated_ruler(
        self,
        config_path: str = "config/flatten_ruler_task.yaml",
        dry_run: bool = False
    ) -> Dict:
        """Flatten an S-shaped articulated ruler by pulling both endpoints apart.

        This task uses dual-arm coordination to:
        1. Locate red endpoint (purple tape) and blue endpoint (green tape) via VLM
        2. Grasp both endpoints with left and right arms
        3. Pull the endpoints apart synchronously to straighten the ruler
        4. Interpolate both position and orientation during pulling

        Args:
            config_path: Path to flatten ruler task configuration
            dry_run: If True, only plan without executing

        Returns:
            Dict with task result:
            {
                'success': bool,
                'message': str,
                'red_endpoint': [x, y, z],
                'blue_endpoint': [x, y, z],
                'initial_separation': float,
                'final_separation': float,
                'num_waypoints': int,
                'left_arm_trajectory': List[pose],
                'right_arm_trajectory': List[pose]
            }
        """
        import yaml

        # ANSI color codes
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        BOLD = '\033[1m'
        RESET = '\033[0m'

        print(f"\n{CYAN}{BOLD}{'='*70}{RESET}")
        print(f"{CYAN}{BOLD}FLATTEN ARTICULATED RULER - DUAL-ARM PULLING{RESET}")
        print(f"{CYAN}{BOLD}{'='*70}{RESET}")
        print(f"Config: {config_path}")
        print(f"Dry run: {dry_run}")
        print(f"{CYAN}{BOLD}{'='*70}{RESET}\n")

        # ============================================================
        # STAGE 1: Load Configuration
        # ============================================================
        print(f"{CYAN}[Stage 1]{RESET} Loading configuration...")

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            task_config = config['flatten_ruler']
            print(f"  {GREEN}✓ Configuration loaded{RESET}")
        except Exception as e:
            print(f"  {RED}✗ Failed to load config: {e}{RESET}")
            return {
                "success": False,
                "message": f"Config load failed: {e}",
                "failed_stage": "load_config"
            }

        # Extract configuration parameters
        red_prompt = task_config['red_endpoint_prompt']
        blue_prompt = task_config['blue_endpoint_prompt']

        grasp_config = task_config['grasp']
        grasp_z = grasp_config['grasp_z']
        approach_z_offset = grasp_config['approach_z_offset']
        grasp_force = grasp_config['grasp_force']

        # Get arm-specific base orientations
        base_orientation = grasp_config['base_orientation']
        left_base_roll = base_orientation['left']['roll']
        left_base_pitch = base_orientation['left']['pitch']
        left_base_yaw = base_orientation['left']['yaw']  # Base yaw offset (creates 45° tilt)
        right_base_roll = base_orientation['right']['roll']
        right_base_pitch = base_orientation['right']['pitch']
        right_base_yaw = base_orientation['right']['yaw']  # Base yaw offset (creates 45° tilt)

        # Get target orientations (when ruler is straightened)
        target_orientation = grasp_config['target_orientation']
        left_target_roll = target_orientation['left']['roll']
        left_target_pitch = target_orientation['left']['pitch']
        left_target_yaw = target_orientation['left']['yaw']
        right_target_roll = target_orientation['right']['roll']
        right_target_pitch = target_orientation['right']['pitch']
        right_target_yaw = target_orientation['right']['yaw']

        pulling_config = task_config['pulling']
        pull_distance = pulling_config['pull_distance']
        num_waypoints = pulling_config['num_waypoints']
        speed_scale = pulling_config['speed_scale']
        min_separation = pulling_config['min_separation']
        max_separation = pulling_config['max_separation']
        interpolate_yaw = pulling_config['interpolate_yaw']
        max_yaw_change = pulling_config.get('max_yaw_change', 0.785398)  # Default 45°

        # ============================================================
        # STAGE 2: VLM Localization (2 endpoints)
        # ============================================================
        print(f"\n{CYAN}[Stage 2]{RESET} VLM Localization (2 endpoints)...")

        if not self.multi_view_vlm:
            print(f"  {RED}✗ Multi-view VLM not available{RESET}")
            return {
                "success": False,
                "message": "Multi-view VLM not initialized",
                "failed_stage": "vlm_init"
            }

        # Locate red endpoint
        print(f"  [2.1] Locating red endpoint (purple tape)...")
        red_result = await self.multi_view_vlm.locate_object_multiview(
            red_prompt,
            arm="right",
            use_wrist_refinement=False  # Disable wrist camera refinement
        )

        if not red_result or not red_result.get('found'):
            print(f"       {RED}✗ Red endpoint not found{RESET}")
            return {
                "success": False,
                "message": "Red endpoint localization failed",
                "failed_stage": "localization_red_endpoint"
            }

        red_endpoint_raw = red_result['position']
        print(f"       {GREEN}✓ Red endpoint (raw): {red_endpoint_raw}{RESET}")

        # Locate blue endpoint
        print(f"  [2.2] Locating blue endpoint (green tape)...")
        blue_result = await self.multi_view_vlm.locate_object_multiview(
            blue_prompt,
            arm="right",
            use_wrist_refinement=False  # Disable wrist camera refinement
        )

        if not blue_result or not blue_result.get('found'):
            print(f"       {RED}✗ Blue endpoint not found{RESET}")
            return {
                "success": False,
                "message": "Blue endpoint localization failed",
                "failed_stage": "localization_blue_endpoint"
            }

        blue_endpoint_raw = blue_result['position']
        print(f"       {GREEN}✓ Blue endpoint (raw): {blue_endpoint_raw}{RESET}")
        print(f"  {GREEN}✓ All localization complete{RESET}")

        # ============================================================
        # STAGE 3: Prepare Grasp Coordinates
        # ============================================================
        print(f"\n{CYAN}[Stage 3]{RESET} Preparing grasp coordinates...")

        # Use VLM XY, fixed Z from config
        red_endpoint = [red_endpoint_raw[0], red_endpoint_raw[1], grasp_z]
        blue_endpoint = [blue_endpoint_raw[0], blue_endpoint_raw[1], grasp_z]

        red_approach = [red_endpoint[0], red_endpoint[1], grasp_z + approach_z_offset]
        blue_approach = [blue_endpoint[0], blue_endpoint[1], grasp_z + approach_z_offset]

        print(f"  {GREEN}✓ Red endpoint: {red_endpoint}{RESET}")
        print(f"  {GREEN}✓ Blue endpoint: {blue_endpoint}{RESET}")
        print(f"  Grasp Z: {grasp_z}m, Approach offset: {approach_z_offset}m")

        # Calculate initial separation
        initial_separation = np.linalg.norm(
            np.array(red_endpoint[:2]) - np.array(blue_endpoint[:2])
        )
        print(f"  Initial separation: {initial_separation:.3f}m")

        # Validate separation
        if initial_separation < min_separation:
            print(f"  {RED}✗ Endpoints too close: {initial_separation:.3f}m < {min_separation}m{RESET}")
            return {
                "success": False,
                "message": f"Endpoints too close: {initial_separation:.3f}m",
                "failed_stage": "separation_validation"
            }

        # ============================================================
        # STAGE 4: Calculate Initial Orientations
        # ============================================================
        print(f"\n{CYAN}[Stage 4]{RESET} Calculating initial grasp orientations...")

        # Use the measured yaw values directly (they already include the 45° tilt)
        # These are the actual orientations measured when the robot was in the correct pose
        left_initial_yaw = left_base_yaw
        right_initial_yaw = right_base_yaw

        # Use arm-specific roll and pitch from config
        left_initial_orientation = [left_base_roll, left_base_pitch, left_initial_yaw]
        right_initial_orientation = [right_base_roll, right_base_pitch, right_initial_yaw]

        print(f"  Using measured orientations (with 45° tilt):")
        print(f"  Left arm initial orientation (RPY): {left_initial_orientation}")
        print(f"    Roll: {np.rad2deg(left_base_roll):.2f}°, Pitch: {np.rad2deg(left_base_pitch):.2f}°, Yaw: {np.rad2deg(left_initial_yaw):.2f}°")
        print(f"  Right arm initial orientation (RPY): {right_initial_orientation}")
        print(f"    Roll: {np.rad2deg(right_base_roll):.2f}°, Pitch: {np.rad2deg(right_base_pitch):.2f}°, Yaw: {np.rad2deg(right_initial_yaw):.2f}°")
        print(f"  {GREEN}✓ Initial orientations set from config{RESET}")

        # ============================================================
        # STAGE 5: Generate Pulling Trajectories
        # ============================================================
        print(f"\n{CYAN}[Stage 5]{RESET} Generating pulling trajectories...")

        # Calculate final positions (pull apart along the line connecting them)
        midpoint = (np.array(red_endpoint[:2]) + np.array(blue_endpoint[:2])) / 2.0

        # Calculate vector from red to blue (for pulling direction)
        pull_vector = np.array(blue_endpoint[:2]) - np.array(red_endpoint[:2])

        # Pull direction unit vectors
        pull_direction_left = -pull_vector / np.linalg.norm(pull_vector)  # Red pulls away from blue
        pull_direction_right = pull_vector / np.linalg.norm(pull_vector)  # Blue pulls away from red

        # Final positions
        red_final_xy = midpoint + pull_direction_left * (initial_separation / 2.0 + pull_distance / 2.0)
        blue_final_xy = midpoint + pull_direction_right * (initial_separation / 2.0 + pull_distance / 2.0)

        red_final = [red_final_xy[0], red_final_xy[1], grasp_z]
        blue_final = [blue_final_xy[0], blue_final_xy[1], grasp_z]

        final_separation = np.linalg.norm(red_final_xy - blue_final_xy)

        print(f"  Red final position: {red_final}")
        print(f"  Blue final position: {blue_final}")
        print(f"  Final separation: {final_separation:.3f}m")

        # Validate final separation
        if final_separation > max_separation:
            print(f"  {RED}✗ Final separation too large: {final_separation:.3f}m > {max_separation}m{RESET}")
            return {
                "success": False,
                "message": f"Final separation too large: {final_separation:.3f}m",
                "failed_stage": "final_separation_validation"
            }

        # Calculate final orientations (straightened ruler)
        # Use target orientations from config (grippers parallel to x-axis)
        left_final_yaw = left_target_yaw
        right_final_yaw = right_target_yaw

        # SAFETY CHECK: Verify yaw change is within safe limits
        left_yaw_change = abs(left_final_yaw - left_base_yaw)
        right_yaw_change = abs(right_final_yaw - right_base_yaw)

        # Handle angle wrapping (e.g., -170° to +170° should be 20°, not 340°)
        if left_yaw_change > np.pi:
            left_yaw_change = 2 * np.pi - left_yaw_change
        if right_yaw_change > np.pi:
            right_yaw_change = 2 * np.pi - right_yaw_change

        print(f"  Final separation: {final_separation:.3f}m")
        print(f"  Target orientations (grippers parallel to x-axis):")
        print(f"    Left yaw change: {np.rad2deg(left_yaw_change):.1f}° (limit: {np.rad2deg(max_yaw_change):.1f}°)")
        print(f"    Right yaw change: {np.rad2deg(right_yaw_change):.1f}° (limit: {np.rad2deg(max_yaw_change):.1f}°)")

        # Check safety constraint
        if left_yaw_change > max_yaw_change:
            print(f"  {RED}✗ Left arm yaw change {np.rad2deg(left_yaw_change):.1f}° exceeds limit {np.rad2deg(max_yaw_change):.1f}°{RESET}")
            return {
                "success": False,
                "message": f"Left arm yaw change {np.rad2deg(left_yaw_change):.1f}° exceeds safety limit {np.rad2deg(max_yaw_change):.1f}°",
                "failed_stage": "yaw_safety_check"
            }

        if right_yaw_change > max_yaw_change:
            print(f"  {RED}✗ Right arm yaw change {np.rad2deg(right_yaw_change):.1f}° exceeds limit {np.rad2deg(max_yaw_change):.1f}°{RESET}")
            return {
                "success": False,
                "message": f"Right arm yaw change {np.rad2deg(right_yaw_change):.1f}° exceeds safety limit {np.rad2deg(max_yaw_change):.1f}°",
                "failed_stage": "yaw_safety_check"
            }

        print(f"  {GREEN}✓ Yaw changes within safety limits{RESET}")

        # Keep the same roll/pitch as initial
        left_final_orientation = [left_target_roll, left_target_pitch, left_final_yaw]
        right_final_orientation = [right_target_roll, right_target_pitch, right_final_yaw]

        print(f"  Left arm final orientation (RPY):")
        print(f"    Roll: {np.rad2deg(left_target_roll):.2f}°, Pitch: {np.rad2deg(left_target_pitch):.2f}°, Yaw: {np.rad2deg(left_final_yaw):.2f}°")
        print(f"  Right arm final orientation (RPY):")
        print(f"    Roll: {np.rad2deg(right_target_roll):.2f}°, Pitch: {np.rad2deg(right_target_pitch):.2f}°, Yaw: {np.rad2deg(right_final_yaw):.2f}°")

        # Generate waypoints with position and orientation interpolation
        left_trajectory = []
        right_trajectory = []

        for i in range(num_waypoints + 1):
            ratio = i / num_waypoints

            # Interpolate positions
            left_pos = [
                red_endpoint[0] + ratio * (red_final[0] - red_endpoint[0]),
                red_endpoint[1] + ratio * (red_final[1] - red_endpoint[1]),
                grasp_z
            ]
            right_pos = [
                blue_endpoint[0] + ratio * (blue_final[0] - blue_endpoint[0]),
                blue_endpoint[1] + ratio * (blue_final[1] - blue_endpoint[1]),
                grasp_z
            ]

            # Interpolate orientations
            if interpolate_yaw:
                # Interpolate yaw angle
                left_yaw = left_initial_yaw + ratio * (left_final_yaw - left_initial_yaw)
                right_yaw = right_initial_yaw + ratio * (right_final_yaw - right_initial_yaw)
            else:
                # Keep initial yaw
                left_yaw = left_initial_yaw
                right_yaw = right_initial_yaw

            # Use arm-specific roll and pitch
            left_orientation = [left_base_roll, left_base_pitch, left_yaw]
            right_orientation = [right_base_roll, right_base_pitch, right_yaw]

            left_trajectory.append(left_pos + left_orientation)
            right_trajectory.append(right_pos + right_orientation)

        print(f"  {GREEN}✓ Trajectories generated: {num_waypoints + 1} waypoints{RESET}")

        # ============================================================
        # STAGE 6: Validate All Poses
        # ============================================================
        print(f"\n{CYAN}[Stage 6]{RESET} Validating all poses...")

        poses_to_check = [
            ("left_red_approach", "left", red_approach + left_initial_orientation),
            ("left_red_grasp", "left", red_endpoint + left_initial_orientation),
            ("right_blue_approach", "right", blue_approach + right_initial_orientation),
            ("right_blue_grasp", "right", blue_endpoint + right_initial_orientation),
        ]

        # Check first, middle, and last waypoints
        for i in [0, len(left_trajectory)//2, -1]:
            poses_to_check.append((f"left_waypoint_{i}", "left", left_trajectory[i]))
            poses_to_check.append((f"right_waypoint_{i}", "right", right_trajectory[i]))

        validation_failed = False
        failed_pose_name = None

        for pose_name, arm, pose in poses_to_check:
            # Workspace safety check
            is_safe, message = self.safety.check_workspace(arm, pose)
            if not is_safe:
                print(f"  {RED}✗ {pose_name} outside workspace: {message}{RESET}")
                validation_failed = True
                failed_pose_name = pose_name
                break

        if validation_failed:
            return {
                "success": False,
                "message": f"Pose validation failed at {failed_pose_name}",
                "failed_stage": "pose_validation",
                "failed_pose": failed_pose_name
            }

        print(f"  {GREEN}✓ All poses validated (workspace check){RESET}")

        # ============================================================
        # STAGE 7: Dry Run Exit
        # ============================================================
        if dry_run:
            print(f"\n{CYAN}[Stage 7]{RESET} {YELLOW}Dry run - returning plan{RESET}")
            print(f"{CYAN}{BOLD}{'='*70}{RESET}")
            print(f"{GREEN}✓ DRY RUN COMPLETE{RESET}")
            print(f"{CYAN}{BOLD}{'='*70}{RESET}\n")

            return {
                "success": True,
                "message": "Dry run complete",
                "dry_run": True,
                "red_endpoint": red_endpoint,
                "blue_endpoint": blue_endpoint,
                "initial_separation": initial_separation,
                "final_separation": final_separation,
                "num_waypoints": len(left_trajectory),
                "left_arm_trajectory": left_trajectory,
                "right_arm_trajectory": right_trajectory
            }

        # ============================================================
        # STAGE 8-15: Robot Execution
        # ============================================================
        print(f"\n{CYAN}[Stage 8]{RESET} {BOLD}Starting robot execution{RESET}...")
        print(f"  {YELLOW}⚠ Robot will now move{RESET}")

        # Stage 8: Move both arms to approach positions
        print(f"\n{CYAN}[Stage 9]{RESET} Moving both arms to approach positions...")

        left_success = self.driver.move_to_pose("left", red_approach + left_initial_orientation, speed=0.2)
        right_success = self.driver.move_to_pose("right", blue_approach + right_initial_orientation, speed=0.2)

        if not left_success or not right_success:
            print(f"  {RED}✗ Failed to move to approach positions{RESET}")
            return {
                "success": False,
                "message": "Failed to move to approach positions",
                "failed_stage": "approach"
            }
        print(f"  {GREEN}✓ Both arms at approach positions{RESET}")

        # Stage 9: Open both grippers
        print(f"\n{CYAN}[Stage 10]{RESET} Opening both grippers...")
        self.driver.gripper_command("left", 'open')
        self.driver.gripper_command("right", 'open')
        time.sleep(0.5)

        # Stage 10: Move down to grasp positions
        print(f"\n{CYAN}[Stage 11]{RESET} Moving down to grasp positions...")

        left_success = self.driver.move_to_pose("left", red_endpoint + left_initial_orientation, speed=0.1)
        right_success = self.driver.move_to_pose("right", blue_endpoint + right_initial_orientation, speed=0.1)

        if not left_success or not right_success:
            print(f"  {RED}✗ Failed to move to grasp positions{RESET}")
            return {
                "success": False,
                "message": "Failed to move to grasp positions",
                "failed_stage": "grasp_approach"
            }
        print(f"  {GREEN}✓ Both arms at grasp positions{RESET}")

        # Stage 11: Close both grippers
        print(f"\n{CYAN}[Stage 12]{RESET} Closing both grippers...")
        self.driver.gripper_command("left", 'close', force=grasp_force)
        self.driver.gripper_command("right", 'close', force=grasp_force)
        time.sleep(1.0)
        print(f"  {GREEN}✓ Both endpoints grasped{RESET}")

        # Stage 12: Execute synchronized pulling motion
        print(f"\n{CYAN}[Stage 13]{RESET} Executing synchronized pulling motion...")
        print(f"  Pulling along {len(left_trajectory)} waypoints at speed {speed_scale}")

        for i, (left_wp, right_wp) in enumerate(zip(left_trajectory, right_trajectory)):
            if i % 5 == 0:  # Print progress every 5 waypoints
                print(f"  Waypoint {i+1}/{len(left_trajectory)}")
                print(f"    Left: pos={left_wp[:3]}, yaw={np.rad2deg(left_wp[5]):.1f}°")
                print(f"    Right: pos={right_wp[:3]}, yaw={np.rad2deg(right_wp[5]):.1f}°")

            # Move both arms synchronously
            left_success = self.driver.move_to_pose("left", left_wp, speed=speed_scale)
            right_success = self.driver.move_to_pose("right", right_wp, speed=speed_scale)

            if not left_success or not right_success:
                print(f"  {RED}✗ Failed at waypoint {i+1}{RESET}")
                return {
                    "success": False,
                    "message": f"Failed at waypoint {i+1}",
                    "failed_stage": "pulling_execution",
                    "failed_waypoint": i
                }

            time.sleep(0.05)  # Small pause between waypoints

        print(f"  {GREEN}✓ Pulling motion complete{RESET}")

        # Stage 13: Release both grippers
        print(f"\n{CYAN}[Stage 14]{RESET} Releasing both grippers...")
        self.driver.gripper_command("left", 'open')
        self.driver.gripper_command("right", 'open')
        time.sleep(0.5)

        # Stage 14: Retreat both arms
        print(f"\n{CYAN}[Stage 15]{RESET} Retreating both arms...")
        left_retreat = [red_final[0], red_final[1], grasp_z + approach_z_offset] + left_final_orientation
        right_retreat = [blue_final[0], blue_final[1], grasp_z + approach_z_offset] + right_final_orientation

        self.driver.move_to_pose("left", left_retreat, speed=0.2)
        self.driver.move_to_pose("right", right_retreat, speed=0.2)

        # Done
        print(f"\n{CYAN}{BOLD}{'='*70}{RESET}")
        print(f"{GREEN}{BOLD}✓ TASK COMPLETE{RESET}")
        print(f"{CYAN}{BOLD}{'='*70}{RESET}")
        print(f"  Ruler flattened successfully")
        print(f"  Initial separation: {initial_separation:.3f}m")
        print(f"  Final separation: {final_separation:.3f}m")
        print(f"  Pull distance: {final_separation - initial_separation:.3f}m")
        print(f"{CYAN}{BOLD}{'='*70}{RESET}\n")

        return {
            "success": True,
            "message": "Ruler flattening task completed successfully",
            "dry_run": False,
            "red_endpoint": red_endpoint,
            "blue_endpoint": blue_endpoint,
            "initial_separation": initial_separation,
            "final_separation": final_separation,
            "pull_distance": final_separation - initial_separation,
            "num_waypoints": len(left_trajectory),
            "left_arm_trajectory": left_trajectory,
            "right_arm_trajectory": right_trajectory
        }
