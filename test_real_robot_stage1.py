#!/usr/bin/env python3
"""
真实 Baxter 机器人测试脚本 - 阶段 1：基础功能
使用精确坐标，不依赖视觉
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8420"

def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def wait_for_user(message="按 Enter 继续，或输入 'skip' 跳过，'quit' 退出: "):
    """等待用户确认"""
    response = input(message).strip().lower()
    if response == 'quit':
        print("测试终止")
        sys.exit(0)
    return response != 'skip'

def test_connection():
    """测试连接"""
    print_section("测试 1: 连接检查")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        print(f"✓ Bridge Server 响应正常")
        print(f"  Connected: {data.get('connected')}")
        print(f"  Healthy: {data.get('healthy')}")
        return True
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False

def test_status():
    """测试状态查询"""
    print_section("测试 2: 状态查询")
    try:
        response = requests.get(f"{BASE_URL}/status")
        data = response.json()
        print(f"✓ 状态查询成功")
        print(f"  Connected: {data.get('connected')}")
        print(f"  Enabled: {data.get('enabled')}")
        print(f"  Arm: {data.get('arm')}")
        print(f"  Joint angles: {json.dumps(data.get('joint_angles'), indent=4)}")
        print(f"  Endpoint pose: {data.get('endpoint_pose')}")
        return True
    except Exception as e:
        print(f"✗ 状态查询失败: {e}")
        return False

def test_enable():
    """测试启用机器人"""
    print_section("测试 3: 启用机器人")
    print("⚠️  警告：这将启用机器人电机")
    print("   确保：")
    print("   1. 工作空间内无人")
    print("   2. 紧急停止按钮可用")
    print("   3. 机器人处于安全位置")

    if not wait_for_user():
        return False

    try:
        response = requests.post(f"{BASE_URL}/enable")
        data = response.json()
        print(f"✓ 机器人已启用")
        print(f"  Message: {data.get('message')}")
        return True
    except Exception as e:
        print(f"✗ 启用失败: {e}")
        return False

def test_home():
    """测试回到初始位置"""
    print_section("测试 4: 回到初始位置")
    print("这将移动右臂到预定义的安全位置")

    if not wait_for_user():
        return False

    try:
        response = requests.post(
            f"{BASE_URL}/primitives/home",
            json={"arm": "right"}
        )
        data = response.json()
        if data.get('success'):
            print(f"✓ 回到初始位置成功")
            print(f"  Message: {data.get('message')}")
            return True
        else:
            print(f"✗ 回到初始位置失败")
            print(f"  Message: {data.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_small_movement():
    """测试小幅度移动"""
    print_section("测试 5: 小幅度移动")
    print("这将移动右臂到一个接近当前位置的点")
    print("目标位置: [0.6, -0.3, 0.2]")
    print("这是一个保守的、安全的位置")

    if not wait_for_user():
        return False

    try:
        response = requests.post(
            f"{BASE_URL}/primitives/move_to",
            json={
                "arm": "right",
                "position": [0.6, -0.3, 0.2],
                "orientation": [0, 0, 0]
            }
        )
        data = response.json()
        if data.get('success'):
            print(f"✓ 移动成功")
            print(f"  Message: {data.get('message')}")
            print(f"  Final position: {data.get('final_position')}")
            return True
        else:
            print(f"✗ 移动失败")
            print(f"  Message: {data.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_gripper_open():
    """测试打开夹爪"""
    print_section("测试 6: 打开夹爪")

    if not wait_for_user():
        return False

    try:
        response = requests.post(
            f"{BASE_URL}/gripper/open",
            json={"arm": "right"}
        )
        data = response.json()
        if data.get('success'):
            print(f"✓ 夹爪打开成功")
            return True
        else:
            print(f"✗ 夹爪打开失败")
            print(f"  Message: {data.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_gripper_close():
    """测试关闭夹爪"""
    print_section("测试 7: 关闭夹爪")

    if not wait_for_user():
        return False

    try:
        response = requests.post(
            f"{BASE_URL}/gripper/close",
            json={"arm": "right", "force": 30.0}
        )
        data = response.json()
        if data.get('success'):
            print(f"✓ 夹爪关闭成功")
            return True
        else:
            print(f"✗ 夹爪关闭失败")
            print(f"  Message: {data.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_pick_with_coordinates():
    """测试使用精确坐标抓取"""
    print_section("测试 8: 使用精确坐标抓取")
    print("⚠️  重要：在执行前，请在指定位置放置一个物体")
    print("   建议位置: [0.65, -0.25, 0.02]")
    print("   - X: 0.65m (机器人前方 65cm)")
    print("   - Y: -0.25m (机器人右侧 25cm)")
    print("   - Z: 0.02m (桌面上方 2cm)")
    print()
    print("   建议使用：")
    print("   - 轻质物体（< 500g）")
    print("   - 易于抓取的形状（立方体、圆柱）")
    print("   - 尺寸：5-10cm")

    if not wait_for_user("物体已放置？按 Enter 继续: "):
        return False

    try:
        response = requests.post(
            f"{BASE_URL}/primitives/pick",
            json={
                "arm": "right",
                "position": [0.65, -0.25, 0.02],
                "approach_height": 0.1
            }
        )
        data = response.json()
        if data.get('success'):
            print(f"✓ 抓取成功")
            print(f"  Message: {data.get('message')}")
            print(f"  Final position: {data.get('final_position')}")
            return True
        else:
            print(f"✗ 抓取失败")
            print(f"  Message: {data.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_place_with_coordinates():
    """测试使用精确坐标放置"""
    print_section("测试 9: 使用精确坐标放置")
    print("这将把抓取的物体放置到新位置")
    print("目标位置: [0.55, -0.35, 0.02]")

    if not wait_for_user():
        return False

    try:
        response = requests.post(
            f"{BASE_URL}/primitives/place",
            json={
                "arm": "right",
                "position": [0.55, -0.35, 0.02],
                "approach_height": 0.1
            }
        )
        data = response.json()
        if data.get('success'):
            print(f"✓ 放置成功")
            print(f"  Message: {data.get('message')}")
            print(f"  Final position: {data.get('final_position')}")
            return True
        else:
            print(f"✗ 放置失败")
            print(f"  Message: {data.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_return_home():
    """测试返回初始位置"""
    print_section("测试 10: 返回初始位置")

    if not wait_for_user():
        return False

    try:
        response = requests.post(
            f"{BASE_URL}/primitives/home",
            json={"arm": "right"}
        )
        data = response.json()
        if data.get('success'):
            print(f"✓ 返回初始位置成功")
            return True
        else:
            print(f"✗ 返回初始位置失败")
            print(f"  Message: {data.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_disable():
    """测试禁用机器人"""
    print_section("测试 11: 禁用机器人")

    try:
        response = requests.post(f"{BASE_URL}/disable")
        data = response.json()
        print(f"✓ 机器人已禁用")
        print(f"  Message: {data.get('message')}")
        return True
    except Exception as e:
        print(f"✗ 禁用失败: {e}")
        return False

def main():
    """主测试流程"""
    print("=" * 60)
    print("  Baxter-Claw 真实机器人测试 - 阶段 1")
    print("  基础功能测试（使用精确坐标）")
    print("=" * 60)
    print()
    print("⚠️  安全提醒：")
    print("   1. 确保工作空间内无人")
    print("   2. 保持紧急停止按钮可用")
    print("   3. 随时准备按下紧急停止")
    print("   4. 如有异常，立即停止测试")
    print()

    if not wait_for_user("准备好开始测试？"):
        print("测试取消")
        return

    results = []

    # 测试序列
    tests = [
        ("连接检查", test_connection),
        ("状态查询", test_status),
        ("启用机器人", test_enable),
        ("回到初始位置", test_home),
        ("小幅度移动", test_small_movement),
        ("打开夹爪", test_gripper_open),
        ("关闭夹爪", test_gripper_close),
        ("精确坐标抓取", test_pick_with_coordinates),
        ("精确坐标放置", test_place_with_coordinates),
        ("返回初始位置", test_return_home),
        ("禁用机器人", test_disable),
    ]

    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
            if not success:
                print(f"\n⚠️  测试 '{name}' 失败")
                if not wait_for_user("继续下一个测试？"):
                    break
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n测试被用户中断")
            break
        except Exception as e:
            print(f"\n✗ 测试 '{name}' 出现异常: {e}")
            results.append((name, False))
            if not wait_for_user("继续下一个测试？"):
                break

    # 总结
    print("\n" + "=" * 60)
    print("  测试结果总结")
    print("=" * 60)

    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")

    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n✓ 所有测试通过！基础功能正常。")
        print("  下一步：可以尝试视觉功能测试")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        print("  请检查失败的测试并解决问题")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    finally:
        print("\n测试结束")