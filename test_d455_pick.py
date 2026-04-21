#!/usr/bin/env python3
"""
D455深度相机定位+抓取测试

使用和debug_localization.py完全相同的定位方法

用法：
    python test_d455_pick.py 魔方
"""

import asyncio
import sys
import os

# 确保输出不被缓冲
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

from bridge.drivers.baxter_driver import BaxterDriver
from bridge.vlm_client import VLMClient
from bridge.safety import SafetyValidator
from bridge.primitives import BaxterPrimitives
from bridge.multi_view_vlm import MultiViewVLMCoordinator

async def test_d455_pick(object_name: str, arm: str = "right"):
    """使用D455定位并抓取物体"""

    print("=" * 70, flush=True)
    print(f"D455定位+抓取测试: {object_name}", flush=True)
    print("=" * 70, flush=True)

    # 初始化
    print("\n[1] 初始化组件...", flush=True)
    driver = BaxterDriver(use_depth_camera=True)
    vlm = VLMClient(provider='qwen')
    safety = SafetyValidator(config_path='config/baxter.yaml')
    primitives = BaxterPrimitives(driver, safety, vlm)

    # 使用MultiViewVLMCoordinator - 和debug_localization完全一样
    coordinator = MultiViewVLMCoordinator(
        driver=driver,
        vlm_client=vlm,
        safety_validator=safety,
        debug=True
    )

    print("  连接Baxter...", flush=True)
    if not driver.connect():
        print("  ✗ 连接失败", flush=True)
        return False

    print("  ✓ Baxter已连接", flush=True)

    try:
        # 步骤1: 使用MultiViewVLMCoordinator定位 - 和debug_localization完全一样
        print(f"\n[2] 使用D455定位: {object_name}", flush=True)
        print("-" * 70, flush=True)

        # 禁用头部相机，只使用D455
        coordinator._head_camera_available = False

        # 调用locate_object_multiview - 和debug_localization完全一样
        result = await coordinator.locate_object_multiview(
            object_name=object_name,
            arm=arm,
            use_wrist_refinement=False  # 只使用Phase 1
        )

        print("-" * 70, flush=True)

        if not result or not result.get('found'):
            print(f"\n✗ 定位失败", flush=True)
            if result:
                print(f"  原因: {result.get('message', '未知')}", flush=True)
            return False

        # 显示定位结果
        position = result['position']
        confidence = result['confidence']

        print(f"\n✓ 定位成功!", flush=True)
        print(f"  位置 (base frame): [{position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f}]", flush=True)
        print(f"  置信度: {confidence}%", flush=True)

        # 显示相机坐标（如果有）
        if 'position_camera_frame' in result:
            cam_pos = result['position_camera_frame']
            print(f"  位置 (camera frame): [{cam_pos[0]:.3f}, {cam_pos[1]:.3f}, {cam_pos[2]:.3f}]", flush=True)

        # 检查位置是否合理
        if not (-0.5 <= position[0] <= 1.2):
            print(f"\n⚠ 警告: X坐标 {position[0]:.3f} 超出合理范围 [-0.5, 1.2]", flush=True)
        if not (-0.7 <= position[1] <= 0.7):
            print(f"\n⚠ 警告: Y坐标 {position[1]:.3f} 超出合理范围 [-0.7, 0.7]", flush=True)
        if not (-0.3 <= position[2] <= 0.5):
            print(f"\n⚠ 警告: Z坐标 {position[2]:.3f} 超出合理范围 [-0.3, 0.5]", flush=True)
            return False

        # 检查置信度
        if confidence < 70:
            print(f"\n⚠ 置信度较低 ({confidence}%)", flush=True)
            response = input("是否继续抓取? (y/n): ").strip().lower()
            if response != 'y':
                print("已取消", flush=True)
                return False

        # 步骤2: 执行抓取
        print(f"\n[3] 执行抓取", flush=True)
        print("-" * 70, flush=True)

        pick_result = primitives.pick(
            arm=arm,
            position=position,
            approach_height=0.12,  # 12cm预抓取高度
            speed=0.3
        )

        print("-" * 70, flush=True)

        if pick_result.get('success'):
            print(f"\n✓ 抓取成功!", flush=True)
            return True
        else:
            print(f"\n✗ 抓取失败: {pick_result.get('message')}", flush=True)
            return False

    except Exception as e:
        print(f"\n✗ 错误: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 断开连接
        #driver.disconnect()
        print("\n" + "=" * 70, flush=True)
        print("测试完成", flush=True)
        print("=" * 70, flush=True)

def main():
    if len(sys.argv) < 2:
        print("用法: python test_d455_pick.py <物体名称> [arm]")
        print("示例:")
        print("  python test_d455_pick.py 魔方")
        print("  python test_d455_pick.py 魔方 left")
        sys.exit(1)

    object_name = sys.argv[1]
    arm = sys.argv[2] if len(sys.argv) > 2 else "right"

    success = asyncio.run(test_d455_pick(object_name, arm))
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
