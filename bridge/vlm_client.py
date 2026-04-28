"""VLM (Vision-Language Model) client for object detection and localization."""

import base64
import os
from typing import Dict, List, Optional, Tuple
import httpx
import numpy as np


class VLMClient:
    """Client for interacting with Vision-Language Models.

    Supports multiple VLM providers:
    - Claude (Anthropic)
    - GPT-4V (OpenAI)
    - Custom endpoints
    """

    def __init__(self, provider: str = "claude", api_key: Optional[str] = None):
        """Initialize VLM client.

        Args:
            provider: VLM provider ('claude', 'openai', 'qwen', 'custom')
            api_key: API key for the provider (or use environment variable)
        """
        self.provider = provider.lower()
        self.api_key = api_key or self._get_api_key()

        # API endpoints
        self.endpoints = {
            'claude': 'https://api.anthropic.com/v1/messages',
            'openai': 'https://api.openai.com/v1/chat/completions',
            'qwen': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
        }

        # Model names
        self.models = {
            'claude': 'claude-3-5-sonnet-20241022',
            'openai': 'gpt-4-vision-preview',
            'qwen': 'qwen-vl-max',
        }

    def _get_api_key(self) -> str:
        """Get API key from environment variables."""
        if self.provider == 'claude':
            return os.getenv('ANTHROPIC_API_KEY', '')
        elif self.provider == 'openai':
            return os.getenv('OPENAI_API_KEY', '')
        elif self.provider == 'qwen':
            return os.getenv('QWEN_API_KEY', '')
        return ''

    async def locate_object(
        self,
        image_bytes: bytes,
        object_name: str,
        workspace_bounds: Optional[Dict[str, Tuple[float, float]]] = None,
        custom_prompt: Optional[str] = None
    ) -> Optional[Dict]:
        """Locate an object in the image.

        Args:
            image_bytes: JPEG image data
            object_name: Name of object to locate (e.g., "red cup", "blue box")
            workspace_bounds: Optional workspace bounds for validation
            custom_prompt: Optional custom prompt (overrides default)

        Returns:
            Dict with object location info:
            {
                'found': bool,
                'position': [x, y, z],  # Estimated 3D position
                'confidence': float,
                'description': str,
                'bounding_box': [x1, y1, x2, y2]  # Pixel coordinates
            }
        """
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

            # Use custom prompt if provided, otherwise build default
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = self._build_locate_prompt(object_name, workspace_bounds)

            # Call VLM
            response = await self._call_vlm(image_b64, prompt)

            # Parse response
            result = self._parse_locate_response(response, object_name)

            return result

        except Exception as e:
            print(f"Failed to locate object: {e}")
            return None

    def _build_locate_prompt(
        self,
        object_name: str,
        workspace_bounds: Optional[Dict[str, Tuple[float, float]]]
    ) -> str:
        """Build prompt for object localization."""
        prompt = f"""Analyze this image from a Baxter robot's camera and locate the {object_name}.

Please provide:
1. Whether the {object_name} is visible in the image (yes/no)
2. If visible, describe its location in the image (e.g., "center-left", "top-right")
3. Estimate the object's position relative to the robot's workspace
4. Provide a bounding box in pixel coordinates [x1, y1, x2, y2] where (0,0) is top-left
5. Your confidence level (0-100%)

"""

        if workspace_bounds:
            prompt += f"""
The robot's workspace is:
- X (forward): {workspace_bounds['x'][0]:.2f}m to {workspace_bounds['x'][1]:.2f}m
- Y (lateral): {workspace_bounds['y'][0]:.2f}m to {workspace_bounds['y'][1]:.2f}m
- Z (height): {workspace_bounds['z'][0]:.2f}m to {workspace_bounds['z'][1]:.2f}m

Estimate the 3D position within this workspace.
"""

        prompt += """
Respond in JSON format:
{
    "found": true/false,
    "position": [x, y, z],
    "confidence": 0-100,
    "description": "detailed description",
    "bounding_box": [x1, y1, x2, y2]
}
"""

        return prompt

    async def _call_vlm(self, image_b64: str, prompt: str) -> Dict:
        """Call VLM API."""
        if self.provider == 'claude':
            return await self._call_claude(image_b64, prompt)
        elif self.provider == 'openai':
            return await self._call_openai(image_b64, prompt)
        elif self.provider == 'qwen':
            return await self._call_qwen(image_b64, prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def _call_claude(self, image_b64: str, prompt: str) -> Dict:
        """Call Claude API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.endpoints['claude'],
                headers={
                    'x-api-key': self.api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json',
                },
                json={
                    'model': self.models['claude'],
                    'max_tokens': 1024,
                    'messages': [
                        {
                            'role': 'user',
                            'content': [
                                {
                                    'type': 'image',
                                    'source': {
                                        'type': 'base64',
                                        'media_type': 'image/jpeg',
                                        'data': image_b64,
                                    },
                                },
                                {
                                    'type': 'text',
                                    'text': prompt,
                                },
                            ],
                        }
                    ],
                },
            )
            response.raise_for_status()
            return response.json()

    async def _call_openai(self, image_b64: str, prompt: str) -> Dict:
        """Call OpenAI GPT-4V API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.endpoints['openai'],
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': self.models['openai'],
                    'messages': [
                        {
                            'role': 'user',
                            'content': [
                                {
                                    'type': 'text',
                                    'text': prompt,
                                },
                                {
                                    'type': 'image_url',
                                    'image_url': {
                                        'url': f'data:image/jpeg;base64,{image_b64}',
                                    },
                                },
                            ],
                        }
                    ],
                    'max_tokens': 1024,
                },
            )
            response.raise_for_status()
            return response.json()

    async def _call_qwen(self, image_b64: str, prompt: str) -> Dict:
        """Call Qwen VL API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.endpoints['qwen'],
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': self.models['qwen'],
                    'messages': [
                        {
                            'role': 'user',
                            'content': [
                                {
                                    'type': 'text',
                                    'text': prompt,
                                },
                                {
                                    'type': 'image_url',
                                    'image_url': {
                                        'url': f'data:image/jpeg;base64,{image_b64}',
                                    },
                                },
                            ],
                        }
                    ],
                    'max_tokens': 1024,
                },
            )
            response.raise_for_status()
            return response.json()

    def _parse_locate_response(self, response: Dict, object_name: str) -> Dict:
        """Parse VLM response for object location."""
        import json

        try:
            # Extract text from response
            if self.provider == 'claude':
                text = response['content'][0]['text']
            elif self.provider == 'openai':
                text = response['choices'][0]['message']['content']
            elif self.provider == 'qwen':
                text = response['choices'][0]['message']['content']
            else:
                text = str(response)

            print(f"[VLM] Raw response text (first 500 chars):")
            print(f"  {text[:500]}...")

            # Try to extract JSON from response
            # Look for JSON block in markdown code fence or plain text
            if '```json' in text:
                json_start = text.find('```json') + 7
                json_end = text.find('```', json_start)
                json_text = text[json_start:json_end].strip()
            elif '```' in text:
                json_start = text.find('```') + 3
                json_end = text.find('```', json_start)
                json_text = text[json_start:json_end].strip()
            elif '{' in text and '}' in text:
                json_start = text.find('{')
                json_end = text.rfind('}') + 1
                json_text = text[json_start:json_end]
            else:
                json_text = text

            # Parse JSON
            result = json.loads(json_text)
            print(f"[VLM] Parsed JSON result:")
            print(f"  found: {result.get('found')}")
            print(f"  confidence: {result.get('confidence')}")
            print(f"  position: {result.get('position')}")

            # Smart detection: if VLM provides position and confidence > 0,
            # it likely found the object even if 'found' field is missing or false
            found = result.get('found', False)
            confidence = result.get('confidence', 0.0)
            position = result.get('position', [0.0, 0.0, 0.0])
            bounding_box = result.get('bounding_box', [0, 0, 0, 0])

            # Override found=false if we have valid detection data
            if not found and confidence > 50 and any(p != 0.0 for p in position):
                print(f"[VLM] ⚠ Overriding found=false because confidence={confidence}% and position is valid")
                found = True

            # Validate and normalize
            return {
                'found': found,
                'position': position,
                'confidence': confidence,
                'description': result.get('description', ''),
                'bounding_box': bounding_box,
            }

        except Exception as e:
            print(f"Failed to parse VLM response: {e}")
            print(f"Response: {response}")
            return {
                'found': False,
                'position': [0.0, 0.0, 0.0],
                'confidence': 0.0,
                'description': f'Failed to parse response: {e}',
                'bounding_box': [0, 0, 0, 0],
            }

    async def describe_scene(self, image_bytes: bytes, language: str = "zh") -> str:
        """Get a general description of the scene.

        Args:
            image_bytes: JPEG image data
            language: Response language ('zh' for Chinese, 'en' for English)

        Returns:
            Text description of the scene
        """
        try:
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

            if language == "zh":
                prompt = """请用中文描述这个场景（从机器人的视角）。包括：
