#!/usr/bin/env python3
"""
Test script for dual-arm support in Baxter-Claw OpenClaw Plugin.

Tests the enhanced LLM intent recognition and arm selection logic.
"""

import sys
import os
from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin


def test_intent_parsing():
    """Test LLM intent parsing for dual-arm commands."""

    # Get API key
    api_key = sys.argv[1] if len(sys.argv) > 1 else os.getenv('QWEN_API_KEY')

    if not api_key:
        print("Error: Please provide Qwen API key")
        print("Usage: python test_dual_arm_plugin.py <api_key>")
        print("Or set QWEN_API_KEY environment variable")
        sys.exit(1)

    plugin = BaxterClawPlugin(llm_api_key=api_key)

    # Test cases for dual-arm support
    test_cases = [
        # Auto arm selection
        {
            "message": "帮我拿一下红色的杯子",
            "expected_action": "pick_by_name",
            "expected_params": {"object_name": "红色的杯子", "arm": "auto"}
        },
        {
            "message": "pick the white box",
            "expected_action": "pick_by_name",
            "expected_params": {"object_name": "white box", "arm": "auto"}
        },

        # Explicit left arm
        {
            "message": "用左手拿蓝色盒子",
            "expected_action": "pick_by_name",
            "expected_params": {"object_name": "蓝色盒子", "arm": "left"}
        },
        {
            "message": "pick the red cup with left arm",
            "expected_action": "pick_by_name",
            "expected_params": {"object_name": "red cup", "arm": "left"}
        },

        # Explicit right arm
        {
            "message": "用右手拿绿色瓶子",
            "expected_action": "pick_by_name",
            "expected_params": {"object_name": "绿色瓶子", "arm": "right"}
        },
        {
            "message": "右臂放到前面",
            "expected_action": "place",
            "expected_params": {"direction": "前", "arm": "right"}
        },

        # Bimanual operations
        {
            "message": "用两只手拿那个大箱子",
            "expected_action": "bimanual_pick",
            "expected_params": {"object_name": "大箱子"}
        },
        {
            "message": "pick the large box with both hands",
            "expected_action": "bimanual_pick",
            "expected_params": {"object_name": "large box"}
        },

        # Handover
        {
            "message": "把物体从右手传到左手",
            "expected_action": "handover",
            "expected_params": {"from_arm": "right", "to_arm": "left"}
        },
        {
            "message": "transfer from left to right",
            "expected_action": "handover",
            "expected_params": {"from_arm": "left", "to_arm": "right"}
        },

        # Gripper control
        {
            "message": "打开左边夹爪",
            "expected_action": "gripper_open",
            "expected_params": {"arm": "left"}
        },
        {
            "message": "open both grippers",
            "expected_action": "gripper_open",
            "expected_params": {"arm": "both"}
        },
        {
            "message": "关闭右边夹爪",
            "expected_action": "gripper_close",
            "expected_params": {"arm": "right"}
        },

        # Home position
        {
            "message": "左臂回原位",
            "expected_action": "home",
            "expected_params": {"arm": "left"}
        },
        {
            "message": "两只手都回到原位",
            "expected_action": "home",
            "expected_params": {"arm": "both"}
        },
        {
            "message": "return both arms to home",
            "expected_action": "home",
            "expected_params": {"arm": "both"}
        },
    ]

    print("=" * 80)
    print("Baxter-Claw 双臂支持测试")
    print("=" * 80)
    print(f"LLM Provider: {plugin.llm_provider}")
    print(f"LLM Model: {plugin.llm_models[plugin.llm_provider]}")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"测试 {i}/{len(test_cases)}: {test['message']}")
        print("-" * 80)

        try:
            # Parse intent
            intent = plugin.parse_intent(test['message'])

            # Check action
            action_match = intent['action'] == test['expected_action']

            # Check params (flexible matching)
            params_match = True
            for key, expected_value in test['expected_params'].items():
                actual_value = intent['params'].get(key)
                if actual_value != expected_value:
                    params_match = False
                    print(f"  ⚠️  参数不匹配: {key}")
                    print(f"     期望: {expected_value}")
                    print(f"     实际: {actual_value}")

            # Print results
            if action_match and params_match:
                print(f"  ✅ 通过")
                print(f"     动作: {intent['action']}")
                print(f"     参数: {intent['params']}")
                print(f"     置信度: {intent['confidence']}")
                passed += 1
            else:
                print(f"  ❌ 失败")
                print(f"     期望动作: {test['expected_action']}")
                print(f"     实际动作: {intent['action']}")
                print(f"     期望参数: {test['expected_params']}")
                print(f"     实际参数: {intent['params']}")
                failed += 1

        except Exception as e:
            print(f"  ❌ 错误: {e}")
            failed += 1

        print()

    # Summary
    print("=" * 80)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print(f"成功率: {passed / len(test_cases) * 100:.1f}%")
    print("=" * 80)


def test_arm_selection():
    """Test automatic arm selection based on position."""

    plugin = BaxterClawPlugin()

    print("\n" + "=" * 80)
    print("测试基于位置的自动臂选择")
    print("=" * 80)
    print()

    test_positions = [
        ([0.6, 0.2, 0.1], "left", "物体在左侧 (y=0.2)"),
        ([0.6, -0.2, 0.1], "right", "物体在右侧 (y=-0.2)"),
        ([0.6, 0.0, 0.1], "right", "物体在中间 (y=0.0)"),
        ([0.7, 0.15, 0.15], "left", "物体在左侧 (y=0.15)"),
        ([0.7, -0.15, 0.15], "right", "物体在右侧 (y=-0.15)"),
        ([0.5, 0.03, 0.1], "right", "物体接近中间 (y=0.03)"),
    ]

    for position, expected_arm, description in test_positions:
        actual_arm = plugin._choose_arm_by_position(position)
        status = "✅" if actual_arm == expected_arm else "❌"
        print(f"{status} {description}")
        print(f"   位置: {position}")
        print(f"   期望: {expected_arm}, 实际: {actual_arm}")
        print()


if __name__ == "__main__":
    print("Baxter-Claw 双臂支持测试脚本")
    print()

    # Test arm selection logic (no API key needed)
    test_arm_selection()

    # Test intent parsing (requires API key)
    if len(sys.argv) > 1 or os.getenv('QWEN_API_KEY'):
        test_intent_parsing()
    else:
        print("\n提示: 提供 API key 以测试 LLM 意图识别")
        print("用法: python test_dual_arm_plugin.py <api_key>")
        print("或设置 QWEN_API_KEY 环境变量")
