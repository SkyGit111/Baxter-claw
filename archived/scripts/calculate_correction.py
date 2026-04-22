#!/usr/bin/env python3
"""
坐标校正工具 - 根据实测数据计算校正偏移量
"""

import numpy as np
import yaml
import os

def calculate_correction():
    """根据实测数据计算校正偏移量"""

    print("=" * 70)
    print("坐标校正工具")
    print("=" * 70)

    # 实测数据
    test_data = [
        {
            "detected": [0.750, 0.182, -0.077],
            "actual": [0.877, 0.049, -0.103]
        },
        {
            "detected": [0.755, -0.108, -0.132],
            "actual": [0.890, -0.288, -0.108]
        },
        {
            "detected": [0.488, 0.048, -0.086],
            "actual": [0.618, -0.090, -0.108]
        }
    ]

    print("\n实测数据:")
    for i, data in enumerate(test_data, 1):
        detected = data["detected"]
        actual = data["actual"]
        diff = [actual[j] - detected[j] for j in range(3)]
        print(f"\n测试{i}:")
        print(f"  检测: [{detected[0]:.3f}, {detected[1]:.3f}, {detected[2]:.3f}]")
        print(f"  实际: [{actual[0]:.3f}, {actual[1]:.3f}, {actual[2]:.3f}]")
        print(f"  偏差: [{diff[0]:+.3f}, {diff[1]:+.3f}, {diff[2]:+.3f}]")

    # 计算平均偏移量
    print("\n" + "=" * 70)
    print("计算平均偏移量:")
    print("=" * 70)

    offsets = []
    for data in test_data:
        detected = np.array(data["detected"])
        actual = np.array(data["actual"])
        offset = actual - detected
        offsets.append(offset)

    mean_offset = np.mean(offsets, axis=0)
    std_offset = np.std(offsets, axis=0)

    print(f"\n平均偏移量: [{mean_offset[0]:+.3f}, {mean_offset[1]:+.3f}, {mean_offset[2]:+.3f}]")
    print(f"标准差:     [{std_offset[0]:.3f}, {std_offset[1]:.3f}, {std_offset[2]:.3f}]")

    # 验证校正效果
    print("\n" + "=" * 70)
    print("验证校正效果:")
    print("=" * 70)

    total_error_before = 0
    total_error_after = 0

    for i, data in enumerate(test_data, 1):
        detected = np.array(data["detected"])
        actual = np.array(data["actual"])
        corrected = detected + mean_offset

        error_before = np.linalg.norm(actual - detected)
        error_after = np.linalg.norm(actual - corrected)

        total_error_before += error_before
        total_error_after += error_after

        print(f"\n测试{i}:")
        print(f"  校正前误差: {error_before*1000:.1f}mm")
        print(f"  校正后误差: {error_after*1000:.1f}mm")
        print(f"  改善: {(1 - error_after/error_before)*100:.1f}%")

    print(f"\n总体:")
    print(f"  平均误差 (校正前): {total_error_before/len(test_data)*1000:.1f}mm")
    print(f"  平均误差 (校正后): {total_error_after/len(test_data)*1000:.1f}mm")
    print(f"  总体改善: {(1 - total_error_after/total_error_before)*100:.1f}%")

    # 保存校正配置
    print("\n" + "=" * 70)
    print("保存校正配置:")
    print("=" * 70)

    config = {
        "d455_position_correction": {
            "enabled": True,
            "offset": {
                "x": float(mean_offset[0]),
                "y": float(mean_offset[1]),
                "z": float(mean_offset[2])
            },
            "description": "Position correction offset based on empirical measurements",
            "measurement_date": "2026-04-17",
            "sample_size": len(test_data),
            "average_error_before_mm": float(total_error_before/len(test_data)*1000),
            "average_error_after_mm": float(total_error_after/len(test_data)*1000)
        }
    }

    config_path = "config/position_correction.yaml"
    os.makedirs("config", exist_ok=True)

    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    print(f"✓ 校正配置已保存到: {config_path}")

    print("\n" + "=" * 70)
    print("下一步:")
    print("=" * 70)
    print("1. 校正配置已生成")
    print("2. 需要修改 camera_transforms.py 应用此校正")
    print("3. 重新测试验证效果")
    print("=" * 70)

if __name__ == "__main__":
    calculate_correction()
