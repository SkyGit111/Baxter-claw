"""
Baxter-Claw OpenClaw Plugin

This plugin enables natural language control of Baxter robot through OpenClaw.
Uses LLM (Qwen) for intelligent intent recognition instead of regex patterns.

Example interactions:
- "帮我拿一下红色的杯子" -> pick_by_name("红色杯子")
- "把它放到桌子左边" -> place([x, y, z])
- "打开夹爪" -> gripper("open")
- "看看桌上有什么" -> describe_scene()
"""

import json
import os
from typing import Dict, Any, Optional
import httpx


class BaxterClawPlugin:
    """OpenClaw plugin for Baxter-Claw control."""

    def __init__(
        self,
        bridge_url: str = "http://localhost:8420",
        llm_provider: str = "qwen",
        llm_api_key: Optional[str] = None,
        use_d455: bool = True  # Use D455 depth camera by default
    ):
        """Initialize plugin.

        Args:
            bridge_url: URL of Baxter-Claw Bridge Server
            llm_provider: LLM provider for intent recognition ('qwen', 'openai', 'claude')
            llm_api_key: API key for LLM (or use environment variable)
            use_d455: Use D455 depth camera for vision tasks (recommended)
                     If False, will use right_hand camera (limited view)
        """
        self.bridge_url = bridge_url
        self.client = httpx.Client(timeout=30.0)
        self.use_d455 = use_d455

        # LLM configuration for intent recognition
        self.llm_provider = llm_provider.lower()
        self.llm_api_key = llm_api_key or self._get_llm_api_key()

        # LLM endpoints
        self.llm_endpoints = {
            'qwen': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
            'openai': 'https://api.openai.com/v1/chat/completions',
            'claude': 'https://api.anthropic.com/v1/messages',
        }

        # LLM models
        self.llm_models = {
            'qwen': 'qwen-plus',
            'openai': 'gpt-4',
            'claude': 'claude-3-5-sonnet-20241022',
        }

    def _get_llm_api_key(self) -> str:
        """Get LLM API key from environment variables."""
        if self.llm_provider == 'qwen':
            return os.getenv('QWEN_API_KEY', '')
        elif self.llm_provider == 'openai':
            return os.getenv('OPENAI_API_KEY', '')
        elif self.llm_provider == 'claude':
            return os.getenv('ANTHROPIC_API_KEY', '')
        return ''

    def parse_intent(self, user_message: str) -> Dict[str, Any]:
        """Parse user message to extract intent and parameters using LLM.

        Args:
            user_message: Natural language message from user

        Returns:
            Dict with 'action', 'params', and 'confidence'
        """
        try:
            # Build prompt for LLM
            prompt = self._build_intent_prompt(user_message)

            # Call LLM
            response = self._call_llm(prompt)

            # Parse LLM response
            intent = self._parse_llm_response(response)

            return intent

        except Exception as e:
            print(f"LLM intent parsing failed: {e}")
            # Fallback to unknown
            return {
                'action': 'unknown',
                'params': {},
                'confidence': 0.0,
                'error': str(e)
            }

    def _build_intent_prompt(self, user_message: str) -> str:
        """Build prompt for LLM intent recognition."""
        prompt = f"""You are a robot control assistant for a dual-arm Baxter robot. Parse the following user command and identify the intent and parameters.

User command: "{user_message}"

IMPORTANT: The robot has TWO arms (left and right). You must identify which arm(s) to use.

Available actions (categorized by type):

QUERY ACTIONS (return information, no robot movement):
1. locate_object - Find the 3D position of an object
   Parameters:
   - object_name (string, e.g., "rubik's cube", "魔方", "red cup")
   Use this when user asks: "where is X", "find X", "locate X", "识别X的坐标"

2. describe_scene - Describe what the robot sees
   Parameters: none
   Use this when user asks: "what do you see", "describe the scene", "看看有什么"

3. identify_objects - List all objects in the scene
   Parameters: none
   Use this when user asks: "what objects are there", "list objects", "有哪些物体"

4. status - Check robot status
   Parameters: none

MANIPULATION ACTIONS (move robot to do tasks):
5. pick_by_name - Pick up an object by name
   Parameters:
   - object_name (string)
   - arm (string: "left"/"right"/"auto", default: "auto")

6. place - Place the held object at a direction
   Parameters:
   - direction (string: "left"/"right"/"front"/"back"/"up"/"down"/"center")
   - arm (string: "left"/"right"/"auto", default: "auto")

7. place_by_name - Place the held object relative to another object (RECOMMENDED for precise placement)
   Parameters:
   - target_object_name (string: name of reference object)
   - relative_position (string: "next_to"/"on_top"/"behind"/"in_front", default: "next_to")
   - arm (string: "left"/"right"/"auto", default: "auto")

8. move_to - Move arm to a position
   Parameters:
   - position (list: [x, y, z])
   - arm (string: "left"/"right", required)

9. gripper_open - Open the gripper
   Parameters:
   - arm (string: "left"/"right"/"both", default: "right")

10. gripper_close - Close the gripper
    Parameters:
    - arm (string: "left"/"right"/"both", default: "right")

11. home - Return to home position
    Parameters:
    - arm (string: "left"/"right"/"both", default: "both")

12. bimanual_pick - Pick large object with both arms
    Parameters:
    - object_name (string)

13. handover - Hand over object from one arm to another
    Parameters:
    - from_arm (string: "left"/"right")
    - to_arm (string: "left"/"right")

Arm selection rules:
- If user specifies arm explicitly (e.g., "用左手", "with right arm"), use that arm
- If user says "both hands" or "两只手", use bimanual actions
- If arm is "auto", the system will choose based on which arm is holding the object
- For handover, identify which arm currently holds the object

IMPORTANT: Identify if this is a QUERY task or MANIPULATION task:
- QUERY tasks: locate_object, describe_scene, identify_objects, status
- MANIPULATION tasks: pick, place, place_by_name, move, gripper, home, handover

IMPORTANT: Use place_by_name instead of place when user specifies a target object:
- "把蓝色方块放到黄色方块上" → place_by_name(target_object_name="黄色方块", relative_position="on_top")
- "把它放到红色杯子旁边" → place_by_name(target_object_name="红色杯子", relative_position="next_to")
- "把它放到左边" → place(direction="左")

Respond ONLY with a JSON object in this exact format:
{{
    "action": "action_name",
    "params": {{"param_name": "param_value"}},
    "confidence": 0.0-1.0,
    "task_type": "query" or "manipulation"
}}

Examples:
- "识别魔方的坐标" -> {{"action": "locate_object", "params": {{"object_name": "魔方"}}, "confidence": 0.95, "task_type": "query"}}
- "where is the red cup" -> {{"action": "locate_object", "params": {{"object_name": "red cup"}}, "confidence": 0.95, "task_type": "query"}}
- "看看桌上有什么" -> {{"action": "describe_scene", "params": {{}}, "confidence": 0.9, "task_type": "query"}}
- "list all objects" -> {{"action": "identify_objects", "params": {{}}, "confidence": 0.9, "task_type": "query"}}
- "帮我拿一下红色的杯子" -> {{"action": "pick_by_name", "params": {{"object_name": "红色的杯子", "arm": "auto"}}, "confidence": 0.95, "task_type": "manipulation"}}
- "用左手拿白色盒子" -> {{"action": "pick_by_name", "params": {{"object_name": "白色盒子", "arm": "left"}}, "confidence": 0.95, "task_type": "manipulation"}}
- "用两只手拿那个大箱子" -> {{"action": "bimanual_pick", "params": {{"object_name": "大箱子"}}, "confidence": 0.9, "task_type": "manipulation"}}
- "把它放到左边" -> {{"action": "place", "params": {{"direction": "左", "arm": "auto"}}, "confidence": 0.9, "task_type": "manipulation"}}
- "把蓝色方块放到黄色方块上" -> {{"action": "place_by_name", "params": {{"target_object_name": "黄色方块", "relative_position": "on_top", "arm": "auto"}}, "confidence": 0.95, "task_type": "manipulation"}}
- "把它放到红色杯子旁边" -> {{"action": "place_by_name", "params": {{"target_object_name": "红色杯子", "relative_position": "next_to", "arm": "auto"}}, "confidence": 0.95, "task_type": "manipulation"}}
- "place it behind the white box" -> {{"action": "place_by_name", "params": {{"target_object_name": "white box", "relative_position": "behind", "arm": "auto"}}, "confidence": 0.95, "task_type": "manipulation"}}
- "打开左边夹爪" -> {{"action": "gripper_open", "params": {{"arm": "left"}}, "confidence": 0.95, "task_type": "manipulation"}}
- "把物体从右手传到左手" -> {{"action": "handover", "params": {{"from_arm": "right", "to_arm": "left"}}, "confidence": 0.9, "task_type": "manipulation"}}
- "两只手都回原位" -> {{"action": "home", "params": {{"arm": "both"}}, "confidence": 0.95, "task_type": "manipulation"}}

Now parse the user command and respond with JSON only:"""

        return prompt

    def _call_llm(self, prompt: str) -> Dict:
        """Call LLM API for intent recognition."""
        if self.llm_provider == 'qwen':
            return self._call_qwen_llm(prompt)
        elif self.llm_provider == 'openai':
            return self._call_openai_llm(prompt)
        elif self.llm_provider == 'claude':
            return self._call_claude_llm(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")

    def _call_qwen_llm(self, prompt: str) -> Dict:
        """Call Qwen LLM API."""
        response = self.client.post(
            self.llm_endpoints['qwen'],
            headers={
                'Authorization': f'Bearer {self.llm_api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': self.llm_models['qwen'],
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt,
                    }
                ],
                'temperature': 0.1,  # Low temperature for consistent parsing
            }
        )
        response.raise_for_status()
        return response.json()

    def _call_openai_llm(self, prompt: str) -> Dict:
        """Call OpenAI LLM API."""
        response = self.client.post(
            self.llm_endpoints['openai'],
            headers={
                'Authorization': f'Bearer {self.llm_api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': self.llm_models['openai'],
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt,
                    }
                ],
                'temperature': 0.1,
            }
        )
        response.raise_for_status()
        return response.json()

    def _call_claude_llm(self, prompt: str) -> Dict:
        """Call Claude LLM API."""
        response = self.client.post(
            self.llm_endpoints['claude'],
            headers={
                'x-api-key': self.llm_api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': self.llm_models['claude'],
                'max_tokens': 512,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt,
                    }
                ],
                'temperature': 0.1,
            }
        )
        response.raise_for_status()
        return response.json()

    def _parse_llm_response(self, response: Dict) -> Dict[str, Any]:
        """Parse LLM response to extract next action."""
        try:
            # Extract text from response
            if self.llm_provider == 'qwen' or self.llm_provider == 'openai':
                text = response['choices'][0]['message']['content']
            elif self.llm_provider == 'claude':
                text = response['content'][0]['text']
            else:
                text = str(response)

            # Extract JSON from response
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
            action_dict = json.loads(json_text)

            # Validate structure for workflow execution
            if 'action' not in action_dict:
                action_dict['action'] = 'next'
            if 'skill' not in action_dict and action_dict['action'] == 'next':
                action_dict['skill'] = 'unknown'
            if 'params' not in action_dict:
                action_dict['params'] = {}
            if 'confidence' not in action_dict:
                action_dict['confidence'] = 0.5

            return action_dict

        except Exception as e:
            print(f"Failed to parse LLM response: {e}")
            print(f"Response: {response}")
            return {
                'action': 'error',
                'message': f'LLM 响应解析失败: {e}'
            }

    def _choose_arm_by_position(self, position: list) -> str:
        """Choose arm based on object position (y-coordinate).

        Args:
            position: [x, y, z] position of object

        Returns:
            'left' or 'right'
        """
        # Baxter coordinate system (with D455 camera):
        # y ≈ 0.16m is the center line
        # y < 0.16m: closer to right arm (use right)
        # y > 0.16m: closer to left arm (use left)
        y = position[1] if len(position) > 1 else 0.0

        CENTER_Y = 0.16  # Center line between arms

        if y > CENTER_Y + 0.05:  # Object on left side (threshold 5cm)
            return 'left'
        elif y < CENTER_Y - 0.05:  # Object on right side
            return 'right'
        else:  # Object in center, default to right
            return 'right'
            return 'right'

    def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action by calling Bridge Server API.

        Args:
            action: Action name
            params: Action parameters

        Returns:
            Result dict with 'success', 'message', and optional 'data'
        """
        try:
            if action == 'pick':
                # Pick at a known position (from previous locate_object)
                arm = params.get('arm', 'auto')
                position = params.get('position')

                if not position or len(position) != 3:
                    return {
                        'success': False,
                        'message': "pick 需要提供 position 参数 [x, y, z]"
                    }

                # If arm is 'auto', choose based on position
                if arm == 'auto':
                    arm = self._choose_arm_by_position(position)
                    print(f"[Auto-select] Position {position}, choosing {arm} arm")

                response = self.client.post(
                    f"{self.bridge_url}/primitives/pick",
                    json={
                        'arm': arm,
                        'position': position,
                        'approach_height': params.get('approach_height', 0.1)
                    }
                )
                response.raise_for_status()
                result = response.json()

                if result.get('success'):
                    return {
                        'success': True,
                        'message': f"成功用{arm}臂在位置 {position} 抓取物体",
                        'data': result,
                        'arm_used': arm,
                        'position': position
                    }
                else:
                    return {
                        'success': False,
                        'message': f"抓取失败: {result.get('message', '未知错误')}",
                        'data': result
                    }

            elif action == 'pick_by_name':
                object_name = params.get('object_name', '')
                arm = params.get('arm', 'auto')

                # If arm is 'auto', first locate the object to determine which arm to use
                if arm == 'auto':
                    # Locate object first using D455 or fallback camera
                    locate_response = self.client.post(
                        f"{self.bridge_url}/vision/locate_object",
                        json={
                            'object_name': object_name,
                            'use_d455': self.use_d455  # Use D455 if available
                        }
                    )
                    locate_response.raise_for_status()
                    locate_result = locate_response.json()

                    if locate_result.get('success') and locate_result.get('position'):
                        # Choose arm based on object position
                        position = locate_result['position']
                        arm = self._choose_arm_by_position(position)
                        print(f"[Auto-select] Object at {position}, choosing {arm} arm")
                    else:
                        # Fallback to right arm if localization fails
                        arm = 'right'
                        print(f"[Auto-select] Localization failed, defaulting to right arm")

                # Execute pick_by_name with D455
                response = self.client.post(
                    f"{self.bridge_url}/vision/pick_by_name",
                    json={
                        'arm': arm,
                        'object_name': object_name,
                        'use_d455': self.use_d455  # Use D455 if available
                    }
                )
                response.raise_for_status()
                result = response.json()

                if result.get('success'):
                    return {
                        'success': True,
                        'message': f"成功用{arm}臂抓取 {object_name}",
                        'data': result,
                        'arm_used': arm
                    }
                else:
                    return {
                        'success': False,
                        'message': f"无法抓取 {object_name}: {result.get('message', '未知错误')}",
                        'data': result
                    }

            elif action == 'place':
                direction = params.get('direction', '前')
                arm = params.get('arm', 'auto')

                # If arm is 'auto', use the arm that's currently holding an object
                if arm == 'auto':
                    # Check robot state to determine which arm is holding object
                    if context.get('robot_state', {}).get('right_arm', {}).get('holding_object'):
                        arm = 'right'
                        print(f"  [Auto-select] Using right arm (holding object)")
                    elif context.get('robot_state', {}).get('left_arm', {}).get('holding_object'):
                        arm = 'left'
                        print(f"  [Auto-select] Using left arm (holding object)")
                    else:
                        # Default to right arm if no arm is holding anything
                        arm = 'right'
                        print(f"  [Auto-select] Defaulting to right arm (no object held)")

                # Convert direction to coordinates
                position = self._direction_to_position(direction)

                response = self.client.post(
                    f"{self.bridge_url}/primitives/place",
                    json={'arm': arm, 'position': position}
                )
                response.raise_for_status()
                result = response.json()

                return {
                    'success': result.get('success', False),
                    'message': f"已用{arm}臂放置到{direction}边",
                    'data': result,
                    'arm_used': arm
                }

            elif action == 'place_by_name':
                target_object_name = params.get('target_object_name', '')
                relative_position = params.get('relative_position', 'next_to')
                arm = params.get('arm', 'auto')

                # If arm is 'auto', use the arm that's currently holding an object
                if arm == 'auto':
                    if context.get('robot_state', {}).get('right_arm', {}).get('holding_object'):
                        arm = 'right'
                        print(f"  [Auto-select] Using right arm (holding object)")
                    elif context.get('robot_state', {}).get('left_arm', {}).get('holding_object'):
                        arm = 'left'
                        print(f"  [Auto-select] Using left arm (holding object)")
                    else:
                        arm = 'right'
                        print(f"  [Auto-select] Defaulting to right arm")

                response = self.client.post(
                    f"{self.bridge_url}/primitives/place_by_name",
                    json={
                        'arm': arm,
                        'target_object_name': target_object_name,
                        'relative_position': relative_position
                    }
                )
                response.raise_for_status()
                result = response.json()

                return {
                    'success': result.get('success', False),
                    'message': f"已将物体放置到{target_object_name}{relative_position}",
                    'data': result,
                    'arm_used': arm
                }

            elif action == 'gripper_open':
                arm = params.get('arm', 'right')

                if arm == 'both':
                    # Open both grippers
                    left_response = self.client.post(
                        f"{self.bridge_url}/gripper",
                        json={'arm': 'left', 'action': 'open'}
                    )
                    right_response = self.client.post(
                        f"{self.bridge_url}/gripper",
                        json={'arm': 'right', 'action': 'open'}
                    )
                    left_response.raise_for_status()
                    right_response.raise_for_status()
                    return {
                        'success': True,
                        'message': "两个夹爪已打开"
                    }
                else:
                    response = self.client.post(
                        f"{self.bridge_url}/gripper",
                        json={'arm': arm, 'action': 'open'}
                    )
                    response.raise_for_status()
                    return {
                        'success': True,
                        'message': f"{arm}臂夹爪已打开"
                    }

            elif action == 'gripper_close':
                arm = params.get('arm', 'right')

                if arm == 'both':
                    # Close both grippers
                    left_response = self.client.post(
                        f"{self.bridge_url}/gripper",
                        json={'arm': 'left', 'action': 'close'}
                    )
                    right_response = self.client.post(
                        f"{self.bridge_url}/gripper",
                        json={'arm': 'right', 'action': 'close'}
                    )
                    left_response.raise_for_status()
                    right_response.raise_for_status()
                    return {
                        'success': True,
                        'message': "两个夹爪已关闭"
                    }
                else:
                    response = self.client.post(
                        f"{self.bridge_url}/gripper",
                        json={'arm': arm, 'action': 'close'}
                    )
                    response.raise_for_status()
                    return {
                        'success': True,
                        'message': f"{arm}臂夹爪已关闭"
                    }

            elif action == 'describe_scene':
                response = self.client.post(
                    f"{self.bridge_url}/vision/describe_scene",
                    json={'use_d455': self.use_d455}  # Use D455 if available
                )
                response.raise_for_status()
                result = response.json()

                return {
                    'success': True,
                    'message': result.get('description', '无法识别场景'),
                    'data': result
                }

            elif action == 'locate_object':
                object_name = params.get('object_name', '')

                response = self.client.post(
                    f"{self.bridge_url}/vision/locate_object",
                    json={
                        'object_name': object_name,
                        'use_d455': self.use_d455  # Use D455 if available
                    }
                )
                response.raise_for_status()
                result = response.json()

                if result.get('success'):
                    position = result.get('position', [])
                    confidence = result.get('confidence', 0)
                    return {
                        'success': True,
                        'message': f"找到 {object_name}，位置: {position}, 置信度: {confidence}%",
                        'data': result,
                        'position': position
                    }
                else:
                    return {
                        'success': False,
                        'message': f"未找到 {object_name}",
                        'data': result
                    }

            elif action == 'identify_objects':
                response = self.client.post(
                    f"{self.bridge_url}/vision/identify_objects",
                    json={'use_d455': self.use_d455}  # Use D455 if available
                )
                response.raise_for_status()
                result = response.json()

                objects = result.get('objects', [])
                if objects:
                    object_list = ', '.join([obj.get('name', 'unknown') for obj in objects])
                    return {
                        'success': True,
                        'message': f"识别到 {len(objects)} 个物体: {object_list}",
                        'data': result
                    }
                else:
                    return {
                        'success': True,
                        'message': "未识别到任何物体",
                        'data': result
                    }

            elif action == 'move_to':
                position = params.get('position')
                arm = params.get('arm', 'right')

                if not position:
                    return {
                        'success': False,
                        'message': "移动失败: 需要提供位置坐标"
                    }
                response = self.client.post(
                    f"{self.bridge_url}/primitives/move_to",
                    json={'arm': arm, 'position': position}
                )
                response.raise_for_status()
                result = response.json()
                return {
                    'success': result.get('success', False),
                    'message': f"{arm}臂" + result.get('message', '移动完成'),
                    'data': result,
                    'arm_used': arm
                }

            elif action == 'home':
                arm = params.get('arm', 'both')

                if arm == 'both':
                    # Return both arms to home
                    left_response = self.client.post(
                        f"{self.bridge_url}/primitives/home",
                        json={'arm': 'left'}
                    )
                    right_response = self.client.post(
                        f"{self.bridge_url}/primitives/home",
                        json={'arm': 'right'}
                    )
                    left_response.raise_for_status()
                    right_response.raise_for_status()
                    return {
                        'success': True,
                        'message': "两只手臂已回到原位"
                    }
                else:
                    response = self.client.post(
                        f"{self.bridge_url}/primitives/home",
                        json={'arm': arm}
                    )
                    response.raise_for_status()
                    return {
                        'success': True,
                        'message': f"{arm}臂已回到原位"
                    }

            elif action == 'bimanual_pick':
                object_name = params.get('object_name', '')

                # First locate the object
                locate_response = self.client.post(
                    f"{self.bridge_url}/vision/locate_object",
                    json={
                        'object_name': object_name,
                        'camera': 'right_hand'
                    }
                )
                locate_response.raise_for_status()
                locate_result = locate_response.json()

                if not locate_result.get('success') or not locate_result.get('position'):
                    return {
                        'success': False,
                        'message': f"无法定位 {object_name}"
                    }

                object_position = locate_result['position']

                # Execute bimanual pick
                response = self.client.post(
                    f"{self.bridge_url}/dualarm/bimanual_pick",
                    json={'object_position': object_position}
                )
                response.raise_for_status()
                result = response.json()

                if result.get('success'):
                    return {
                        'success': True,
                        'message': f"成功用双臂抓取 {object_name}",
                        'data': result
                    }
                else:
                    return {
                        'success': False,
                        'message': f"双臂抓取失败: {result.get('message', '未知错误')}",
                        'data': result
                    }

            elif action == 'handover':
                from_arm = params.get('from_arm', 'right')
                to_arm = params.get('to_arm', 'left')

                response = self.client.post(
                    f"{self.bridge_url}/dualarm/handover",
                    json={
                        'from_arm': from_arm,
                        'to_arm': to_arm
                    }
                )
                response.raise_for_status()
                result = response.json()

                if result.get('success'):
                    return {
                        'success': True,
                        'message': f"成功从{from_arm}臂传递到{to_arm}臂",
                        'data': result
                    }
                else:
                    return {
                        'success': False,
                        'message': f"传递失败: {result.get('message', '未知错误')}",
                        'data': result
                    }

            elif action == 'status':
                response = self.client.get(f"{self.bridge_url}/status")
                response.raise_for_status()
                result = response.json()

                status_msg = f"机器人状态:\n"
                status_msg += f"- 连接: {'是' if result.get('connected') else '否'}\n"
                status_msg += f"- 使能: {'是' if result.get('enabled') else '否'}\n"
                status_msg += f"- 位置: {result.get('current_pose', {}).get('position', 'N/A')}"

                return {
                    'success': True,
                    'message': status_msg,
                    'data': result
                }

            else:
                return {
                    'success': False,
                    'message': f"未知操作: {action}"
                }

        except httpx.HTTPStatusError as e:
            # Extract detailed error message from response
            try:
                error_detail = e.response.json().get('detail', str(e))
            except:
                error_detail = str(e)

            return {
                'success': False,
                'message': f"API 调用失败: {error_detail}"
            }
        except httpx.HTTPError as e:
            return {
                'success': False,
                'message': f"网络错误: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"执行失败: {str(e)}"
            }

    def _direction_to_position(self, direction: str) -> list:
        """Convert direction to approximate position.

        Args:
            direction: Direction string (左/右/前/后/上/下/中 or left/right/front/back/up/down/center)

        Returns:
            [x, y, z] position
        """
        # Base position (center of workspace)
        base = [0.7, 0.0, 0.0]

        offsets = {
            # 中文
            '左': [0.0, 0.3, 0.0],
            '右': [0.0, -0.3, 0.0],
            '前': [0.1, 0.0, 0.0],
            '后': [-0.1, 0.0, 0.0],
            '上': [0.0, 0.0, 0.1],
            '下': [0.0, 0.0, -0.1],
            '中': [0.0, 0.0, 0.0],
            # 英文
            'left': [0.0, 0.3, 0.0],
            'right': [0.0, -0.3, 0.0],
            'front': [0.1, 0.0, 0.0],
            'back': [-0.1, 0.0, 0.0],
            'up': [0.0, 0.0, 0.1],
            'down': [0.0, 0.0, -0.1],
            'center': [0.0, 0.0, 0.0],
        }

        offset = offsets.get(direction, [0.0, 0.0, 0.0])
        return [base[i] + offset[i] for i in range(3)]

    def handle_message(self, user_message: str) -> str:
        """Handle user message with intelligent task routing.

        For query tasks: execute once and return result immediately.
        For manipulation tasks: use dynamic workflow execution.

        Args:
            user_message: Natural language message from user

        Returns:
            Response message to user
        """
        # First, parse the intent to determine task type
        intent = self.parse_intent(user_message)

        if not intent or intent.get('action') == 'unknown':
            return '抱歉，我无法理解您的指令'

        task_type = intent.get('task_type', 'manipulation')
        action = intent.get('action')
        params = intent.get('params', {})

        print(f"[Task Type] {task_type}")
        print(f"[Action] {action}")
        print(f"[Params] {params}")

        # For QUERY tasks: execute directly and return result
        if task_type == 'query':
            print("[Mode] Direct execution (query task)")
            result = self.execute_action(action, params)

            if result.get('success'):
                return result.get('message', '查询完成')
            else:
                return f"查询失败: {result.get('message', '未知错误')}"

        # For MANIPULATION tasks: use dynamic workflow
        else:
            print("[Mode] Dynamic workflow (manipulation task)")
            # Initialize execution context with robot state tracking
            context = {
                'user_message': user_message,
                'initial_intent': intent,  # Store initial intent
                'execution_history': [],
                'current_state': {},
                'robot_state': {
                    'left_arm': {
                        'holding_object': False,
                        'object_name': None,
                        'last_position': None
                    },
                    'right_arm': {
                        'holding_object': False,
                        'object_name': None,
                        'last_position': None
                    }
                },
                'max_iterations': 10,
                'iteration': 0
            }

            # Execute workflow dynamically
            return self._execute_workflow(context)

    def _execute_workflow(self, context: Dict[str, Any]) -> str:
        """Execute workflow by dynamically calling skills.

        LLM decides next skill based on current state.
        """
        while context['iteration'] < context['max_iterations']:
            context['iteration'] += 1

            # 1. Ask LLM what to do next
            next_action = self._get_next_action(context)

            if not next_action:
                return '无法获取下一个动作'

            # Check for completion or error
            action_type = next_action.get('action', 'next')

            if action_type == 'done':
                # Task completed
                return context['current_state'].get(
                    'final_message',
                    '任务完成！'
                )

            if action_type == 'error':
                return next_action.get('message', '任务失败')

            # For 'next' action, must have 'skill' field
            if action_type == 'next':
                if 'skill' not in next_action or not next_action['skill']:
                    print(f"警告: LLM 返回的动作缺少 'skill' 字段: {next_action}")
                    # 尝试重新询问
                    if context['iteration'] < context['max_iterations'] - 1:
                        print("重新询问 LLM...")
                        continue
                    return '无法确定下一个技能'

            # 2. Execute the skill
            skill_name = next_action.get('skill')
            params = next_action.get('params', {})

            print(f"[迭代 {context['iteration']}] 执行: {skill_name}")
            print(f"参数: {params}")

            result = self.execute_action(skill_name, params)

            # 3. Record execution
            context['execution_history'].append({
                'skill': skill_name,
                'params': params,
                'result': result,
                'reasoning': next_action.get('reasoning', '')
            })

            # Debug: 打印结果
            print(f"  结果: {result.get('message', 'N/A')}")

            # 4. Update state
            context['current_state']['last_result'] = result
            context['current_state']['last_skill'] = skill_name

            # Update robot state based on action
            if result.get('success'):
                arm_used = result.get('arm_used')

                # Track pick actions
                if skill_name == 'pick_by_name' and arm_used:
                    context['robot_state'][f'{arm_used}_arm']['holding_object'] = True
                    context['robot_state'][f'{arm_used}_arm']['object_name'] = params.get('object_name')
                    print(f"  [State] {arm_used} arm now holding: {params.get('object_name')}")

                # Track place actions
                elif skill_name == 'place' and arm_used:
                    context['robot_state'][f'{arm_used}_arm']['holding_object'] = False
                    context['robot_state'][f'{arm_used}_arm']['object_name'] = None
                    print(f"  [State] {arm_used} arm released object")

                # Track bimanual pick
                elif skill_name == 'bimanual_pick':
                    context['robot_state']['left_arm']['holding_object'] = True
                    context['robot_state']['right_arm']['holding_object'] = True
                    object_name = params.get('object_name')
                    context['robot_state']['left_arm']['object_name'] = object_name
                    context['robot_state']['right_arm']['object_name'] = object_name
                    print(f"  [State] Both arms now holding: {object_name}")

                # Track handover
                elif skill_name == 'handover':
                    from_arm = params.get('from_arm', 'right')
                    to_arm = params.get('to_arm', 'left')
                    object_name = context['robot_state'][f'{from_arm}_arm']['object_name']
                    context['robot_state'][f'{from_arm}_arm']['holding_object'] = False
                    context['robot_state'][f'{from_arm}_arm']['object_name'] = None
                    context['robot_state'][f'{to_arm}_arm']['holding_object'] = True
                    context['robot_state'][f'{to_arm}_arm']['object_name'] = object_name
                    print(f"  [State] Object transferred from {from_arm} to {to_arm}")

            # Check for failure - count failures
            if not result.get('success'):
                context['current_state']['error'] = result.get('message', '未知错误')
                # Count how many times this skill failed
                failed_count = sum(
                    1 for entry in context['execution_history']
                    if entry['skill'] == skill_name and not entry['result'].get('success')
                )
                context['current_state']['failed_skill'] = skill_name
                context['current_state']['failed_count'] = failed_count
                print(f"  注意: {skill_name} 失败 {failed_count} 次")
            else:
                context['current_state']['last_success'] = result
                context['current_state']['failed_count'] = 0

        return '超过最大迭代次数，任务未完成'

    def _get_next_action(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ask LLM to decide next action based on current context."""
        prompt = self._build_workflow_prompt(context)

        try:
            response = self._call_llm(prompt)
            action = self._parse_llm_response(response)
            return action
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            return {'action': 'error', 'message': f'LLM 错误: {e}'}

    def _build_workflow_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for LLM to decide next action."""
        execution_history = context['execution_history']
        current_state = context['current_state']
        robot_state = context['robot_state']
        initial_intent = context.get('initial_intent', {})

        # Build execution history summary with OUTPUT DATA
        history_text = ""
        if execution_history:
            history_text = "\n执行历史:\n"
            for i, entry in enumerate(execution_history[-3:]):  # Only last 3
                status = "✓ 成功" if entry['result'].get('success') else "✗ 失败"
                history_text += f"{i+1}. {entry['skill']}: {status}\n"

                # Include message
                if entry['result'].get('message'):
                    history_text += f"   信息: {entry['result'].get('message')}\n"

                # IMPORTANT: Include structured output data
                result = entry['result']
                if result.get('success'):
                    output_data = {}

                    # Extract useful output data based on skill type
                    if 'position' in result:
                        output_data['position'] = result['position']
                    if 'arm_used' in result:
                        output_data['arm_used'] = result['arm_used']
                    if 'confidence' in result:
                        output_data['confidence'] = result['confidence']
                    if 'object_name' in result:
                        output_data['object_name'] = result['object_name']

                    if output_data:
                        history_text += f"   输出数据: {output_data}\n"

                        # Suggest how to use this data
                        skill = entry['skill']
                        if skill == 'locate_object' and 'position' in output_data:
                            history_text += f"   → 可用于: pick(arm='auto', position={output_data['position']})\n"
                        elif skill == 'pick_by_name' and 'arm_used' in output_data:
                            history_text += f"   → 可用于: place(arm='{output_data['arm_used']}', ...) 或 place_by_name(arm='{output_data['arm_used']}', ...)\n"

        # Build current state summary
        state_text = ""
        if current_state.get('error'):
            state_text += f"\n最后的错误: {current_state['error']}"
        if current_state.get('last_success'):
            state_text += f"\n上一个成功的动作: {current_state.get('last_skill')}"

        # Build robot state summary
        robot_state_text = "\n当前机器人状态:\n"
        left_holding = robot_state['left_arm']['holding_object']
        right_holding = robot_state['right_arm']['holding_object']
        robot_state_text += f"- 左臂: {'持有物体' if left_holding else '空闲'}"
        if left_holding:
            robot_state_text += f" ({robot_state['left_arm']['object_name']})"
        robot_state_text += f"\n- 右臂: {'持有物体' if right_holding else '空闲'}"
        if right_holding:
            robot_state_text += f" ({robot_state['right_arm']['object_name']})"

        # Add initial intent context
        initial_intent_text = ""
        if initial_intent:
            initial_intent_text = f"\n初始意图: {initial_intent.get('action')} with params {initial_intent.get('params')}"

        prompt = f"""You are a robot control assistant for a dual-arm Baxter robot. Your task is to decide what the robot should do NEXT.

