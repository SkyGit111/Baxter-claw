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
        prompt = f"""You are a robot control assistant. Parse the following user command and identify the intent and parameters.

User command: "{user_message}"

Available actions:
1. pick_by_name - Pick up an object by name
   Parameters: object_name (string, e.g., "red cup", "blue box", "红色杯子")

2. place - Place the held object at a location
   Parameters: direction (string: "left"/"right"/"front"/"back"/"up"/"down"/"center" or "左"/"右"/"前"/"后"/"上"/"下"/"中")

3. gripper_open - Open the gripper
   Parameters: none

4. gripper_close - Close the gripper
   Parameters: none

5. describe_scene - Describe what the robot sees
   Parameters: none

6. home - Return to home position
   Parameters: none

7. status - Check robot status
   Parameters: none

Respond ONLY with a JSON object in this exact format:
{{
    "action": "action_name",
    "params": {{"param_name": "param_value"}},
    "confidence": 0.0-1.0
}}

Examples:
- "帮我拿一下红色的杯子" -> {{"action": "pick_by_name", "params": {{"object_name": "红色的杯子"}}, "confidence": 0.95}}
- "pick the white box" -> {{"action": "pick_by_name", "params": {{"object_name": "white box"}}, "confidence": 0.95}}
- "把它放到左边" -> {{"action": "place", "params": {{"direction": "左"}}, "confidence": 0.9}}
- "place it on the right" -> {{"action": "place", "params": {{"direction": "right"}}, "confidence": 0.9}}
- "打开夹爪" -> {{"action": "gripper_open", "params": {{}}, "confidence": 0.95}}
- "open gripper" -> {{"action": "gripper_open", "params": {{}}, "confidence": 0.95}}
- "看看桌上有什么" -> {{"action": "describe_scene", "params": {{}}, "confidence": 0.9}}
- "what do you see" -> {{"action": "describe_scene", "params": {{}}, "confidence": 0.9}}

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
                response = self.client.post(
                    f"{self.bridge_url}/vision/pick_by_name",
                    json={
                        'arm': 'right',
                        'object_name': object_name,
                        'camera': 'right_hand'
                    }
                )
                response.raise_for_status()
                result = response.json()

                if result.get('success'):
                    return {
                        'success': True,
                        'message': f"成功抓取 {object_name}",
                        'data': result
                    }
                else:
                    return {
                        'success': False,
                        'message': f"无法抓取 {object_name}: {result.get('message', '未知错误')}",
                        'data': result
                    }

            elif action == 'place':
                direction = params.get('direction', '前')
                # Convert direction to coordinates
                position = self._direction_to_position(direction)

                response = self.client.post(
                    f"{self.bridge_url}/primitives/place",
                    json={'arm': 'right', 'position': position}
                )
                response.raise_for_status()
                result = response.json()

                return {
                    'success': result.get('success', False),
                    'message': f"已放置到{direction}边",
                    'data': result
                }

            elif action == 'gripper_open':
                response = self.client.post(
                    f"{self.bridge_url}/gripper",
                    json={'arm': 'right', 'action': 'open'}
                )
                response.raise_for_status()
                return {
                    'success': True,
                    'message': "夹爪已打开"
                }

            elif action == 'gripper_close':
                response = self.client.post(
                    f"{self.bridge_url}/gripper",
                    json={'arm': 'right', 'action': 'close'}
                )
                response.raise_for_status()
                return {
                    'success': True,
                    'message': "夹爪已关闭"
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

            elif action == 'home':
                response = self.client.post(
                    f"{self.bridge_url}/primitives/home",
                    json={'arm': 'right'}
                )
                response.raise_for_status()
                return {
                    'success': True,
                    'message': "已回到原位"
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
        # Initialize execution context
        context = {
            'user_message': user_message,
            'execution_history': [],
            'current_state': {},
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

            # 4. Update state
            context['current_state']['last_result'] = result
            context['current_state']['last_skill'] = skill_name

            # Check for failure
            if not result.get('success'):
                context['current_state']['error'] = result.get('message', '未知错误')
            else:
                context['current_state']['last_success'] = result

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

        prompt = f"""You are a robot control assistant. Your task is to decide what the robot should do NEXT.

User's goal: "{context['user_message']}"
{history_text}{state_text}

Available skills (choose ONE):
- pick_by_name {{"object_name": "物体名字"}}
- place {{"direction": "left"/"right"/"front"/"back"/"center"}}
- move_to {{"position": [x, y, z]}}
- gripper_open {{}}
- gripper_close {{}}
- describe_scene {{}}
- home {{}}
- status {{}}

Decision rules:
1. If user's goal is DONE, set action="done"
2. If same action failed 2+ times, try different approach or action="error"
3. Always return VALID JSON with these REQUIRED fields:
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