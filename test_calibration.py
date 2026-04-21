#!/usr/bin/env python3
"""
验证手眼标定精度的测试脚本
"""

import numpy as np
from bridge.camera_transforms import CameraTransforms

def test_calibration():
    """测试手眼标定的准确性"""

    print("=" * 60)
    print("手眼标定验证测试")
    print("=" * 60)

    # 初始化
    transforms = CameraTransforms()

    # 检查标定状态
    print("\n1. 检查标定状态:")
    print(f"   D455标定: {'✓' if transforms.is_d455_calibrated() else '✗'}")

    if not transforms.is_d455_calibrated():
        print("\n错误: D455未标定!")
        print("请运行手眼标定: python manual_handeye_calibration.py")
        return

    # 显示标定数据
    print("\n2. 标定数据:")
    transform_matrix = transforms.d455_to_base
    translation = transform_matrix[:3, 3]
    rotation = transform_matrix[:3, :3]

    print(f"   平移向量 (T): {translation}")
    print(f"   旋转矩阵 (R):")
    for row in rotation:
        print(f"      [{row[0]:8.5f}, {row[1]:8.5f}, {row[2]:8.5f}]")

    # 测试已知点的转换
    print("\n3. 测试已知点转换:")

    test_cases = [
        {
            "name": "相机原点",
            "camera": np.array([0.0, 0.0, 0.0]),
            "expected_base": "相机在基座坐标系中的位置"
        },
        {
            "name": "相机前方50cm",
            "camera": np.array([0.0, 0.0, 0.5]),
            "expected_base": "相机前方50cm在基座坐标系中的位置"
        },
        {
            "name": "相机右侧20cm",
            "camera": np.array([0.2, 0.0, 0.0]),
            "expected_base": "相机右侧20cm在基座坐标系中的位置"
        },
        {
            "name": "相机上方10cm",
            "camera": np.array([0.0, -0.1, 0.0]),
            "expected_base": "相机上方10cm在基座坐标系中的位置"
        }
    ]

    for test in test_cases:
        pos_camera = test["camera"]
        pos_base = transforms.transform_d455_to_base(pos_camera)

        print(f"\n   {test['name']}:")
        print(f"      相机坐标系: {pos_camera}")
        print(f"      基座坐标系: {pos_base}")
        print(f"      说明: {test['expected_base']}")

    # 验证转换的合理性
    print("\n4. 合理性检查:")

    # 相机原点应该在机器人工作空间内
    camera_origin_base = transforms.transform_d455_to_base(np.array([0, 0, 0]))
    print(f"   相机位置 (base): {camera_origin_base}")

    # 检查是否在合理范围内
    # Baxter的工作空间大约是: x: [0.3, 1.0], y: [-0.8, 0.8], z: [-0.3, 0.5]
    reasonable = True
    if not (0.2 < camera_origin_base[0] < 1.2):
        print(f"   ⚠ X坐标 {camera_origin_base[0]:.3f} 可能不合理 (期望: 0.2-1.2)")
        reasonable = False
    if not (-1.0 < camera_origin_base[1] < 1.0):
        print(f"   ⚠ Y坐标 {camera_origin_base[1]:.3f} 可能不合理 (期望: -1.0-1.0)")
        reasonable = False
    if not (-0.5 < camera_origin_base[2] < 1.0):
        print(f"   ⚠ Z坐标 {camera_origin_base[2]:.3f} 可能不合理 (期望: -0.5-1.0)")
        reasonable = False

    if reasonable:
        print("   ✓ 相机位置在合理范围内")
    else:
        print("   ✗ 相机位置可能不合理，建议重新标定")

    # 测试逆转换
    print("\n5. 测试逆转换:")
    test_point_camera = np.array([0.1, 0.2, 0.3])
    test_point_base = transforms.transform_d455_to_base(test_point_camera)

    # 手动实现逆转换
    transform_matrix = transforms.d455_to_base
    inverse_transform = np.linalg.inv(transform_matrix)

    # 转换回相机坐标系
    test_point_base_homo = np.append(test_point_base, 1.0)
    test_point_camera_back_homo = inverse_transform @ test_point_base_homo
    test_point_camera_back = test_point_camera_back_homo[:3]

    print(f"   原始 (camera): {test_point_camera}")
    print(f"   转换 (base):   {test_point_base}")
    print(f"   逆转换 (camera): {test_point_camera_back}")

    error = np.linalg.norm(test_point_camera - test_point_camera_back)
    print(f"   误差: {error:.6f}m")

    if error < 0.001:
        print("   ✓ 逆转换精度良好")
    else:
        print("   ⚠ 逆转换误差较大")

    # 总结
    print("\n" + "=" * 60)
    print("总结:")
    if reasonable and error < 0.001:
        print("✓ 手眼标定数据看起来合理")
        print("  如果定位仍然不准确，可能的原因:")
        print("  1. VLM边界框识别不准确")
        print("  2. 深度相机测量误差")
        print("  3. 标定精度不足（建议增加标定点数量）")
    else:
        print("✗ 手眼标定数据可能有问题")
        print("  建议重新进行手眼标定")
    print("=" * 60)

if __name__ == "__main__":
    test_calibration()
