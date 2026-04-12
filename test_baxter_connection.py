#!/usr/bin/env python
"""Test script for Baxter robot connection and basic functionality.

This script tests:
1. ROS connection
2. Baxter interface initialization
3. RealSense D455 depth camera
4. Basic robot operations (enable, joint angles, gripper)
"""

import sys
import time

# Add ROS Python paths to sys.path (append, not insert, to avoid numpy conflicts)
_ros_paths = ['/opt/ros/noetic/lib/python3/dist-packages', '/usr/lib/python3/dist-packages']
for path in _ros_paths:
    if path not in sys.path:
        sys.path.append(path)

def test_ros_connection():
    """Test ROS connection."""
    print("\n" + "="*60)
    print("测试 1: ROS 连接")
    print("="*60)

    try:
        import rospy
        print("  ✓ rospy 导入成功")

        if not rospy.core.is_initialized():
            rospy.init_node('baxter_connection_test', anonymous=True)
            print("  ✓ ROS 节点初始化成功")
        else:
            print("  ✓ ROS 节点已初始化")

        # Test rostopic list
        import subprocess
        result = subprocess.run(['rostopic', 'list'], capture_output=True, text=True, timeout=5)
        topics = result.stdout.strip().split('\n')

        baxter_topics = [t for t in topics if '/robot/' in t]
        if baxter_topics:
            print(f"  ✓ 检测到 {len(baxter_topics)} 个 Baxter 话题")
            print(f"    示例: {baxter_topics[0]}")
            return True
        else:
            print("  ✗ 未检测到 Baxter 话题")
            print("    请确认已运行 ./baxter.sh")
            return False

    except Exception as e:
        print(f"  ✗ ROS 连接失败: {e}")
        return False

def test_baxter_interface():
    """Test Baxter interface."""
    print("\n" + "="*60)
    print("测试 2: Baxter 接口")
    print("="*60)

    try:
        import baxter_interface
        from baxter_interface import CHECK_VERSION
        print("  ✓ baxter_interface 导入成功")

        # Test robot enable
        rs = baxter_interface.RobotEnable(CHECK_VERSION)
        print("  ✓ RobotEnable 接口创建成功")

        state = rs.state()
        print(f"  机器人状态:")
        print(f"    - 使能: {state.enabled}")
        print(f"    - 停止: {state.stopped}")
        print(f"    - 错误: {state.error}")

        # Test limb interface
        right_limb = baxter_interface.Limb('right')
        print("  ✓ 右臂接口创建成功")

        angles = right_limb.joint_angles()
        print(f"  ✓ 成功读取关节角度 ({len(angles)} 个关节)")

        # Test gripper interface
        right_gripper = baxter_interface.Gripper('right', CHECK_VERSION)
        print("  ✓ 右手夹爪接口创建成功")

        return True

    except Exception as e:
        print(f"  ✗ Baxter 接口测试失败: {e}")
        return False

def test_realsense():
    """Test RealSense D455 depth camera."""
    print("\n" + "="*60)
    print("测试 3: RealSense D455 深度相机")
    print("="*60)

    try:
        import pyrealsense2 as rs
        print("  ✓ pyrealsense2 导入成功")

        from bridge.drivers.realsense_driver import RealSenseDriver
        print("  ✓ RealSenseDriver 导入成功")

        # Initialize driver
        driver = RealSenseDriver(width=640, height=480, fps=30)
        print("  ✓ D455 初始化成功")

        # Capture a frame
        rgb, depth = driver.capture_rgbd()
        print(f"  ✓ 成功捕获图像:")
        print(f"    - RGB: {rgb.shape}")
        print(f"    - Depth: {depth.shape}, 范围: {depth.min()}-{depth.max()} mm")

        # Test 3D conversion
        center_x = rgb.shape[1] // 2
        center_y = rgb.shape[0] // 2
        point_3d = driver.get_3d_point_from_pixel(depth, center_x, center_y)

        if point_3d:
            print(f"  ✓ 3D 坐标转换成功:")
            print(f"    像素 ({center_x}, {center_y}) -> 3D ({point_3d[0]:.3f}, {point_3d[1]:.3f}, {point_3d[2]:.3f}) m")

        driver.stop()
        return True

    except Exception as e:
        print(f"  ✗ RealSense 测试失败: {e}")
        return False

def test_baxter_driver():
    """Test Baxter driver with depth camera."""
    print("\n" + "="*60)
    print("测试 4: Baxter 驱动集成")
    print("="*60)

    try:
        from bridge.drivers.baxter_driver import BaxterDriver
        print("  ✓ BaxterDriver 导入成功")

        # Initialize with depth camera
        driver = BaxterDriver(use_depth_camera=True)
        print("  ✓ BaxterDriver 初始化成功 (启用深度相机)")

        # Connect
        if driver.connect():
            print("  ✓ 连接到 Baxter 成功")
        else:
            print("  ✗ 连接到 Baxter 失败")
            return False

        # Check depth camera
        if driver.has_depth_camera():
            print("  ✓ 深度相机可用")

            # Test RGBD capture
            rgb, depth = driver.capture_rgbd()
            if rgb is not None and depth is not None:
                print(f"  ✓ 通过驱动捕获 RGBD 成功")
            else:
                print("  ✗ RGBD 捕获失败")
        else:
            print("  ⚠ 深度相机不可用")

        # Test basic operations
        if driver.is_enabled():
            print("  ✓ 机器人已使能")
        else:
            print("  ⚠ 机器人未使能 (这是正常的)")

        # Get joint angles
        angles = driver.get_joint_angles('right')
        if angles:
            print(f"  ✓ 成功读取右臂关节角度 ({len(angles)} 个关节)")

        # Get endpoint pose
        pose = driver.get_endpoint_pose('right')
        print(f"  ✓ 右臂末端位姿: [{pose[0]:.3f}, {pose[1]:.3f}, {pose[2]:.3f}] m")

        driver.disconnect()
        print("  ✓ 断开连接成功")

        return True

    except Exception as e:
        print(f"  ✗ Baxter 驱动测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Baxter-Claw 连接测试")
    print("="*60)

    results = {}

    # Test 1: ROS
    results['ROS'] = test_ros_connection()

    if not results['ROS']:
        print("\n⚠ ROS 连接失败，跳过后续测试")
        print("请确认:")
        print("  1. 已运行 cd ~/catkin_ws && ./baxter.sh")
        print("  2. Baxter 机器人已开机并完全启动")
        sys.exit(1)

    # Test 2: Baxter interface
    results['Baxter接口'] = test_baxter_interface()

    # Test 3: RealSense
    results['RealSense'] = test_realsense()

    # Test 4: Baxter driver
    results['Baxter驱动'] = test_baxter_driver()

    # Summary
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\n✓ 所有测试通过！")
        print("\n下一步:")
        print("  运行 python test_real_baxter_grasp.py 测试抓取功能")
    else:
        print("\n⚠ 部分测试失败，请检查上述错误信息")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())