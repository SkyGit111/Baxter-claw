#!/usr/bin/env python
"""Test script for real Baxter robot grasping tasks.

This script performs step-by-step tests:
1. Basic robot control (enable, home position)
2. Coordinate-based movement
3. Gripper control
4. Vision-based object detection
5. Complete pick-and-place task
"""

import sys
import time
import asyncio
from typing import Optional

# Add ROS Python paths to sys.path (append, not insert, to avoid numpy conflicts)
_ros_paths = ['/opt/ros/noetic/lib/python3/dist-packages', '/usr/lib/python3/dist-packages']
for path in _ros_paths:
    if path not in sys.path:
        sys.path.append(path)

def test_basic_control():
    """Test basic robot control."""
    print("\n" + "="*60)
    print("测试 1: 基础机器人控制")
    print("="*60)

    try:
        from bridge.drivers.baxter_driver import BaxterDriver

        driver = BaxterDriver(use_depth_camera=True)

        if not driver.connect():
            print("  ✗ 连接失败")
            return None

        print("  ✓ 连接成功")

        # Enable robot
        print("\n  尝试使能机器人...")
        if driver.enable():
            print("  ✓ 机器人已使能")
        else:
            print("  ✗ 使能失败")
            return None

        # Get current pose
        pose = driver.get_endpoint_pose('right')
        print(f"\n  当前右臂末端位姿:")
        print(f"    位置: [{pose[0]:.3f}, {pose[1]:.3f}, {pose[2]:.3f}] m")
        print(f"    姿态: [{pose[3]:.3f}, {pose[4]:.3f}, {pose[5]:.3f}] rad")

        # Get joint angles
        angles = driver.get_joint_angles('right')
        print(f"\n  当前关节角度:")
        for joint, angle in angles.items():
            print(f"    {joint}: {angle:.3f} rad")

        return driver

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_gripper_control(driver):
    """Test gripper control."""
    print("\n" + "="*60)
    print("测试 2: 夹爪控制")
    print("="*60)

    try:
        # Calibrate gripper
        print("  校准夹爪...")
        if driver.gripper_command('right', 'calibrate'):
            print("  ✓ 夹爪校准成功")
        else:
            print("  ✗ 夹爪校准失败")
            return False

        time.sleep(2)

        # Open gripper
        print("\n  打开夹爪...")
        if driver.gripper_command('right', 'open'):
            print("  ✓ 夹爪已打开")
        else:
            print("  ✗ 打开失败")
            return False

        time.sleep(2)
        pos, force = driver.get_gripper_state('right')
        print(f"    状态: 位置={pos:.1f}, 力={force:.1f}")

        # Close gripper
        print("\n  关闭夹爪...")
        if driver.gripper_command('right', 'close'):
            print("  ✓ 夹爪已关闭")
        else:
            print("  ✗ 关闭失败")
            return False

        time.sleep(2)
        pos, force = driver.get_gripper_state('right')
        print(f"    状态: 位置={pos:.1f}, 力={force:.1f}")

        # Open again
        print("\n  再次打开夹爪...")
        driver.gripper_command('right', 'open')
        time.sleep(1)

        return True

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False

