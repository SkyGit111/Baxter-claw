#!/usr/bin/env python3
"""
详细调试单次定位的脚本
"""

import asyncio
import sys
from bridge.drivers.baxter_driver import BaxterDriver
from bridge.vlm_client import VLMClient
from bridge.safety import SafetyValidator
from bridge.multi_view_vlm import MultiViewVLMCoordinator

async def debug_single_localization(object_name: str):
    """详细调试单次定位"""

    print("=" * 70)
    print(f"详细调试定位: {object_name}")
    print("=" * 70)

    # 初始化
    print("\n[1] 初始化组件...")
    driver = BaxterDriver(use_depth_camera=True)
    vlm = VLMClient(provider='qwen')
    safety = SafetyValidator(config_path='config/baxter.yaml')

    print("  连接Baxter...")
    if not driver.connect():
        print("  ✗ 连接失败")
        return

    print("  ✓ Baxter已连接")

    # 创建多视角协调器
    coordinator = MultiViewVLMCoordinator(
        driver=driver,
        vlm_client=vlm,
        safety_validator=safety,
        debug=True  # 启用调试模式
    )

    # 执行定位
    print(f"\n[2] 执行多视角定位: {object_name}")
    print("-" * 70)

    # 临时禁用头部相机
    print("  注意: 跳过头部相机（临时禁用）")
    coordinator._head_camera_available = False

    result = await coordinator.locate_object_multiview(
        object_name=object_name,
        arm="right",
        use_wrist_refinement=False  # 先只测试Phase 1
    )

    print("-" * 70)

    # 分析结果
    print(f"\n[3] 结果分析:")

    if not result or not result.get('found'):
        print("  ✗ 未找到物体")
        if result:
            print(f"  原因: {result.get('message', '未知')}")
        return

    print("  ✓ 找到物体")
    print()

    # 显示详细信息
    print("  位置信息:")
    if 'position_camera_frame' in result:
        print(f"    相机坐标系: {result['position_camera_frame']}")
    print(f"    基座坐标系: {result['position']}")
    print()

    print("  置信度:")
    print(f"    {result.get('confidence', 0)}%")
    print()

    print("  描述:")
    print(f"    {result.get('description', 'N/A')}")
    print()

    if 'bounding_box' in result and result['bounding_box']:
        bbox = result['bounding_box']
        print("  边界框:")
        print(f"    左上: ({bbox[0]}, {bbox[1]})")
        print(f"    右下: ({bbox[2]}, {bbox[3]})")
        print(f"    宽度: {bbox[2] - bbox[0]}px")
        print(f"    高度: {bbox[3] - bbox[1]}px")
        print()

    print("  验证状态:")
    print(f"    多视角验证: {result.get('multi_view_validated', False)}")
    print(f"    手腕验证: {result.get('wrist_validated', False)}")
    print(f"    坐标转换: {result.get('coordinate_transformed', False)}")
    print()

    # 检查调试图像
    print("[4] 调试图像:")
    import os
    debug_images = [
        "debug_d455_phase1_annotated.jpg",
        "debug_d455_phase1_depth_annotated.jpg",
        "debug_d455_phase1_raw.jpg",
        "debug_d455_phase1_processed.jpg",
        "debug_d455_phase1_depth.jpg"
    ]

    for img in debug_images:
        if os.path.exists(img):
            size = os.path.getsize(img) / 1024
            print(f"  ✓ {img} ({size:.1f} KB)")
        else:
            print(f"  ✗ {img} (未生成)")

    print()
    print("=" * 70)
    print("调试完成！")
    print()
    print("下一步:")
    print("  1. 查看调试图像，检查边界框是否准确")
    print("  2. 查看深度图，检查深度质量")
    print("  3. 对比相机坐标系和基座坐标系的位置")
    print("  4. 如果位置偏差大，手动测量实际位置进行对比")
    print("=" * 70)

    # 断开连接
    #driver.disconnect()

def main():
    if len(sys.argv) < 2:
        print("用法: python debug_localization.py <物体名称>")
        print("示例: python debug_localization.py 魔方")
        sys.exit(1)

    object_name = sys.argv[1]
    asyncio.run(debug_single_localization(object_name))

if __name__ == "__main__":
    main()