User's goal: "{context['user_message']}"{initial_intent_text}
{history_text}{state_text}{robot_state_text}

Available skills (choose ONE):
- pick {{"arm": "left"/"right"/"auto", "position": [x, y, z]}} - Pick at known position
- pick_by_name {{"object_name": "物体名字", "arm": "left"/"right"/"auto"}} - Locate and pick
- place {{"direction": "left"/"right"/"front"/"back"/"center", "arm": "left"/"right"/"auto"}} - Place at direction
- place_by_name {{"target_object_name": "目标物体", "relative_position": "next_to"/"on_top"/"behind"/"in_front", "arm": "left"/"right"/"auto"}} - Place relative to object (RECOMMENDED)
- move_to {{"position": [x, y, z], "arm": "left"/"right"}}
- gripper_open {{"arm": "left"/"right"/"both"}}
- gripper_close {{"arm": "left"/"right"/"both"}}
- home {{"arm": "left"/"right"/"both"}}
- bimanual_pick {{"object_name": "物体名字"}}
- handover {{"from_arm": "left"/"right", "to_arm": "left"/"right"}}

CRITICAL: Use output data from previous skills!
- If locate_object returned position=[x,y,z], use: pick(position=[x,y,z], arm="auto")
- If pick returned arm_used="right", use: place(arm="right", ...) or place_by_name(arm="right", ...)
- DO NOT call pick_by_name if you already have the position!

