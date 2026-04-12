#!/usr/bin/env python
"""
简单的命令行测试工具，用于测试 Baxter-Claw OpenClaw 插件

使用方法：
1. 确保 Bridge Server 正在运行
2. 运行此脚本: python test_plugin.py
3. 输入自然语言命令
"""

import sys
sys.path.insert(0, '/home/cothink/Baxter-claw')

from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin


def main():
    print("="*60)
    print("Baxter-Claw OpenClaw 插件测试")
    print("="*60)
    print()
    print("连接到 Bridge Server...")

    try:
        plugin = BaxterClawPlugin(bridge_url="http://localhost:8420")
        print("✓ 连接成功")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        print("\n请确保 Bridge Server 正在运行:")
        print("  python -m bridge.server --config config/baxter.yaml")
        return 1

    print()
    print("你可以输入以下命令:")
    print("  - 帮我拿一下红色的杯子")
    print("  - 把它放到左边")
    print("  - 打开夹爪")
    print("  - 看看桌上有什么")
    print("  - 回到原位")
    print("  - 查看状态")
    print()
    print("输入 'quit' 或 'exit' 退出")
    print("="*60)
    print()

    while True:
        try:
            user_input = input("你: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', '退出']:
                print("\n再见！")
                break

            # Parse intent first to show what was understood
            intent = plugin.parse_intent(user_input)
            print(f"[识别] 动作: {intent['action']}, 参数: {intent['params']}")

            # Execute and get response
            response = plugin.handle_message(user_input)
            print(f"机器人: {response}")
            print()

        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"错误: {e}")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())