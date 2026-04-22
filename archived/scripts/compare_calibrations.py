#!/usr/bin/env python3
"""
对比新旧标定数据
"""

import numpy as np
from scipy.spatial.transform import Rotation

print("=" * 70)
print("标定数据对比")
print("=" * 70)

# 旧标定数据 (2026-04-17之前)
old_trans = np.array([0.79105528, -0.03208981, 0.87098674])
old_quat = np.array([-0.6968628435748352, -0.6934558408352157, 0.01570590782478907, 0.1823581599921379])  # [qx, qy, qz, qw]

# 新标定数据 (2026-04-20)
new_trans = np.array([0.8542316736122598, -0.35403652088847243, 0.6511577622428796])
new_quat = np.array([-0.4529813846811967, -0.6306747347467527, -0.07883270716550929, 0.6251740944452001])  # [qx, qy, qz, qw]

print("\n旧标定 (2026-04-17之前):")
print(f"  平移: {old_trans}")
print(f"  四元数: {old_quat}")
old_rot = Rotation.from_quat(old_quat)
old_euler = old_rot.as_euler('xyz', degrees=True)
print(f"  欧拉角 (度): {old_euler}")

print("\n新标定 (2026-04-20):")
print(f"  平移: {new_trans}")
print(f"  四元数: {new_quat}")
new_rot = Rotation.from_quat(new_quat)
new_euler = new_rot.as_euler('xyz', degrees=True)
print(f"  欧拉角 (度): {new_euler}")

print("\n变化:")
trans_diff = new_trans - old_trans
print(f"  平移变化: {trans_diff}")
print(f"  平移变化幅度: {np.linalg.norm(trans_diff):.3f}m")

euler_diff = new_euler - old_euler
print(f"  欧拉角变化 (度): {euler_diff}")

print("\n" + "=" * 70)
print("分析:")
print("=" * 70)

if np.linalg.norm(trans_diff) > 0.5:
    print("⚠ 警告: 平移变化超过50cm，这对于固定相机来说不正常！")
    print("  可能原因:")
    print("  1. 相机确实移动了很多")
    print("  2. 新标定有错误")
    print("  3. 标定时的参考系设置不一致")

if np.abs(euler_diff).max() > 30:
    print("⚠ 警告: 旋转变化超过30度，这对于固定相机来说不正常！")

print("\n建议:")
print("1. 检查相机是否真的移动了这么多")
print("2. 如果相机只是小幅调整，建议重新标定")
print("3. 标定时确保:")
print("   - 使用足够多的标定点 (>20个)")
print("   - 标定点分布均匀")
print("   - ArUco标记清晰可见")
print("   - 机械臂姿态多样化")
