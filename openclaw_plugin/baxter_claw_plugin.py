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
        llm_api_key: Optional[str] = None
    ):
        """Initialize plugin.

        Args:
            bridge_url: URL of Baxter-Claw Bridge Server
            llm_provider: LLM provider for intent recognition ('qwen', 'openai', 'claude')
            llm_api_key: API key for LLM (or use environment variable)
        """
        self.bridge_url = bridge_url
        self.client = httpx.Client(timeout=30.0)

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

Available actions:
1. pick_by_name - Pick up an object by name
   Parameters:
   - object_name (string, e.g., "red cup", "blue box", "红色杯子")
   - arm (string: "left"/"right"/"auto", default: "auto" - will choose based on object position)

2. place - Place the held object at a location
   Parameters:
   - direction (string: "left"/"right"/"front"/"back"/"up"/"down"/"center" or "左"/"右"/"前"/"后"/"上"/"下"/"中")
   - arm (string: "left"/"right"/"auto", default: "auto")

3. move_to - Move arm to a position
   Parameters:
   - position (list: [x, y, z])
   - arm (string: "left"/"right", required)

4. gripper_open - Open the gripper
   Parameters:
   - arm (string: "left"/"right"/"both", default: "right")

5. gripper_close - Close the gripper
   Parameters:
   - arm (string: "left"/"right"/"both", default: "right")

6. describe_scene - Describe what the robot sees
   Parameters: none

7. home - Return to home position
   Parameters:
   - arm (string: "left"/"right"/"both", default: "both")

8. status - Check robot status
   Parameters: none

9. bimanual_pick - Pick large object with both arms
   Parameters:
   - object_name (string)

10. handover - Hand over object from one arm to another
    Parameters:
    - from_arm (string: "left"/"right")
    - to_arm (string: "left"/"right")

Arm selection rules:
- If user specifies arm explicitly (e.g., "用左手", "with right arm"), use that arm
- If user says "both hands" or "两只手", use bimanual actions
- If arm is "auto", the system will choose based on object position (closer arm)
- For handover, identify which arm currently holds the object

Respond ONLY with a JSON object in this exact format:
{{
    "action": "action_name",
    "params": {{"param_name": "param_value"}},
    "confidence": 0.0-1.0
}}

Examples:
- "帮我拿一下红色的杯子" -> {{"action": "pick_by_name", "params": {{"object_name": "红色的杯子", "arm": "auto"}}, "confidence": 0.95}}
- "用左手拿白色盒子" -> {{"action": "pick_by_name", "params": {{"object_name": "白色盒子", "arm": "left"}}, "confidence": 0.95}}
- "pick the white box with right arm" -> {{"action": "pick_by_name", "params": {{"object_name": "white box", "arm": "right"}}, "confidence": 0.95}}
- "用两只手拿那个大箱子" -> {{"action": "bimanual_pick", "params": {{"object_name": "大箱子"}}, "confidence": 0.9}}
- "把它放到左边" -> {{"action": "place", "params": {{"direction": "左", "arm": "auto"}}, "confidence": 0.9}}
- "右臂放到右边" -> {{"action": "place", "params": {{"direction": "右", "arm": "right"}}, "confidence": 0.9}}
- "打开左边夹爪" -> {{"action": "gripper_open", "params": {{"arm": "left"}}, "confidence": 0.95}}
- "open both grippers" -> {{"action": "gripper_open", "params": {{"arm": "both"}}, "confidence": 0.95}}
- "把物体从右手传到左手" -> {{"action": "handover", "params": {{"from_arm": "right", "to_arm": "left"}}, "confidence": 0.9}}
- "两只手都回原位" -> {{"action": "home", "params": {{"arm": "both"}}, "confidence": 0.95}}
- "看看桌上有什么" -> {{"action": "describe_scene", "params": {{}}, "confidence": 0.9}}

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
        # Baxter coordinate system: positive y is to the left, negative y is to the right
        # If y > 0, object is on left side, use left arm
        # If y < 0, object is on right side, use right arm
        # If y ≈ 0, use right arm as default
        y = position[1] if len(position) > 1 else 0.0

        if y > 0.05:  # Object on left side (threshold 5cm)
            return 'left'
        elif y < -0.05:  # Object on right side
            return 'right'
        else:  # Object in center, default to right
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
            if action == 'pick_by_name':
                object_name = params.get('object_name', '')
                arm = params.get('arm', 'auto')

                # If arm is 'auto', first locate the object to determine which arm to use
                if arm == 'auto':
                    # Locate object first
                    locate_response = self.client.post(
                        f"{self.bridge_url}/vision/locate_object",
                        json={
                            'object_name': object_name,
                            'camera': 'right_hand'  # Use right hand camera for initial scan
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

                # Determine which camera to use based on arm
                camera = f"{arm}_hand"

                response = self.client.post(
                    f"{self.bridge_url}/vision/pick_by_name",
                    json={
                        'arm': arm,
                        'object_name': object_name,
                        'camera': camera
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
                # For now, default to right arm (state tracking will improve this)
                if arm == 'auto':
                    arm = 'right'  # TODO: Use state tracking to determine which arm holds object

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
                    json={'camera': 'right_hand'}
                )
                response.raise_for_status()
                result = response.json()

                return {
                    'success': True,
                    'message': result.get('description', '无法识别场景'),
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
        """Handle user message with dynamic skill execution.

        Uses LLM to dynamically decide next skill after each execution.

        Args:
            user_message: Natural language message from user

        Returns:
            Response message to user
        """
        # Initialize execution context with robot state tracking
        context = {
            'user_message': user_message,
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

        # Build execution history summary
        history_text = ""
        if execution_history:
            history_text = "\n执行历史:\n"
            for i, entry in enumerate(execution_history[-3:]):  # Only last 3
                status = "✓ 成功" if entry['result'].get('success') else "✗ 失败"
                history_text += f"{i+1}. {entry['skill']}: {status}\n"
                if entry['result'].get('message'):
                    history_text += f"   信息: {entry['result'].get('message')}\n"

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

        prompt = f"""You are a robot control assistant for a dual-arm Baxter robot. Your task is to decide what the robot should do NEXT.

User's goal: "{context['user_message']}"
{history_text}{state_text}{robot_state_text}

Available skills (choose ONE):
- pick_by_name {{"object_name": "物体名字", "arm": "left"/"right"/"auto"}}
- place {{"direction": "left"/"right"/"front"/"back"/"center", "arm": "left"/"right"/"auto"}}
- move_to {{"position": [x, y, z], "arm": "left"/"right"}}
- gripper_open {{"arm": "left"/"right"/"both"}}
- gripper_close {{"arm": "left"/"right"/"both"}}
- describe_scene {{}}
- home {{"arm": "left"/"right"/"both"}}
- status {{}}
- bimanual_pick {{"object_name": "物体名字"}}
- handover {{"from_arm": "left"/"right", "to_arm": "left"/"right"}}

Decision rules:
1. If user's goal is DONE, set action="done"
2. If same action failed 2+ times, try different approach or action="error"
3. Consider which arm is holding objects when deciding next action
4. Use "auto" for arm parameter to let system choose based on object position
5. Use bimanual_pick for large objects or when user says "both hands"
6. Always return VALID JSON with these REQUIRED fields:
   - action: "next" or "done" or "error"
   - skill: skill name (if action="next")
   - params: skill parameters
   - reasoning: brief explanation

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