def test_coordinate_movement(driver):
    """Test coordinate-based movement."""
    print("\n" + "="*60)
    print("测试 3: 坐标运动")
    print("="*60)

    try:
        # Get current pose
        current_pose = driver.get_endpoint_pose('right')
        print(f"  当前位置: [{current_pose[0]:.3f}, {current_pose[1]:.3f}, {current_pose[2]:.3f}]")

        # Move up 10cm
        print("\n  向上移动 10cm...")
        target_pose = current_pose.copy()
        target_pose[2] += 0.1  # Move up 10cm

        if driver.move_to_pose('right', target_pose, speed=0.2):
            print("  ✓ 移动成功")
            time.sleep(1)
        else:
            print("  ✗ 移动失败")
            return False

        # Move back down
        print("\n  返回原位置...")
        if driver.move_to_pose('right', current_pose, speed=0.2):
            print("  ✓ 返回成功")
            time.sleep(1)
        else:
            print("  ✗ 返回失败")
            return False

        return True

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_vision_detection(driver):
    """Test vision-based object detection."""
    print("\n" + "="*60)
    print("测试 4: 视觉物体检测")
    print("="*60)

    try:
        from bridge.vlm_client import VLMClient

        # Initialize VLM client
        vlm = VLMClient(provider='qwen', api_key='sk-bd990626c84a4142b9581f13c5317522')
        print("  ✓ VLM 客户端初始化成功")

        # Capture image from Baxter camera
        print("\n  从右手相机捕获图像...")
        image_bytes = driver.capture_image('right_hand')

        if not image_bytes:
            print("  ✗ 图像捕获失败")
            return False

        print(f"  ✓ 捕获图像成功 ({len(image_bytes)} bytes)")

        # Describe scene
        print("\n  分析场景...")
        description = await vlm.describe_scene(image_bytes)
        print(f"\n  场景描述:\n{description}")

        # Identify objects
        print("\n  识别物体...")
        objects = await vlm.identify_objects(image_bytes)

        if objects:
            print(f"  ✓ 检测到 {len(objects)} 个物体:")
            for i, obj in enumerate(objects, 1):
                print(f"    {i}. {obj.get('name', 'unknown')}")
                print(f"       颜色: {obj.get('color', 'unknown')}")
                print(f"       位置: {obj.get('location', 'unknown')}")
                print(f"       可抓取: {obj.get('graspable', False)}")
        else:
            print("  ⚠ 未检测到物体")

        return True

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_vision_with_depth(driver):
    """Test vision with depth camera."""
    print("\n" + "="*60)
    print("测试 5: 深度增强视觉定位")
    print("="*60)

    try:
        if not driver.has_depth_camera():
            print("  ⚠ 深度相机不可用，跳过此测试")
            return True

        from bridge.vlm_client import VLMClient

        vlm = VLMClient(provider='qwen', api_key='sk-bd990626c84a4142b9581f13c5317522')

        # Capture RGBD
        print("  捕获 RGB-D 图像...")
        rgb, depth = driver.capture_rgbd()

        if rgb is None or depth is None:
            print("  ✗ RGB-D 捕获失败")
            return False

        print(f"  ✓ RGB-D 捕获成功")
        print(f"    RGB: {rgb.shape}")
        print(f"    Depth: {depth.shape}, 范围: {depth.min()}-{depth.max()} mm")

        # Convert RGB to JPEG
        import cv2
        success, jpeg_buffer = cv2.imencode('.jpg', rgb)
        if not success:
            print("  ✗ JPEG 编码失败")
            return False

        image_bytes = jpeg_buffer.tobytes()

        # Ask user what to locate
        print("\n  请输入要定位的物体名称 (例如: 红色杯子, 蓝色盒子)")
        print("  或按 Enter 跳过此测试")
        object_name = input("  物体名称: ").strip()

        if not object_name:
            print("  跳过物体定位测试")
            return True

        # Locate object with depth
        print(f"\n  定位物体: {object_name}...")

        workspace_bounds = {
            'x': (0.3, 0.9),
            'y': (-0.7, 0.7),
            'z': (-0.2, 0.5)
        }

        depth_camera = driver.get_depth_camera_driver()
        result = await vlm.locate_object_with_depth(
            image_bytes,
            depth,
            object_name,
            depth_camera,
            workspace_bounds
        )

        if result and result['found']:
            print(f"  ✓ 找到物体!")
            print(f"    位置: {result['position']}")
            print(f"    置信度: {result['confidence']}%")
            print(f"    描述: {result['description']}")
            if result.get('depth_enhanced'):
                print(f"    深度增强: 是")
                print(f"    VLM 估计: {result.get('vlm_estimate')}")
        else:
            print(f"  ✗ 未找到物体")

        return True

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_pick_place(driver):
    """Test complete pick and place task."""
    print("\n" + "="*60)
    print("测试 6: 完整抓取放置任务")
    print("="*60)

    print("\n  此测试需要手动指定物体位置")
    print("  请确保工作空间内有可抓取物体")
    print("\n  是否继续? (y/n): ", end='')

    response = input().strip().lower()
    if response != 'y':
        print("  跳过抓取测试")
        return True

    try:
        # Get pick position from user
        print("\n  请输入抓取位置 (单位: 米):")
        x = float(input("    X (前后, 0.3-0.9): "))
        y = float(input("    Y (左右, -0.7-0.7): "))
        z = float(input("    Z (高度, -0.2-0.5): "))

        pick_pos = [x, y, z]
        print(f"\n  抓取位置: {pick_pos}")

        # Get current pose for orientation
        current_pose = driver.get_endpoint_pose('right')

        # Approach position (10cm above)
        approach_pose = pick_pos + [current_pose[3], current_pose[4], current_pose[5]]
        approach_pose[2] += 0.1

        # Pick pose
        pick_pose = pick_pos + [current_pose[3], current_pose[4], current_pose[5]]

        # Open gripper
        print("\n  1. 打开夹爪...")
        driver.gripper_command('right', 'open')
        time.sleep(1)

        # Move to approach
        print("  2. 移动到接近位置...")
        if not driver.move_to_pose('right', approach_pose, speed=0.2):
            print("  ✗ 移动失败")
            return False
        time.sleep(1)

        # Move down to pick
        print("  3. 下降到抓取位置...")
        if not driver.move_to_pose('right', pick_pose, speed=0.1):
            print("  ✗ 移动失败")
            return False
        time.sleep(1)

        # Close gripper
        print("  4. 关闭夹爪...")
        driver.gripper_command('right', 'close')
        time.sleep(2)

        # Lift up
        print("  5. 提升物体...")
        if not driver.move_to_pose('right', approach_pose, speed=0.1):
            print("  ✗ 移动失败")
            return False
        time.sleep(1)

        # Get place position
        print("\n  请输入放置位置 (单位: 米):")
        x = float(input("    X (前后, 0.3-0.9): "))
        y = float(input("    Y (左右, -0.7-0.7): "))
        z = float(input("    Z (高度, -0.2-0.5): "))

        place_pos = [x, y, z]
        place_approach = place_pos + [current_pose[3], current_pose[4], current_pose[5]]
        place_approach[2] += 0.1
        place_pose = place_pos + [current_pose[3], current_pose[4], current_pose[5]]

        # Move to place approach
        print("\n  6. 移动到放置接近位置...")
        if not driver.move_to_pose('right', place_approach, speed=0.2):
            print("  ✗ 移动失败")
            return False
        time.sleep(1)

        # Move down to place
        print("  7. 下降到放置位置...")
        if not driver.move_to_pose('right', place_pose, speed=0.1):
            print("  ✗ 移动失败")
            return False
        time.sleep(1)

        # Open gripper
        print("  8. 打开夹爪释放物体...")
        driver.gripper_command('right', 'open')
        time.sleep(2)

        # Lift up
        print("  9. 提升...")
        if not driver.move_to_pose('right', place_approach, speed=0.1):
            print("  ✗ 移动失败")
            return False

        print("\n  ✓ 抓取放置任务完成!")
        return True

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Baxter 真机抓取测试")
    print("="*60)
    print("\n⚠ 警告: 此测试将控制真实机器人运动")
    print("请确保:")
    print("  1. 工作空间内无障碍物")
    print("  2. 已按下机器人急停按钮准备")
    print("  3. 有人在旁监督")
    print("\n继续? (y/n): ", end='')

    response = input().strip().lower()
    if response != 'y':
        print("\n测试已取消")
        return 1

    driver = None
    results = {}

    try:
        # Test 1: Basic control
        driver = test_basic_control()
        results['基础控制'] = driver is not None

        if not driver:
            print("\n⚠ 基础控制测试失败，终止测试")
            return 1

        # Test 2: Gripper
        results['夹爪控制'] = test_gripper_control(driver)

        # Test 3: Movement
        results['坐标运动'] = test_coordinate_movement(driver)

        # Test 4: Vision
        #results['视觉检测'] = await test_vision_detection(driver)

        # Test 5: Vision with depth
        #results['深度视觉'] = await test_vision_with_depth(driver)

        # Test 6: Pick and place
        results['抓取放置'] = await test_pick_place(driver)

        # Summary
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)

        for name, passed in results.items():
            status = "✓ 通过" if passed else "✗ 失败"
            print(f"  {name}: {status}")

        all_passed = all(results.values())

        if all_passed:
            print("\n✓ 所有测试通过!")
            print("\n系统已就绪，可以启动 Bridge Server:")
            print("  ./start_with_baxter.sh")
        else:
            print("\n⚠ 部分测试失败，请检查上述错误")

        return 0 if all_passed else 1

    except KeyboardInterrupt:
        print("\n\n⚠ 测试被用户中断")
        return 1

    except Exception as e:
        print(f"\n✗ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        if driver:
            print("\n清理资源...")
            # 保持机器人使能状态以防止机械臂下落
            driver.disconnect(keep_enabled=True)
            print("✓ 清理完成（机器人保持使能状态）")

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))