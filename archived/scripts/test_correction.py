#!/usr/bin/env python3
"""
验证位置校正效果
"""

import numpy as np
from bridge.camera_transforms import CameraTransforms

def test_correction():
    """测试位置校正效果"""

    print("=" * 70)
    print("位置校正验证")
    print("=" * 70)

    # 初始化（会自动加载校正配置）
    transforms = CameraTransforms()

    # 测试数据（相机坐标系）
    test_cases = [
        {
            "name": "测试1",
            "camera": [0.00453787, 0.22584686, 0.94499999],
            "expected": [0.877, 0.049, -0.103]
        },
        {
            "name": "测试2 (假设)",
            "camera": [0.1, 0.2, 0.9],  # 需要替换为实际的相机坐标
            "expected": [0.890, -0.288, -0.108]
        },
        {
            "name": "测试3 (假设)",
            "camera": [0.05, 0.15, 0.85],  # 需要替换为实际的相机坐标
            "expected": [0.618, -0.090, -0.108]
        }
    ]

    print("\n校正状态:")
    if transforms.position_correction is not None:
        print(f"  ✓ 校正已启用")
        print(f"  偏移量: {transforms.position_correction}")
    else:
        print(f"  ✗ 校正未启用")

    print("\n" + "=" * 70)
    print("测试结果:")
    print("=" * 70)

    total_error = 0
    for test in test_cases:
        camera_pos = np.array(test["camera"])
        expected_pos = np.array(test["expected"])

        # 转换（会自动应用校正）
        result_pos = transforms.transform_d455_to_base(camera_pos)

        # 计算误差
        error = np.linalg.norm(result_pos - expected_pos)
        total_error += error

        print(f"\n{test['name']}:")
        print(f"  相机坐标: [{camera_pos[0]:.3f}, {camera_pos[1]:.3f}, {camera_pos[2]:.3f}]")
        print(f"  转换结果: [{result_pos[0]:.3f}, {result_pos[1]:.3f}, {result_pos[2]:.3f}]")
        print(f"  期望位置: [{expected_pos[0]:.3f}, {expected_pos[1]:.3f}, {expected_pos[2]:.3f}]")
        print(f"  误差: {error*1000:.1f}mm")

        if error < 0.05:  # 50mm
            print(f"  ✓ 精度良好")
        elif error < 0.10:  # 100mm
            print(f"  ⚠ 精度一般")
        else:
            print(f"  ✗ 精度较差")

    avg_error = total_error / len(test_cases)
    print(f"\n平均误差: {avg_error*1000:.1f}mm")

    print("\n" + "=" * 70)
    if avg_error < 0.05:
        print("✓ 校正效果良好！")
    elif avg_error < 0.10:
        print("⚠ 校正有改善，但仍有优化空间")
    else:
        print("✗ 校正效果不佳，可能需要更多测试数据")
    print("=" * 70)

if __name__ == "__main__":
    test_correction()
