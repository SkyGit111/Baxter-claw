"""VLM (Vision-Language Model) client for object detection and localization."""

import base64
import os
from typing import Dict, List, Optional, Tuple
import httpx


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
            provider: VLM provider ('claude', 'openai', 'custom')
            api_key: API key for the provider (or use environment variable)
        """
        self.provider = provider.lower()
        self.api_key = api_key or self._get_api_key()

        # API endpoints
        self.endpoints = {
            'claude': 'https://api.anthropic.com/v1/messages',
            'openai': 'https://api.openai.com/v1/chat/completions',
        }

        # Model names
        self.models = {
            'claude': 'claude-3-5-sonnet-20241022',
            'openai': 'gpt-4-vision-preview',
        }

    def _get_api_key(self) -> str:
        """Get API key from environment variables."""
        if self.provider == 'claude':
            return os.getenv('ANTHROPIC_API_KEY', '')
        elif self.provider == 'openai':
            return os.getenv('OPENAI_API_KEY', '')
        return ''

    async def locate_object(
        self,
        image_bytes: bytes,
        object_name: str,
        workspace_bounds: Optional[Dict[str, Tuple[float, float]]] = None
    ) -> Optional[Dict]:
        """Locate an object in the image.

        Args:
            image_bytes: JPEG image data
            object_name: Name of object to locate (e.g., "red cup", "blue box")
            workspace_bounds: Optional workspace bounds for validation

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

            # Construct prompt
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

    def _parse_locate_response(self, response: Dict, object_name: str) -> Dict:
        """Parse VLM response for object location."""
        import json

        try:
            # Extract text from response
            if self.provider == 'claude':
                text = response['content'][0]['text']
            elif self.provider == 'openai':
                text = response['choices'][0]['message']['content']
            else:
                text = str(response)

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

            # Validate and normalize
            return {
                'found': result.get('found', False),
                'position': result.get('position', [0.0, 0.0, 0.0]),
                'confidence': result.get('confidence', 0.0),
                'description': result.get('description', ''),
                'bounding_box': result.get('bounding_box', [0, 0, 0, 0]),
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

    async def describe_scene(self, image_bytes: bytes) -> str:
        """Get a general description of the scene.

        Args:
            image_bytes: JPEG image data

        Returns:
            Text description of the scene
        """
        try:
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

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
