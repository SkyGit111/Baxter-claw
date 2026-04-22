#!/usr/bin/env python3
"""
验证坐标转换准确性的工具
"""

import numpy as np
from bridge.camera_transforms import CameraTransforms

def test_coordinate_transform():
    """测试坐标转换"""

    print("=" * 70)
    print("坐标转换验证工具")
    print("=" * 70)

    transforms = CameraTransforms()

    if not transforms.is_d455_calibrated():
        print("\n错误: D455未标定!")
        return

    print("\n手眼标定数据:")
    transform_matrix = transforms.d455_to_base
    print(f"变换矩阵:\n{transform_matrix}")

    print("\n" + "=" * 70)
    print("请输入相机坐标系的位置进行验证")
    print("=" * 70)

    while True:
        print("\n输入相机坐标系位置 (格式: x y z，单位米)")
        print("例如: 0.1 0.2 0.85")
        print("输入 'q' 退出")

        user_input = input("> ").strip()

        if user_input.lower() == 'q':
            break

        try:
            parts = user_input.split()
            if len(parts) != 3:
                print("错误: 需要3个数值 (x y z)")
                continue

            x, y, z = map(float, parts)
            pos_camera = np.array([x, y, z])

            # 转换到基座坐标系
            pos_base = transforms.transform_d455_to_base(pos_camera)

            print(f"\n相机坐标系: [{x:.3f}, {y:.3f}, {z:.3f}]")
            print(f"基座坐标系: [{pos_base[0]:.3f}, {pos_base[1]:.3f}, {pos_base[2]:.3f}]")

            # 检查是否在合理范围内
            print("\n合理性检查:")

            # Baxter工作空间大约: x:[0.3, 1.0], y:[-0.8, 0.8], z:[-0.3, 0.5]
            issues = []

            if not (0.2 < pos_base[0] < 1.2):
                issues.append(f"  ⚠ X={pos_base[0]:.3f} 可能超出范围 (期望: 0.2-1.2)")

            if not (-0.9 < pos_base[1] < 0.9):
                issues.append(f"  ⚠ Y={pos_base[1]:.3f} 可能超出范围 (期望: -0.9-0.9)")

            if not (-0.4 < pos_base[2] < 0.6):
                issues.append(f"  ⚠ Z={pos_base[2]:.3f} 可能超出范围 (期望: -0.4-0.6)")

            if issues:
                for issue in issues:
                    print(issue)
            else:
                print("  ✓ 位置在合理范围内")

            # 提供手动验证建议
            print("\n手动验证建议:")
            print(f"  1. 使用Baxter移动到基座坐标: [{pos_base[0]:.3f}, {pos_base[1]:.3f}, {pos_base[2]:.3f}]")
            print(f"  2. 观察末端执行器是否到达物体位置")
            print(f"  3. 如果偏差大，可能需要重新标定")

        except ValueError as e:
            print(f"错误: 输入格式不正确 - {e}")
        except Exception as e:
            print(f"错误: {e}")

    print("\n" + "=" * 70)
    print("退出")
    print("=" * 70)

if __name__ == "__main__":
    test_coordinate_transform()
