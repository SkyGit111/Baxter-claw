#!/usr/bin/env python
"""深度相机标定脚本 - 测量相机到机器人基座的坐标变换

使用方法：
1. 在工作空间放置一个已知位置的标记物（如棋盘格或明显的物体）
2. 使用机器人末端触碰该物体，记录机器人坐标
3. 使用深度相机测量该物体，记录相机坐标
4. 计算变换矩阵
"""

import sys
import numpy as np

# Add ROS paths
_ros_paths = ['/opt/ros/noetic/lib/python3/dist-packages', '/usr/lib/python3/dist-packages']
for path in _ros_paths:
    if path not in sys.path:
        sys.path.append(path)

def main():
    print("\n" + "="*60)
    print("深度相机标定工具")
    print("="*60)

    from bridge.drivers.baxter_driver import BaxterDriver

    # Initialize driver with depth camera
    print("\n初始化机器人和深度相机...")
    driver = BaxterDriver(use_depth_camera=True)

    if not driver.connect():
        print("✗ 连接失败")
        return 1

    if not driver.has_depth_camera():
        print("✗ 深度相机不可用")
        return 1

    print("✓ 初始化成功")

    # Enable robot
    if not driver.enable():
        print("✗ 使能失败")
        return 1

    print("\n" + "="*60)
    print("标定步骤")
    print("="*60)
    print("\n请按照以下步骤操作：")
    print("1. 在工作空间放置一个明显的标记物（如红色杯子）")
    print("2. 手动移动机器人末端，让末端触碰标记物中心")
    print("3. 记录机器人末端位置")
    print("4. 使用深度相机测量标记物位置")
    print("5. 移动标记物到不同位置，重复步骤 2-4")
    print("6. 使用多个点计算坐标变换")
    print("\n建议：至少采集 3-5 个标定点以提高精度")

    input("\n按 Enter 继续...")

    # Collect multiple calibration points
    robot_points = []
    camera_points = []

    num_points = int(input("\n请输入要采集的标定点数量（建议 3-5 个）: "))

    for i in range(num_points):
        print("\n" + "="*60)
        print(f"标定点 {i+1}/{num_points}")
        print("="*60)

        if i > 0:
            print("\n请移动标记物到新位置")
            input("移动完成后按 Enter...")

        # Step 1: Get robot endpoint position
        print("\n请手动移动机器人末端到标记物中心位置")
        print("（可以使用 Baxter 的零重力模式）")
        input("移动完成后按 Enter...")

        robot_pose = driver.get_endpoint_pose('right')
        robot_pos = robot_pose[:3]

        print(f"\n机器人末端位置: [{robot_pos[0]:.4f}, {robot_pos[1]:.4f}, {robot_pos[2]:.4f}] m")

        # Step 2: Capture depth image
        print("\n捕获深度图像...")

        rgb, depth = driver.capture_rgbd()

        if rgb is None or depth is None:
            print("✗ 图像捕获失败")
            continue

        print(f"✓ 图像捕获成功: RGB {rgb.shape}, Depth {depth.shape}")

        # Save debug images
        import cv2
        cv2.imwrite(f'/tmp/calibration_{i+1}_rgb.jpg', rgb)
        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(depth, alpha=0.03),
            cv2.COLORMAP_JET
        )
        cv2.imwrite(f'/tmp/calibration_{i+1}_depth.jpg', depth_colormap)
        print(f"\n图像已保存到:")
        print(f"  RGB: /tmp/calibration_{i+1}_rgb.jpg")
        print(f"  Depth: /tmp/calibration_{i+1}_depth.jpg")

        print(f"\n图像尺寸: {rgb.shape[1]} x {rgb.shape[0]} 像素")
        print(f"图像中心: ({rgb.shape[1]//2}, {rgb.shape[0]//2})")

        pixel_x = int(input("\n输入标记物中心的 X 像素坐标: "))
        pixel_y = int(input("输入标记物中心的 Y 像素坐标: "))

        # Get 3D point from depth camera
        depth_camera = driver.get_depth_camera_driver()
        camera_point = depth_camera.get_3d_point_from_pixel(depth, pixel_x, pixel_y)

        if camera_point is None:
            print("✗ 无法获取深度数据，跳过此点")
            continue

        camera_pos = list(camera_point)
        print(f"\n深度相机测量位置: [{camera_pos[0]:.4f}, {camera_pos[1]:.4f}, {camera_pos[2]:.4f}] m")

        # Store points
        robot_points.append(robot_pos)
        camera_points.append(camera_pos)

        print(f"\n✓ 标定点 {i+1} 采集完成")

    if len(robot_points) < 3:
        print("\n✗ 标定点数量不足（至少需要 3 个点）")
        return 1

    # Step 3: Calculate transformation using least squares
    print("\n" + "="*60)
    print("步骤 3: 计算坐标变换")
    print("="*60)

    robot_points = np.array(robot_points)
    camera_points = np.array(camera_points)

    # Calculate translation (average offset)
    translation = np.mean(robot_points - camera_points, axis=0)

    print(f"\n使用 {len(robot_points)} 个标定点计算得到的平移变换:")
    print(f"  X 偏移: {translation[0]:+.4f} m")
    print(f"  Y 偏移: {translation[1]:+.4f} m")
    print(f"  Z 偏移: {translation[2]:+.4f} m")

    print("\n" + "="*60)
    print("标定结果")
    print("="*60)
    print("\n请将以下配置添加到 config/baxter.yaml:")
    print("\ndriver:")
    print("  depth_camera_transform:")
    print(f"    translation: [{translation[0]:.4f}, {translation[1]:.4f}, {translation[2]:.4f}]")
    print(f"    rotation: [0.0, 0.0, 0.0]  # 假设无旋转，如需精确请使用多点标定")

    print("\n" + "="*60)
    print("验证")
    print("="*60)
    print("\n各标定点的误差:")

    errors = []
    for i, (robot_pos, camera_pos) in enumerate(zip(robot_points, camera_points)):
        corrected_pos = camera_pos + translation
        error = np.linalg.norm(robot_pos - corrected_pos)
        errors.append(error)
        print(f"\n点 {i+1}:")
        print(f"  机器人位置: [{robot_pos[0]:.4f}, {robot_pos[1]:.4f}, {robot_pos[2]:.4f}] m")
        print(f"  相机位置（校正后）: [{corrected_pos[0]:.4f}, {corrected_pos[1]:.4f}, {corrected_pos[2]:.4f}] m")
        print(f"  误差: {error*1000:.2f} mm")

    mean_error = np.mean(errors)
    max_error = np.max(errors)

    print(f"\n平均误差: {mean_error*1000:.2f} mm")
    print(f"最大误差: {max_error*1000:.2f} mm")

    if mean_error < 0.01:
        print("\n✓ 标定精度优秀（平均误差 < 10mm）")
    elif mean_error < 0.02:
        print("\n✓ 标定精度良好（平均误差 < 20mm）")
    elif mean_error < 0.05:
        print("\n⚠ 标定精度一般（平均误差 < 50mm），建议增加标定点")
    else:
        print("\n✗ 标定精度较差（平均误差 > 50mm），请检查标定过程")

    print("\n建议：")
    print("- 如果误差较大，可以增加更多标定点")
    print("- 确保标记物在不同位置（前后、左右、高低）")
    print("- 确保机器人末端精确触碰标记物中心")
    print("- 确保像素坐标选择准确")

    # Cleanup
    driver.disconnect(keep_enabled=True)
    print("\n✓ 标定完成（机器人保持使能状态）")

    return 0

if __name__ == "__main__":
    sys.exit(main())