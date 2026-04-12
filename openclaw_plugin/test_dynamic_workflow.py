#!/usr/bin/env python
"""
测试动态工作流执行

使用方法:
1. 确保 Bridge Server 正在运行
2. 设置 QWEN_API_KEY 环境变量
3. 运行: python test_dynamic_workflow.py
"""

import sys
import os
import asyncio

sys.path.insert(0, '/home/cothink/Baxter-claw')

from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin


def test_dynamic_workflow():
    """测试动态工作流执行"""

    # 获取 API key
    api_key = os.getenv('QWEN_API_KEY', 'sk-bd990626c84a4142b9581f13c5317522')

    if not api_key:
        print("错误: 请设置 QWEN_API_KEY 环境变量")
        return

    # 初始化插件
    print("初始化 Baxter-Claw 插件 (动态工作流模式)...")
    plugin = BaxterClawPlugin(
        bridge_url="http://localhost:8420",
        llm_provider="qwen",
        llm_api_key=api_key
    )

    print(f"LLM Provider: {plugin.llm_provider}")
    print(f"Bridge URL: {plugin.bridge_url}")
    print()

    # 测试用例
    test_cases = [
        # 简单单步命令
        "打开夹爪",
        "查看状态",

        # 复合多步命令（需要 Bridge Server 运行）
        "帮我拿起红色的杯子",
        # "拿起白色盒子并放到左边",
        # "找一下蓝色瓶子然后拿起来",
    ]

    print("="*70)
    print("开始测试动态工作流")
    print("="*70)
    print()

    for i, user_message in enumerate(test_cases, 1):
        print(f"\n[测试 {i}/{len(test_cases)}] 用户输入: {user_message}")
        print("-" * 70)

        try:
            # 执行工作流
            response = plugin.handle_message(user_message)

            print(f"\n最终响应: {response}")
            print("-" * 70)

        except Exception as e:
            print(f"\n错误: {e}")
            import traceback
            traceback.print_exc()
            print("-" * 70)

    print("\n" + "="*70)
    print("测试完成")
    print("="*70)


if __name__ == "__main__":
    test_dynamic_workflow()