CRITICAL: Choose the right place action:
- If user specifies target object (e.g., "放到黄色方块上"), use: place_by_name(target_object_name="黄色方块", relative_position="on_top")
- If user only specifies direction (e.g., "放到左边"), use: place(direction="左")

Decision rules:
1. Check if user's goal is COMPLETED:
   - For "识别坐标" task: if locate_object succeeded, goal is DONE
   - For pick task: if object is picked and lifted, set action="done"
   - For place task: if object is placed and arm retracted, set action="done"
   - For move task: if arm reached target position, set action="done"
   - For home task: if arm(s) returned to home, set action="done"
   - For handover task: if object transferred successfully, set action="done"

2. If same action failed 2+ times, try different approach or set action="error"

3. Use output data from previous step as input to next step

4. Consider which arm is holding objects when deciding next action

5. CRITICAL: If place or place_by_name fails, DO NOT retry pick!
   - If place_by_name fails (cannot locate target object), set action="error"
   - DO NOT pick the object again if it's already in hand
   - Report the error to user instead

6. Always return VALID JSON with these REQUIRED fields:
   - action: "next" or "done" or "error"
   - skill: skill name (if action="next")
   - params: skill parameters (if action="next") - USE DATA FROM PREVIOUS STEP!
   - reasoning: brief explanation (always required)

