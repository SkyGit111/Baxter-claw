#!/usr/bin/env python3
"""
简化的调试脚本 - 立即显示输出
"""

import asyncio
import sys
import os

# 确保输出不被缓冲
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

from bridge.drivers.baxter_driver import BaxterDriver
from bridge.vlm_client import VLMClient
from bridge.safety import SafetyValidator
from bridge.multi_view_vlm import MultiViewVLMCoordinator

async def main():
    object_name = sys.argv[1] if len(sys.argv) > 1 else "魔方"

    print("=" * 70, flush=True)
    print(f"调试定位: {object_name}", flush=True)
    print("=" * 70, flush=True)

    # 初始化
    print("\n初始化...", flush=True)
    driver = BaxterDriver(use_depth_camera=True)
    vlm = VLMClient(provider='qwen')
    safety = SafetyValidator(config_path='config/baxter.yaml')

    print("连接Baxter...", flush=True)
    if not driver.connect():
        print("连接失败", flush=True)
        return

    print("✓ 已连接", flush=True)

    # 创建协调器
    coordinator = MultiViewVLMCoordinator(
        driver=driver,
        vlm_client=vlm,
        safety_validator=safety,
        debug=True
    )

    # 执行定位
    print(f"\n开始定位: {object_name}", flush=True)
    print("-" * 70, flush=True)

    # 临时禁用头部相机
    print("注意: 跳过头部相机（临时禁用）", flush=True)
    coordinator._head_camera_available = False

    result = await coordinator.locate_object_multiview(
        object_name=object_name,
        arm="right",
        use_wrist_refinement=False
    )

    print("-" * 70, flush=True)

    # 显示结果
    print("\n结果:", flush=True)
    if not result or not result.get('found'):
        print("✗ 未找到", flush=True)
        return

    print("✓ 找到物体", flush=True)
    print(f"  位置 (base): {result['position']}", flush=True)
    print(f"  置信度: {result.get('confidence', 0)}%", flush=True)

    if 'position_camera_frame' in result:
        print(f"  位置 (camera): {result['position_camera_frame']}", flush=True)

    # 检查图像
    print("\n调试图像:", flush=True)
    for img in ["debug_d455_phase1_annotated.jpg", "debug_d455_phase1_depth_annotated.jpg"]:
        if os.path.exists(img):
            print(f"  ✓ {img}", flush=True)

    driver.disconnect()
    print("\n完成!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