1. 可见的物体有哪些
2. 它们的大致位置
3. 任何值得注意的特征或障碍物
4. 对机器人操作任务的建议

请简洁明了，重点关注对机器人控制有用的信息。"""
            else:
                prompt = """Describe this scene from a robot's perspective. Include:
1. What objects are visible
2. Their approximate locations
3. Any notable features or obstacles
4. Suggestions for manipulation tasks

Be concise and focus on actionable information for robot control."""

            response = await self._call_vlm(image_b64, prompt)

            # Extract text
            if self.provider == 'claude':
                return response['content'][0]['text']
            elif self.provider == 'openai':
                return response['choices'][0]['message']['content']
            elif self.provider == 'qwen':
                return response['choices'][0]['message']['content']
            else:
                return str(response)

        except Exception as e:
            print(f"Failed to describe scene: {e}")
            return f"Error: {e}"

    async def identify_objects(self, image_bytes: bytes) -> List[Dict]:
        """Identify all objects in the scene.

        Args:
            image_bytes: JPEG image data

        Returns:
            List of detected objects with their properties
        """
        try:
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

            prompt = """Identify all objects visible in this image. For each object, provide:
1. Object name/type
2. Color
3. Approximate size (small/medium/large)
4. Location in image (e.g., "center", "left side")
5. Whether it appears graspable by a robot

