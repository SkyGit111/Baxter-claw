"""Multi-view VLM coordinator for improved object localization.

Combines multiple camera views (D455, Baxter head, Baxter wrist) with:
- Hand-eye calibration for accurate coordinate transformation
- Image preprocessing for optimal VLM analysis
- Stage-specific optimized prompts
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Tuple
import cv2

from .camera_transforms import CameraTransforms
from .image_processor import ImageProcessor
from .vlm_prompts import VLMPrompts


class MultiViewVLMCoordinator:
    """Coordinates multiple camera views for VLM-based object localization.

    Complete pipeline:
    1. Phase 1 (Global): D455 + head camera for initial detection
       - Retract arm to avoid occlusion
       - Process images (crop, enhance, correct)
       - Use optimized prompts for each camera
       - Apply coordinate transformations
       - Cross-validate between views

    2. Phase 2 (Refinement): D455 + wrist camera for precise localization
       - Switch to wrist camera
       - Move to estimated location
       - Capture close-up with detailed prompt
       - Fuse all views for final estimate
    """

    def __init__(self, driver, vlm_client, safety_validator):
        """Initialize multi-view coordinator.

        Args:
            driver: BaxterDriver instance
            vlm_client: VLMClient instance
            safety_validator: SafetyValidator instance
        """
        self.driver = driver
        self.vlm = vlm_client
        self.safety = safety_validator

        # Initialize coordinate transforms
        print("[MultiView] Initializing coordinate transforms...")
        self.transforms = CameraTransforms()

        # Initialize image processor
        print("[MultiView] Initializing image processor...")
        self.image_processor = ImageProcessor()

        # Initialize VLM prompts
        workspace_bounds = self.safety.get_workspace_bounds()
        print("[MultiView] Initializing VLM prompts...")
        self.prompts = VLMPrompts(workspace_bounds)

        # Camera state tracking
        self._head_camera_active = False
        self._wrist_camera_active = False

        # Debug mode
        self.debug = True  # Save debug images

    async def locate_object_multiview(
        self,
        object_name: str,
        arm: str = "right",
        use_wrist_refinement: bool = True
    ) -> Optional[Dict]:
        """Locate object using complete multi-view approach.

        Args:
            object_name: Name of object to locate
            arm: Which arm to use for wrist camera ("left" or "right")
            use_wrist_refinement: Whether to use wrist camera for refinement

        Returns:
            Dict with object location and confidence, or None if not found
        """
        print(f"\n{'='*60}")
        print(f"[MultiView] Locating '{object_name}' using multi-view approach")
        print(f"{'='*60}")

        # Phase 1: Global localization
        print("\n=== Phase 1: Global Localization ===")
        global_result = await self._phase1_global_localization(object_name, arm)

        if not global_result or not global_result.get('found'):
            print(f"[MultiView] ✗ Object '{object_name}' not found in global view")
            return global_result

        print(f"[MultiView] ✓ Initial detection:")
        print(f"  Position: {global_result['position']}")
        print(f"  Confidence: {global_result['confidence']}%")

        # Phase 2: Wrist refinement (optional)
        if use_wrist_refinement:
            print("\n=== Phase 2: Wrist Camera Refinement ===")
            refined_result = await self._phase2_wrist_refinement(
                object_name, arm, global_result
            )

            if refined_result:
                print(f"[MultiView] ✓ Refined position:")
                print(f"  Position: {refined_result['position']}")
                print(f"  Confidence: {refined_result['confidence']}%")
                return refined_result
            else:
                print("[MultiView] ⚠ Refinement failed, using global result")
                return global_result

        return global_result

    async def _phase1_global_localization(
        self,
        object_name: str,
        arm: str
    ) -> Optional[Dict]:
        """Phase 1: Use D455 + head camera for initial detection."""

        # Step 1: Retract arm to avoid occlusion
        print("[Phase1] Step 1: Retracting arm to avoid occlusion...")
        success = await self._retract_arm(arm)
        if not success:
            print("[Phase1] ⚠ Warning: Failed to retract arm, continuing anyway...")

        # Wait for motion to settle
        await asyncio.sleep(1.0)

        # Step 2: Capture and process D455 images
        print("[Phase1] Step 2: Capturing from D455 depth camera...")
        d455_result = await self._capture_and_analyze_d455(object_name, "phase1")

        # Step 3: Capture and process head camera
        print("[Phase1] Step 3: Capturing from head camera...")
        head_result = await self._capture_and_analyze_head(object_name)

        # Step 4: Cross-validate and fuse results
        print("[Phase1] Step 4: Cross-validating results...")
        fused_result = self._fuse_phase1_results(
            object_name, d455_result, head_result
        )

        return fused_result

    async def _capture_and_analyze_d455(
        self,
        object_name: str,
        phase: str
    ) -> Optional[Dict]:
        """Capture and analyze D455 camera image."""

        if not self.driver.has_depth_camera():
            print("[D455] ✗ Depth camera not available")
            return None

        # Capture RGB-D
        rgb_image, depth_image = self.driver.capture_rgbd()
        if rgb_image is None or depth_image is None:
            print("[D455] ✗ Failed to capture images")
            return None

        print(f"[D455] ✓ Captured: RGB {rgb_image.shape}, Depth {depth_image.shape}")

        # Process images
        processed_rgb, processed_depth, metadata = self.image_processor.process_d455_image(
            rgb_image, depth_image
        )

        # Save debug images
        if self.debug:
            self.image_processor.save_debug_images(
                f"debug_d455_{phase}",
                raw_image=rgb_image,
                processed_image=processed_rgb,
                depth_image=processed_depth
            )

        # Encode to JPEG
        jpeg_bytes = self.image_processor.encode_image_to_jpeg(processed_rgb)

        # Get optimized prompt
        prompt = self.prompts.get_phase1_d455_prompt(object_name)

        # Call VLM with depth enhancement and custom prompt
        print("[D455] Analyzing with VLM (depth-enhanced)...")
        depth_camera = self.driver.get_depth_camera_driver()
        workspace_bounds = self.safety.get_workspace_bounds()

        result = await self.vlm.locate_object_with_depth(
            jpeg_bytes,
            processed_depth,
            object_name,
            depth_camera,
            workspace_bounds,
            custom_prompt=prompt
        )

        if result and result.get('found'):
            # Apply coordinate transformation
            position_camera = np.array(result['position'])
            position_base = self.transforms.transform_d455_to_base(position_camera)

            if position_base is not None:
                result['position'] = position_base.tolist()
                result['position_camera_frame'] = position_camera.tolist()
                result['coordinate_transformed'] = True
                print(f"[D455] ✓ Coordinate transform applied")
                print(f"  Camera frame: {position_camera}")
                print(f"  Base frame: {position_base}")
            else:
                print(f"[D455] ⚠ Coordinate transform not available")
                result['coordinate_transformed'] = False

        return result

    async def _capture_and_analyze_head(
        self,
        object_name: str
    ) -> Optional[Dict]:
        """Capture and analyze head camera image."""

        # Enable head camera
        self._enable_head_camera()

        # Capture image
        head_image_bytes = self.driver.capture_image('head')
        if not head_image_bytes:
            print("[Head] ✗ Failed to capture image")
            return None

        print(f"[Head] ✓ Captured: {len(head_image_bytes)} bytes")

        # Decode image
        nparr = np.frombuffer(head_image_bytes, np.uint8)
        head_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Process image (crop, enhance, perspective correction)
        processed_head, metadata = self.image_processor.process_head_camera_image(head_image)

        # Save debug images
        if self.debug:
            self.image_processor.save_debug_images(
                "debug_head_phase1",
                raw_image=head_image,
                processed_image=processed_head
            )

        # Encode processed image
        jpeg_bytes = self.image_processor.encode_image_to_jpeg(processed_head)

        # Get optimized prompt
        prompt = self.prompts.get_phase1_head_camera_prompt(object_name)

        # Call VLM with custom prompt
        print("[Head] Analyzing with VLM (validation)...")
        result = await self.vlm.locate_object(
            jpeg_bytes,
            object_name,
            self.safety.get_workspace_bounds(),
            custom_prompt=prompt
        )

        # Note: Head camera coordinate transformation is approximate
        # We mainly use it for validation, not precise positioning
        if result and result.get('found'):
            result['validation_view'] = True
            print(f"[Head] ✓ Object detected (validation)")

        return result

    def _fuse_phase1_results(
        self,
        object_name: str,
        d455_result: Optional[Dict],
        head_result: Optional[Dict]
    ) -> Optional[Dict]:
        """Fuse Phase 1 results from D455 and head camera."""

        print("[Fusion] Fusing Phase 1 results...")

        # Primary: D455 with depth
        if not d455_result or not d455_result.get('found'):
            print("[Fusion] ✗ D455 did not detect object")
            return d455_result

        # If no head camera result, return D455 only
        if not head_result or not head_result.get('found'):
            print("[Fusion] ⚠ Head camera validation not available")
            d455_result['multi_view_validated'] = False
            return d455_result

        # Compare positions
        d455_pos = np.array(d455_result['position'])
        head_pos = np.array(head_result['position'])
        pos_diff = np.linalg.norm(d455_pos - head_pos)

        print(f"[Fusion] Position difference: {pos_diff:.3f}m")

        # Validate consistency
        if pos_diff < 0.05:  # < 5cm difference
            print(f"[Fusion] ✓ Views highly consistent, boosting confidence")
            d455_result['confidence'] = min(d455_result['confidence'] + 10, 95)
            d455_result['multi_view_validated'] = True
            d455_result['validation_quality'] = 'excellent'
        elif pos_diff < 0.15:  # < 15cm difference
            print(f"[Fusion] ✓ Views reasonably consistent")
            d455_result['confidence'] = min(d455_result['confidence'] + 5, 90)
            d455_result['multi_view_validated'] = True
            d455_result['validation_quality'] = 'good'
        else:  # > 15cm difference
            print(f"[Fusion] ⚠ Large discrepancy between views, reducing confidence")
            d455_result['confidence'] = min(d455_result['confidence'], 70)
            d455_result['multi_view_validated'] = False
            d455_result['validation_quality'] = 'poor'

        d455_result['position_difference_m'] = float(pos_diff)
        d455_result['head_camera_position'] = head_pos.tolist()

        return d455_result

    async def _phase2_wrist_refinement(
        self,
        object_name: str,
        arm: str,
        initial_result: Dict
    ) -> Optional[Dict]:
        """Phase 2: Use wrist camera for close-up refinement."""

        # Step 1: Switch to wrist camera
        print("[Phase2] Step 1: Switching to wrist camera...")
        self._disable_head_camera()
        self._enable_wrist_camera(arm)

        # Step 2: Move wrist above object
        print("[Phase2] Step 2: Moving wrist above object...")
        estimated_pos = initial_result['position']

        # Calculate scan position (30cm above object, pointing down)
        scan_height = 0.3
        scan_pose = [
            estimated_pos[0],
            estimated_pos[1],
            estimated_pos[2] + scan_height,
            np.pi,  # Point down
            0.0,
            0.0
        ]

        # Validate scan pose
        if not self.safety.validate_pose(scan_pose):
            print("[Phase2] ✗ Scan pose outside workspace")
            return None

        # Move to scan position
        success = self.driver.move_to_pose(arm, scan_pose, speed=0.2, timeout=10.0)
        if not success:
            print("[Phase2] ✗ Failed to move to scan position")
            return None

        # Wait for motion to settle
        await asyncio.sleep(1.0)

        # Step 3: Capture wrist camera
        print("[Phase2] Step 3: Capturing from wrist camera...")
        wrist_result = await self._capture_and_analyze_wrist(
            object_name, arm, initial_result
        )

        if not wrist_result or not wrist_result.get('found'):
            print("[Phase2] ✗ Object not visible in wrist view")
            return None

        # Step 4: Capture D455 from new angle (optional, for additional validation)
        print("[Phase2] Step 4: Capturing D455 from new angle...")
        d455_result_phase2 = await self._capture_and_analyze_d455(object_name, "phase2")

        # Step 5: Fuse all results
        print("[Phase2] Step 5: Fusing all views...")
        final_result = self._fuse_all_results(
            object_name,
            initial_result,
            wrist_result,
            d455_result_phase2
        )

        return final_result

    async def _capture_and_analyze_wrist(
        self,
        object_name: str,
        arm: str,
        initial_result: Dict
    ) -> Optional[Dict]:
        """Capture and analyze wrist camera image."""

        # Capture image
        wrist_camera = f"{arm}_hand"
        wrist_image_bytes = self.driver.capture_image(wrist_camera)

        if not wrist_image_bytes:
            print("[Wrist] ✗ Failed to capture image")
            return None

        print(f"[Wrist] ✓ Captured: {len(wrist_image_bytes)} bytes")

        # Decode image
        nparr = np.frombuffer(wrist_image_bytes, np.uint8)
        wrist_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Process image (denoise, sharpen, white balance)
        processed_wrist, metadata = self.image_processor.process_wrist_camera_image(wrist_image)

        # Save debug images
        if self.debug:
            self.image_processor.save_debug_images(
                "debug_wrist_phase2",
                raw_image=wrist_image,
                processed_image=processed_wrist
            )

        # Encode processed image
        jpeg_bytes = self.image_processor.encode_image_to_jpeg(processed_wrist)

        # Get optimized prompt with initial position context
        prompt = self.prompts.get_phase2_wrist_camera_prompt(
            object_name,
            initial_result['position']
        )

        # Call VLM with custom prompt
        print("[Wrist] Analyzing with VLM (refinement)...")
        result = await self.vlm.locate_object(
            jpeg_bytes,
            object_name,
            self.safety.get_workspace_bounds(),
            custom_prompt=prompt
        )

        if result and result.get('found'):
            result['wrist_view'] = True
            result['refinement_applied'] = True
            print(f"[Wrist] ✓ Object detected (close-up)")

        return result

    def _fuse_all_results(
        self,
        object_name: str,
        phase1_result: Dict,
        wrist_result: Dict,
        d455_phase2_result: Optional[Dict]
    ) -> Dict:
        """Fuse all results from both phases."""

        print("[Fusion] Fusing all views (Phase 1 + Phase 2)...")

        # Start with Phase 1 D455 result (most reliable for 3D position)
        final_result = phase1_result.copy()

        # If we have Phase 2 D455, use it (arm is in different position, less occlusion)
        if d455_phase2_result and d455_phase2_result.get('found'):
            print("[Fusion] Using Phase 2 D455 position (less occlusion)")
            final_result['position'] = d455_phase2_result['position']
            final_result['phase2_d455_used'] = True

        # Incorporate wrist camera information
        if wrist_result and wrist_result.get('found'):
            # Wrist camera provides detailed description and grasp info
            final_result['description'] = f"Multi-view: {final_result.get('description', '')} | Wrist close-up: {wrist_result.get('description', '')}"

            if 'grasp_recommendations' in wrist_result:
                final_result['grasp_recommendations'] = wrist_result['grasp_recommendations']

            # Boost confidence due to wrist validation
            final_result['confidence'] = min(final_result['confidence'] + 5, 95)
            final_result['wrist_validated'] = True

            print(f"[Fusion] ✓ Wrist camera information incorporated")

        # Mark as fully refined
        final_result['refinement_applied'] = True
        final_result['multi_stage_fusion'] = True

        print(f"[Fusion] ✓ Final result:")
        print(f"  Position: {final_result['position']}")
        print(f"  Confidence: {final_result['confidence']}%")

        return final_result

    async def _retract_arm(self, arm: str) -> bool:
        """Move arm to retracted pose to avoid occlusion."""

        # Retracted joint positions (arm pulled back and up)
        retracted_positions = {
            'right': {
                'right_s0': -0.5,
                'right_s1': -0.5,
                'right_e0': 0.0,
                'right_e1': 1.5,
                'right_w0': 0.0,
                'right_w1': 1.0,
                'right_w2': 0.0,
            },
            'left': {
                'left_s0': 0.5,
                'left_s1': -0.5,
                'left_e0': 0.0,
                'left_e1': 1.5,
                'left_w0': 0.0,
                'left_w1': 1.0,
                'left_w2': 0.0,
            }
        }

        if arm not in retracted_positions:
            return False

        return self.driver.move_to_joint_positions(
            arm,
            retracted_positions[arm],
            speed=0.3,
            timeout=10.0
        )

    def _enable_head_camera(self):
        """Enable Baxter head camera."""
        self._head_camera_active = True
        print("  ✓ Head camera enabled")

    def _disable_head_camera(self):
        """Disable Baxter head camera."""
        self._head_camera_active = False
        print("  ✓ Head camera disabled")

    def _enable_wrist_camera(self, arm: str):
        """Enable Baxter wrist camera."""
        self._wrist_camera_active = True
        print(f"  ✓ {arm} wrist camera enabled")

    def _disable_wrist_camera(self):
        """Disable Baxter wrist camera."""
        self._wrist_camera_active = False
        print("  ✓ Wrist camera disabled")
