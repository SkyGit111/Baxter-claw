#!/usr/bin/env python
"""
测试 LLM 意图识别功能

使用方法：
1. 确保设置了 QWEN_API_KEY 环境变量
2. 运行: python test_llm_intent.py
"""

import sys
import os
sys.path.insert(0, '/home/cothink/Baxter-claw')

from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin


def test_intent_recognition():
    """测试 LLM 意图识别"""

    # 获取 API key
    api_key = os.getenv('QWEN_API_KEY', 'sk-bd990626c84a4142b9581f13c5317522')

    if not api_key:
        print("错误: 请设置 QWEN_API_KEY 环境变量")
        return

    # 初始化插件
    print("初始化 Baxter-Claw 插件 (LLM 模式)...")
    plugin = BaxterClawPlugin(
        bridge_url="http://localhost:8420",
        llm_provider="qwen",
        llm_api_key=api_key
    )

    print(f"LLM Provider: {plugin.llm_provider}")
    print(f"LLM Model: {plugin.llm_models[plugin.llm_provider]}")
    print()

    # 测试用例
    test_cases = [
        # 中文抓取命令
        "帮我拿一下红色的杯子",
        "抓住那个蓝色的瓶子",
        "取一下细长的白色盒子",

        # 英文抓取命令
        "pick the white box",
        "grab the red cup",
        "get me the blue bottle",

        # 中文放置命令
        "把它放到左边",
        "放在右边",
        "放到前面",

        # 英文放置命令
        "place it on the left",
        "put it on the right",
        "place it in the center",

        # 夹爪控制
        "打开夹爪",
        "open gripper",
        "关闭夹爪",
        "close gripper",

        # 场景理解
        "看看桌上有什么",
        "what do you see",
        "识别一下物体",
        "describe the scene",

        # 其他命令
        "回到原位",
        "home",
        "查看状态",
        "status",
    ]

    print("="*70)
    print("开始测试 LLM 意图识别")
    print("="*70)
    print()

    success_count = 0
    total_count = len(test_cases)

    for i, message in enumerate(test_cases, 1):
        print(f"[{i}/{total_count}] 用户输入: {message}")

        try:
            # 解析意图
            intent = plugin.parse_intent(message)

            # 显示结果
            print(f"  ✓ 识别成功")
            print(f"    动作: {intent['action']}")
            print(f"    参数: {intent['params']}")
            print(f"    置信度: {intent['confidence']:.2f}")

            if intent['action'] != 'unknown':
                success_count += 1
            else:
                print(f"    ⚠ 警告: 未识别的命令")

        except Exception as e:
            print(f"  ✗ 识别失败: {e}")

        print()

    # 统计结果
    print("="*70)
    print(f"测试完成: {success_count}/{total_count} 成功")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    print("="*70)


if __name__ == "__main__":
    test_intent_recognition()