Respond in JSON format:
[
    {
        "name": "object name",
        "color": "color",
        "size": "small/medium/large",
        "location": "description",
        "graspable": true/false
    },
    ...
]
"""

            response = await self._call_vlm(image_b64, prompt)

            # Extract and parse JSON
            if self.provider == 'claude':
                text = response['content'][0]['text']
            elif self.provider == 'openai':
                text = response['choices'][0]['message']['content']
            elif self.provider == 'qwen':
                text = response['choices'][0]['message']['content']
            else:
                text = str(response)

            # Extract JSON array
            import json
            if '```json' in text:
                json_start = text.find('```json') + 7
                json_end = text.find('```', json_start)
                json_text = text[json_start:json_end].strip()
            elif '[' in text and ']' in text:
                json_start = text.find('[')
                json_end = text.rfind(']') + 1
                json_text = text[json_start:json_end]
            else:
                json_text = text

            objects = json.loads(json_text)
            return objects

        except Exception as e:
            print(f"Failed to identify objects: {e}")
            return []

    async def locate_object_with_depth(
        self,
        image_bytes: bytes,
        depth_image: np.ndarray,
        object_name: str,
        depth_camera_driver,
        workspace_bounds: Optional[Dict[str, Tuple[float, float]]] = None,
        custom_prompt: Optional[str] = None
    ) -> Optional[Dict]:
        """Locate an object using VLM + depth camera for accurate 3D position.

        Args:
            image_bytes: JPEG image data
            depth_image: Depth image array (H, W) in millimeters
            object_name: Name of object to locate
            depth_camera_driver: RealSense driver instance for 3D conversion
            workspace_bounds: Optional workspace bounds for validation
            custom_prompt: Optional custom prompt (overrides default)

        Returns:
            Dict with accurate 3D position from depth data
        """
        try:
            # Step 1: Use VLM to identify object and get 2D bounding box
            print(f"[VLM+Depth] Locating {object_name} with depth enhancement...")
            location_2d = await self.locate_object(
                image_bytes,
                object_name,
                workspace_bounds,
                custom_prompt=custom_prompt
            )

            if not location_2d or not location_2d['found']:
                return location_2d

            # Step 2: Extract bounding box center
            bbox = location_2d['bounding_box']
            center_x = (bbox[0] + bbox[2]) // 2
            center_y = (bbox[1] + bbox[3]) // 2

            print(f"  [Debug] VLM bounding box: {bbox}")
            print(f"  [Debug] Bbox center pixel: ({center_x}, {center_y})")
            print(f"  [Debug] VLM estimated position: {location_2d['position']}")

            # Step 3: Get real 3D position from depth camera
            # Check depth value at center
            if center_y < depth_image.shape[0] and center_x < depth_image.shape[1]:
                depth_at_center = depth_image[center_y, center_x]
                print(f"  [Debug] Depth at center pixel: {depth_at_center}mm")
            else:
                print(f"  [Debug] WARNING: Center pixel out of bounds!")

            point_3d = depth_camera_driver.get_3d_point_from_pixel(
                depth_image,
                center_x,
                center_y,
                window_size=5
            )

            if point_3d is None:
                print(f"  [Debug] WARNING: No valid depth at object center!")
                print(f"  [Debug] Using VLM estimate (unreliable)")
                return location_2d

            # Step 4: Position is in camera frame, will be transformed by caller
            real_position = list(point_3d)

            print(f"  [Debug] Depth camera measured position (camera frame): {real_position}")
            vlm_pos = location_2d['position']
            diff = [real_position[i] - vlm_pos[i] for i in range(3)]
            print(f"  [Debug] VLM vs Depth difference: {diff}")
            print(f"  [Debug] Difference magnitude: {np.linalg.norm(diff):.3f}m")

            # Return enhanced result
            return {
                'found': True,
                'position': real_position,  # Real 3D position from depth (camera frame)
                'confidence': 95,  # High confidence with depth data
                'description': location_2d['description'],
                'bounding_box': bbox,
                'depth_enhanced': True,
                'vlm_estimate': location_2d['position'],  # Keep VLM estimate for comparison
            }

        except Exception as e:
            print(f"Failed to locate object with depth: {e}")
            # Fallback to VLM-only estimate
            return await self.locate_object(image_bytes, object_name, workspace_bounds)

    async def query_image(self, image_bytes: bytes, prompt: str) -> str:
        """Generic method to query VLM with an image and custom prompt.

        Args:
            image_bytes: JPEG image data
            prompt: Custom prompt for the VLM

        Returns:
            VLM response text
        """
        try:
            # Encode image
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

            # Call VLM
            response = await self._call_vlm(image_b64, prompt)

            # Extract text from response based on provider
            if self.provider == 'claude':
                response_text = response['content'][0]['text']
            elif self.provider == 'openai':
                response_text = response['choices'][0]['message']['content']
            elif self.provider == 'qwen':
                response_text = response['choices'][0]['message']['content']
            else:
                response_text = str(response)

            return response_text

        except Exception as e:
            print(f"Failed to query VLM: {e}")
            raise