IMPORTANT: If the last action succeeded and completed the user's goal, set action="done"!

RETURN ONLY JSON, no other text:
"""
        return prompt
        return prompt


# For testing
if __name__ == "__main__":
    import sys

    # Get API key from command line or environment
    api_key = sys.argv[1] if len(sys.argv) > 1 else os.getenv('QWEN_API_KEY')

    if not api_key:
        print("Error: Please provide Qwen API key")
        print("Usage: python baxter_claw_plugin.py <api_key>")
        print("Or set QWEN_API_KEY environment variable")
        sys.exit(1)

    plugin = BaxterClawPlugin(llm_api_key=api_key)

    # Test cases
    test_messages = [
        "帮我拿一下红色的杯子",
        "pick the white box",
        "grab a blue bottle",
        "把它放到左边",
        "place it on the right",
        "打开夹爪",
        "open gripper",
        "看看桌上有什么",
        "what do you see",
        "回到原位",
        "home",
        "查看状态",
    ]

    print("Baxter-Claw OpenClaw Plugin 测试 (LLM-based Intent Recognition)\n")
    print("="*60)
    print(f"LLM Provider: {plugin.llm_provider}")
    print(f"LLM Model: {plugin.llm_models[plugin.llm_provider]}")
    print("="*60)

    for msg in test_messages:
        print(f"\n用户: {msg}")
        intent = plugin.parse_intent(msg)
        print(f"意图: {intent['action']}")
        print(f"参数: {intent['params']}")
        print(f"置信度: {intent['confidence']}")

        # Uncomment to test actual execution
        # response = plugin.handle_message(msg)
        # print(f"回复: {response}")