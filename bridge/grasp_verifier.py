"""
Grasp Verification Module

This module provides post-grasp verification using wrist camera and VLM.
After a pick action, it captures an image from the wrist camera and asks
the VLM to verify if the gripper is holding an object.

Features:
- Optional verification (can be disabled via config)
- Automatic retry on grasp failure
- Isolated from main pick logic (failures don't break the system)
- Configurable retry attempts

Usage:
    verifier = GraspVerifier(driver, vlm_client, enabled=True)
    success = await verifier.verify_and_retry_if_needed(
        arm='right',
        object_name='blue cube',
        pick_function=lambda: pick_by_name(...)
    )
"""

import asyncio
from typing import Callable, Optional, Dict, Any
import numpy as np


class GraspVerifier:
    """Verify grasp success using wrist camera and VLM."""

    def __init__(
        self,
        driver,
        vlm_client,
        enabled: bool = True,
        max_retries: int = 2,
        debug: bool = False
    ):
        """Initialize grasp verifier.

        Args:
            driver: BaxterDriver instance
            vlm_client: VLMClient instance
            enabled: Enable/disable verification (default: True)
            max_retries: Maximum retry attempts (default: 2)
            debug: Save debug images (default: False)
        """
        self.driver = driver
        self.vlm = vlm_client
        self.enabled = enabled
        self.max_retries = max_retries
        self.debug = debug

        print(f"[GraspVerifier] Initialized (enabled={enabled}, max_retries={max_retries})")

    async def verify_grasp(self, arm: str, object_name: str) -> Dict[str, Any]:
        """Verify if gripper is holding an object using wrist camera.

        Args:
            arm: Which arm ('left' or 'right')
            object_name: Name of object that should be grasped

        Returns:
            Dict with 'success' (bool), 'confidence' (float), 'reasoning' (str)
        """
        if not self.enabled:
            print("[GraspVerifier] Verification disabled, assuming success")
            return {
                'success': True,
                'confidence': 1.0,
                'reasoning': 'Verification disabled'
            }

        try:
            print(f"[GraspVerifier] Verifying grasp on {arm} arm...")

            # Step 1: Capture image from wrist camera
            camera_name = f"{arm}_hand"
            print(f"[GraspVerifier] Capturing from {camera_name} camera...")

            rgb_image = self.driver.capture_camera_image(camera_name)
            if rgb_image is None:
                print(f"[GraspVerifier] Warning: Failed to capture from {camera_name}")
                # Fail-safe: assume success if camera fails
                return {
                    'success': True,
                    'confidence': 0.5,
                    'reasoning': 'Camera capture failed, assuming success'
                }

            # Save debug image if enabled
            if self.debug:
                import cv2
                import time
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                debug_path = f"grasp_verify_{arm}_{timestamp}.jpg"
                cv2.imwrite(debug_path, cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR))
                print(f"[GraspVerifier] Debug image saved: {debug_path}")

            # Step 2: Ask VLM to verify grasp
            prompt = self._build_verification_prompt(object_name)
            print(f"[GraspVerifier] Asking VLM to verify...")

            vlm_response = await self.vlm.query_image(rgb_image, prompt)

            # Step 3: Parse VLM response
            result = self._parse_vlm_response(vlm_response)

            print(f"[GraspVerifier] Result: {result['success']} "
                  f"(confidence: {result['confidence']:.2f})")
            print(f"[GraspVerifier] Reasoning: {result['reasoning']}")

            return result

        except Exception as e:
            print(f"[GraspVerifier] Error during verification: {e}")
            # Fail-safe: assume success on error
            return {
                'success': True,
                'confidence': 0.5,
                'reasoning': f'Verification error: {str(e)}, assuming success'
            }

    def _build_verification_prompt(self, object_name: str) -> str:
        """Build prompt for VLM to verify grasp."""
        prompt = f"""Look at this image from a robot gripper's wrist camera.

The robot just attempted to pick up: {object_name}

Your task: Determine if the gripper is successfully holding the object.

Look for:
1. Is the object visible between the gripper fingers?
2. Are the gripper fingers closed around something?
3. Does the object appear to be securely held?

Answer in this JSON format:
{{
    "holding_object": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of what you see"
}}

IMPORTANT: Return ONLY the JSON, no other text."""
        return prompt

    def _parse_vlm_response(self, response: str) -> Dict[str, Any]:
        """Parse VLM response to extract verification result."""
        import json

        try:
            # Clean response
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()

            # Parse JSON
            data = json.loads(response)

            return {
                'success': data.get('holding_object', False),
                'confidence': data.get('confidence', 0.5),
                'reasoning': data.get('reasoning', 'No reasoning provided')
            }

        except Exception as e:
            print(f"[GraspVerifier] Failed to parse VLM response: {e}")
            print(f"[GraspVerifier] Raw response: {response}")

            # Fallback: try to detect keywords
            response_lower = response.lower()
            if any(word in response_lower for word in ['yes', 'holding', 'grasped', 'success']):
                return {
                    'success': True,
                    'confidence': 0.6,
                    'reasoning': 'Keyword-based detection (fallback)'
                }
            else:
                return {
                    'success': False,
                    'confidence': 0.6,
                    'reasoning': 'No positive keywords detected (fallback)'
                }

    async def verify_and_retry_if_needed(
        self,
        arm: str,
        object_name: str,
        pick_function: Callable,
        pick_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Verify grasp and retry if failed.

        Args:
            arm: Which arm ('left' or 'right')
            object_name: Name of object to pick
            pick_function: Function to call for picking (e.g., pick_by_name)
            pick_params: Parameters to pass to pick_function

        Returns:
            Dict with 'success', 'attempts', 'verification_result'
        """
        if not self.enabled:
            print("[GraspVerifier] Verification disabled, skipping")
            return {
                'success': True,
                'attempts': 1,
                'verification_result': None
            }

        if pick_params is None:
            pick_params = {}

        attempts = 0
        last_verification = None

        while attempts < self.max_retries:
            attempts += 1
            print(f"\n[GraspVerifier] Attempt {attempts}/{self.max_retries}")

            # Verify current grasp
            verification = await self.verify_grasp(arm, object_name)
            last_verification = verification

            if verification['success']:
                print(f"[GraspVerifier] ✓ Grasp verified successfully on attempt {attempts}")
                return {
                    'success': True,
                    'attempts': attempts,
                    'verification_result': verification
                }

            # Grasp failed
            print(f"[GraspVerifier] ✗ Grasp verification failed: {verification['reasoning']}")

            if attempts < self.max_retries:
                print(f"[GraspVerifier] Retrying pick operation...")

                # Open gripper to release (if anything)
                try:
                    self.driver.gripper_command(arm, "open")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"[GraspVerifier] Warning: Failed to open gripper: {e}")

                # Retry pick
                try:
                    result = await pick_function(**pick_params)
                    if not result.get('success'):
                        print(f"[GraspVerifier] Pick retry failed: {result.get('message')}")
                        break
                except Exception as e:
                    print(f"[GraspVerifier] Error during pick retry: {e}")
                    break

                # Wait before verification
                await asyncio.sleep(1.0)

        # All retries exhausted
        print(f"[GraspVerifier] ✗ Failed after {attempts} attempts")
        return {
            'success': False,
            'attempts': attempts,
            'verification_result': last_verification
        }
