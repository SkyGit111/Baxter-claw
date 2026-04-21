#!/usr/bin/env python3
"""
手动验证标定数据

通过实际测量来验证标定是否准确
"""

import numpy as np
from bridge.camera_transforms import CameraTransforms
from bridge.drivers.baxter_driver import BaxterDriver

def manual_calibration_check():
    """手动检查标定准确性"""

    print("=" * 70)
    print("手动标定验证工具")
    print("=" * 70)

    print("\n步骤:")
    print("1. 在桌面上放置一个明显的物体")
    print("2. 使用Baxter手臂移动到物体位置")
    print("3. 记录末端执行器的位置")
    print("4. 使用深度相机测量物体位置")
    print("5. 对比两个位置，计算偏差")

    print("\n" + "=" * 70)
    print("请输入测量数据")
    print("=" * 70)

    # 输入相机测量的位置
    print("\n从调试输出中复制相机坐标系位置:")
    print("格式: Position (camera frame): [x, y, z]")
    camera_input = input("> ").strip()

    # 解析输入
    import re
    match = re.search(r'\[([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\]', camera_input)
    if not match:
        print("错误: 无法解析输入")
        return

    camera_pos = np.array([float(match.group(1)), float(match.group(2)), float(match.group(3))])

    # 输入实际位置
    print("\n从Baxter末端执行器读取的实际位置:")
    print("格式: [x, y, z]")
    actual_input = input("> ").strip()

    match = re.search(r'\[([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\]', actual_input)
    if not match:
        print("错误: 无法解析输入")
        return

    actual_pos = np.array([float(match.group(1)), float(match.group(2)), float(match.group(3))])

    # 使用当前标定转换
    transforms = CameraTransforms()
    converted_pos = transforms.transform_d455_to_base(camera_pos)

    print("\n" + "=" * 70)
    print("结果:")
    print("=" * 70)

    print(f"\n相机坐标: {camera_pos}")
    print(f"转换后坐标: {converted_pos}")
    print(f"实际坐标: {actual_pos}")

    error = actual_pos - converted_pos
    error_magnitude = np.linalg.norm(error)

    print(f"\n误差: {error}")
    print(f"误差幅度: {error_magnitude*1000:.1f}mm")

    if error_magnitude < 0.05:
        print("\n✓ 标定准确 (<5cm)")
    elif error_magnitude < 0.10:
        print("\n⚠ 标定一般 (5-10cm)")
    else:
        print("\n✗ 标定不准确 (>10cm)")
        print("\n建议:")
        print("1. 重新进行手眼标定")
        print("2. 确保使用30+个标定点")
        print("3. 标定点要覆盖整个工作空间")
        print("4. 或者使用位置校正来补偿")

        print(f"\n如果误差是系统性的，可以添加校正偏移:")
        print(f"  X偏移: {error[0]:+.4f}m")
        print(f"  Y偏移: {error[1]:+.4f}m")
        print(f"  Z偏移: {error[2]:+.4f}m")

if __name__ == "__main__":
    manual_calibration_check()
