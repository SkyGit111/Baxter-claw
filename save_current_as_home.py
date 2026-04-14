#!/usr/bin/env python3
"""
保存当前位姿为新的Home位姿

使用方法:
    python save_current_as_home.py
"""

import sys
import httpx
import json

def get_current_positions():
    """获取双臂当前关节角度"""
    client = httpx.Client(base_url="http://localhost:8420", timeout=10.0)

    positions = {}

    for arm in ['left', 'right']:
        try:
            response = client.get(f"/status?arm={arm}")
            if response.status_code == 200:
                data = response.json()
                positions[arm] = data['joint_angles']
                print(f"✓ 获取{arm}臂位姿成功")
            else:
                print(f"✗ 获取{arm}臂位姿失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"✗ 错误: {e}")
            return None

    return positions

def format_home_positions(positions):
    """格式化为Python代码"""
    code = """        # Predefined home positions for each arm
        # Updated to current comfortable positions (auto-generated)
        self.home_positions = {
            'right': {
"""

    # Right arm
    for joint, angle in sorted(positions['right'].items()):
        code += f"                '{joint}': {angle:.6f},\n"

    code += """            },
            'left': {
"""

    # Left arm
    for joint, angle in sorted(positions['left'].items()):
        code += f"                '{joint}': {angle:.6f},\n"

    code += """            }
        }"""

    return code

def main():
    print("="*60)
    print("保存当前位姿为Home位姿")
    print("="*60)
    print()

    # 检查Bridge Server
    try:
        client = httpx.Client(base_url="http://localhost:8420", timeout=5.0)
        response = client.get("/")
        if response.status_code != 200:
            print("✗ Bridge Server未运行")
            print("  请先启动: ./start_bridge.sh")
            return 1
    except:
        print("✗ 无法连接到Bridge Server")
        print("  请先启动: ./start_bridge.sh")
        return 1

    print("✓ Bridge Server运行中")
    print()

    # 获取当前位姿
    print("获取当前双臂位姿...")
    positions = get_current_positions()

    if not positions:
        print("\n✗ 获取位姿失败")
        return 1

    print()
    print("当前位姿:")
    print("-" * 60)

    # 显示右臂
    print("\n右臂:")
    for joint, angle in sorted(positions['right'].items()):
        print(f"  {joint}: {angle:.6f} rad")

    # 显示左臂
    print("\n左臂:")
    for joint, angle in sorted(positions['left'].items()):
        print(f"  {joint}: {angle:.6f} rad")

    print()
    print("-" * 60)
    print()

    # 确认
    response = input("是否将此位姿保存为新的Home位姿? (y/n): ").strip().lower()
    if response != 'y':
        print("\n已取消")
        return 0

    # 生成代码
    code = format_home_positions(positions)

    # 保存到文件
    output_file = "new_home_positions.txt"
    with open(output_file, 'w') as f:
        f.write("# 将以下代码替换到 bridge/primitives.py 中的 home_positions 定义\n\n")
        f.write(code)
        f.write("\n")

    print()
    print(f"✓ 已保存到: {output_file}")
    print()
    print("下一步:")
    print("1. 查看文件内容: cat new_home_positions.txt")
    print("2. 手动编辑 bridge/primitives.py，替换 home_positions 定义")
    print("3. 重启Bridge Server: pkill -f bridge.server && ./start_bridge.sh")
    print()
    print("或者直接运行:")
    print("  python update_home_positions.py")
    print()

    return 0

if __name__ == '__main__':
    sys.exit(main())
