#!/usr/bin/env python3
"""
VLM+D455 定位精度系统测试脚本

基于 debug_localization.py 的逻辑，直接使用底层定位流程
测试不同位置的偏移量，分析是否存在固定偏移

测试流程：
1. 使用 VLM+D455 定位物体（完整的坐标转换）
2. 等待手动将右手移到物体位置
3. 读取右手末端执行器实际位姿
4. 计算偏移量
5. 等待移动物体到新位置
6. 重复测试
"""

import asyncio
import sys
import csv
from datetime import datetime
from typing import List, Dict
import numpy as np

from bridge.drivers.baxter_driver import BaxterDriver
from bridge.vlm_client import VLMClient
from bridge.safety import SafetyValidator
from bridge.multi_view_vlm import MultiViewVLMCoordinator


class VLMLocalizationTester:
    """VLM+D455 定位精度测试器"""

    def __init__(self):
        """初始化测试器"""
        self.driver = None
        self.vlm = None
        self.safety = None
        self.coordinator = None
        self.test_data: List[Dict] = []

    async def initialize(self):
        """初始化组件"""
        print("=" * 70)
        print("初始化测试环境")
        print("=" * 70)

        print("\n[1] 初始化组件...")
        self.driver = BaxterDriver(use_depth_camera=True)
        self.vlm = VLMClient(provider='qwen', api_key='sk-fdb3645b56b44749a3c4a3f86af2edb0')
        self.safety = SafetyValidator(config_path='config/baxter.yaml')

        print("  连接 Baxter...")
        if not self.driver.connect():
            print("  ✗ 连接失败")
            return False

        print("  ✓ Baxter 已连接")

        # 检查 D455
        if not self.driver.has_depth_camera():
            print("  ✗ D455 深度相机不可用")
            return False

        print("  ✓ D455 深度相机可用")

        # 创建多视角协调器
        self.coordinator = MultiViewVLMCoordinator(
            driver=self.driver,
            vlm_client=self.vlm,
            safety_validator=self.safety,
            debug=True  # 启用调试模式
        )

        # 临时禁用头部相机（视角差）
        print("  注意: 禁用头部相机（视角差）")
        self.coordinator._head_camera_available = False

        print("\n✅ 初始化完成")
        return True

    async def locate_object(self, object_name: str) -> Dict:
        """使用 VLM+D455 定位物体（完整流程）

        Args:
            object_name: 物体名称

        Returns:
            定位结果字典
        """
        print(f"\n{'='*70}")
        print(f"🔍 定位物体: {object_name}")
        print(f"{'='*70}")

        try:
            # 执行多视角定位（使用完整的坐标转换）
            result = await self.coordinator.locate_object_multiview(
                object_name=object_name,
                arm="right",
                use_wrist_refinement=False  # 只用 D455，不用手腕精修
            )

            if not result or not result.get('found'):
                print("  ✗ 未找到物体")
                if result:
                    print(f"  原因: {result.get('message', '未知')}")
                return {'success': False}

            print("  ✓ 找到物体")
            print()

            # 显示详细信息
            position_camera = result.get('position_camera_frame', [])
            position_base = result.get('position', [])
            confidence = result.get('confidence', 0)
            bbox = result.get('bounding_box', [])

            print("  位置信息:")
            if position_camera:
                print(f"    相机坐标系: [{position_camera[0]:.4f}, {position_camera[1]:.4f}, {position_camera[2]:.4f}]")
            print(f"    基座坐标系: [{position_base[0]:.4f}, {position_base[1]:.4f}, {position_base[2]:.4f}]")
            print()

            print(f"  置信度: {confidence}%")
            print()

            if bbox:
                print(f"  边界框: [{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}]")
                print(f"    中心像素: ({(bbox[0]+bbox[2])//2}, {(bbox[1]+bbox[3])//2})")
                print()

            print(f"  坐标转换: {result.get('coordinate_transformed', False)}")
            print()

            return {
                'success': True,
                'position': position_base,
                'position_camera': position_camera,
                'confidence': confidence,
                'bbox': bbox,
                'coordinate_transformed': result.get('coordinate_transformed', False)
            }

        except Exception as e:
            print(f"  ✗ 定位出错: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False}

    def get_right_arm_pose(self) -> Dict:
        """获取右手末端执行器当前位姿

        Returns:
            位姿字典，包含 position 和 orientation
        """
        try:
            print("\n📍 读取右手末端执行器位姿...")

            # 获取右手当前位姿 [x, y, z, roll, pitch, yaw]
            pose = self.driver.get_endpoint_pose('right')

            if pose and len(pose) >= 6:
                position = pose[0:3]  # [x, y, z]
                rpy = pose[3:6]       # [roll, pitch, yaw]

                print(f"  位置: [{position[0]:.4f}, {position[1]:.4f}, {position[2]:.4f}]")
                print(f"  姿态 (RPY): [{rpy[0]:.4f}, {rpy[1]:.4f}, {rpy[2]:.4f}]")

                return {
                    'success': True,
                    'position': position,
                    'rpy': rpy
                }
            else:
                print("  ✗ 无法获取位姿")
                return {'success': False}

        except Exception as e:
            print(f"  ✗ 获取位姿失败: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False}

    def calculate_offset(
        self,
        vlm_position: List[float],
        actual_position: List[float]
    ) -> tuple:
        """计算偏移量

        Args:
            vlm_position: VLM+D455 计算的位置（基座坐标系）
            actual_position: 实际位置（右手末端执行器）

        Returns:
            (偏移向量, 偏移距离)
        """
        offset = [
            actual_position[i] - vlm_position[i]
            for i in range(3)
        ]
        distance = np.linalg.norm(offset)
        return offset, distance

    def print_offset_analysis(self, offset: List[float], distance: float):
        """打印偏移量分析"""
        print(f"\n{'='*70}")
        print("📊 偏移量分析")
        print(f"{'='*70}")
        print(f"  X 轴偏移: {offset[0]:+.4f} m ({offset[0]*100:+.2f} cm)")
        print(f"  Y 轴偏移: {offset[1]:+.4f} m ({offset[1]*100:+.2f} cm)")
        print(f"  Z 轴偏移: {offset[2]:+.4f} m ({offset[2]*100:+.2f} cm)")
        print(f"  总偏移距离: {distance:.4f} m ({distance*100:.2f} cm)")
        print(f"{'='*70}")

    async def run_single_test(self, object_name: str, test_id: int) -> bool:
        """运行单次测试

        Args:
            object_name: 物体名称
            test_id: 测试编号

        Returns:
            是否成功
        """
        print(f"\n\n{'#'*70}")
        print(f"# 测试 #{test_id}")
        print(f"{'#'*70}")

        # Step 1: 定位物体
        locate_result = await self.locate_object(object_name)
        if not locate_result['success']:
            return False

        vlm_position = locate_result['position']
        position_camera = locate_result.get('position_camera', [])
        confidence = locate_result['confidence']
        bbox = locate_result.get('bbox', [])

        # Step 2: 等待手动移动右手到物体位置
        print(f"\n{'='*70}")
        print("👉 请将右手末端执行器移动到物体位置")
        print("   (移动完成后按 Enter 继续)")
        print(f"{'='*70}")
        input()

        # Step 3: 读取右手实际位姿
        pose_result = self.get_right_arm_pose()
        if not pose_result['success']:
            return False

        actual_position = pose_result['position']
        rpy = pose_result['rpy']

        # Step 4: 计算偏移量
        offset, distance = self.calculate_offset(vlm_position, actual_position)
        self.print_offset_analysis(offset, distance)

        # Step 5: 记录数据
        test_record = {
            'test_id': test_id,
            'timestamp': datetime.now().isoformat(),
            'object_name': object_name,
            'vlm_x': vlm_position[0],
            'vlm_y': vlm_position[1],
            'vlm_z': vlm_position[2],
            'camera_x': position_camera[0] if position_camera else 0,
            'camera_y': position_camera[1] if position_camera else 0,
            'camera_z': position_camera[2] if position_camera else 0,
            'actual_x': actual_position[0],
            'actual_y': actual_position[1],
            'actual_z': actual_position[2],
            'offset_x': offset[0],
            'offset_y': offset[1],
            'offset_z': offset[2],
            'offset_distance': distance,
            'confidence': confidence,
            'bbox_x1': bbox[0] if bbox else 0,
            'bbox_y1': bbox[1] if bbox else 0,
            'bbox_x2': bbox[2] if bbox else 0,
            'bbox_y2': bbox[3] if bbox else 0,
            'roll': rpy[0],
            'pitch': rpy[1],
            'yaw': rpy[2],
        }

        self.test_data.append(test_record)

        return True

    def save_results(self, filename: str = None):
        """保存测试结果到 CSV 文件"""
        if not self.test_data:
            print("⚠️  没有测试数据可保存")
            return

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"vlm_localization_test_{timestamp}.csv"

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'test_id', 'timestamp', 'object_name',
                    'vlm_x', 'vlm_y', 'vlm_z',
                    'camera_x', 'camera_y', 'camera_z',
                    'actual_x', 'actual_y', 'actual_z',
                    'offset_x', 'offset_y', 'offset_z',
                    'offset_distance', 'confidence',
                    'bbox_x1', 'bbox_y1', 'bbox_x2', 'bbox_y2',
                    'roll', 'pitch', 'yaw'
                ]

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.test_data)

            print(f"\n✅ 测试结果已保存到: {filename}")

        except Exception as e:
            print(f"❌ 保存结果失败: {e}")

    def print_statistics(self):
        """打印统计信息"""
        if not self.test_data:
            print("⚠️  没有测试数据")
            return

        print(f"\n{'='*70}")
        print(f"统计分析 (共 {len(self.test_data)} 次测试)")
        print(f"{'='*70}")

        # 计算平均偏移
        avg_offset_x = np.mean([d['offset_x'] for d in self.test_data])
        avg_offset_y = np.mean([d['offset_y'] for d in self.test_data])
        avg_offset_z = np.mean([d['offset_z'] for d in self.test_data])
        avg_distance = np.mean([d['offset_distance'] for d in self.test_data])

        # 计算标准差
        std_offset_x = np.std([d['offset_x'] for d in self.test_data])
        std_offset_y = np.std([d['offset_y'] for d in self.test_data])
        std_offset_z = np.std([d['offset_z'] for d in self.test_data])
        std_distance = np.std([d['offset_distance'] for d in self.test_data])

        # 计算最大/最小偏移
        max_distance = max([d['offset_distance'] for d in self.test_data])
        min_distance = min([d['offset_distance'] for d in self.test_data])

        print(f"\n平均偏移量:")
        print(f"  X: {avg_offset_x:+.4f} m ({avg_offset_x*100:+.2f} cm) ± {std_offset_x*100:.2f} cm")
        print(f"  Y: {avg_offset_y:+.4f} m ({avg_offset_y*100:+.2f} cm) ± {std_offset_y*100:.2f} cm")
        print(f"  Z: {avg_offset_z:+.4f} m ({avg_offset_z*100:+.2f} cm) ± {std_offset_z*100:.2f} cm")
        print(f"\n平均偏移距离: {avg_distance:.4f} m ({avg_distance*100:.2f} cm) ± {std_distance*100:.2f} cm")
        print(f"最大偏移距离: {max_distance:.4f} m ({max_distance*100:.2f} cm)")
        print(f"最小偏移距离: {min_distance:.4f} m ({min_distance*100:.2f} cm)")

        # 判断偏移是否相对固定
        print(f"\n偏移稳定性分析:")
        if std_offset_x < 0.02 and std_offset_y < 0.02 and std_offset_z < 0.02:
            print(f"  ✅ 偏移量相对固定 (标准差 < 2cm)")
            print(f"  建议: 可以使用固定偏移量进行校准")
            print(f"\n  建议校准偏移量:")
            print(f"    X: {avg_offset_x:.4f} m")
            print(f"    Y: {avg_offset_y:.4f} m")
            print(f"    Z: {avg_offset_z:.4f} m")
        else:
            print(f"  ⚠️  偏移量变化较大 (标准差 ≥ 2cm)")
            print(f"  建议: 需要进一步分析偏移与位置的关系")

        # 平均置信度
        avg_confidence = np.mean([d['confidence'] for d in self.test_data])
        print(f"\n平均置信度: {avg_confidence:.1f}%")

        print(f"{'='*70}")

    async def run_interactive_test(self):
        """运行交互式测试"""
        print("=" * 70)
        print("VLM+D455 定位精度系统测试")
        print("=" * 70)

        # 初始化
        if not await self.initialize():
            print("❌ 初始化失败")
            return

        # 输入物体名称
        object_name = input("\n请输入要测试的物体名称 (例如: 蓝色小方块): ").strip()
        if not object_name:
            print("❌ 物体名称不能为空")
            return

        print(f"\n开始测试物体: {object_name}")
        print(f"\n测试流程:")
        print(f"  1. 系统使用 VLM+D455 定位物体（完整坐标转换）")
        print(f"  2. 你手动将右手移到物体位置")
        print(f"  3. 系统读取右手实际位姿并计算偏移")
        print(f"  4. 你移动物体到新位置")
        print(f"  5. 重复测试")
        print(f"\n按 Enter 开始...")
        input()

        test_id = 1
        while True:
            # 运行单次测试
            success = await self.run_single_test(object_name, test_id)

            if success:
                test_id += 1

                # 询问是否继续
                print(f"\n{'='*70}")
                choice = input("继续测试? (y=继续, n=结束, s=查看统计): ").strip().lower()

                if choice == 'n':
                    break
                elif choice == 's':
                    self.print_statistics()
                    choice = input("\n继续测试? (y/n): ").strip().lower()
                    if choice == 'n':
                        break

                if choice == 'y' or choice == '':
                    print(f"\n{'='*70}")
                    print("👉 请将物体移动到桌面的新位置")
                    print("   (移动完成后按 Enter 继续)")
                    print(f"{'='*70}")
                    input()
            else:
                retry = input("\n测试失败，是否重试? (y/n): ").strip().lower()
                if retry != 'y':
                    break

        # 保存结果
        if self.test_data:
            self.print_statistics()
            self.save_results()
        else:
            print("\n⚠️  没有收集到测试数据")


async def main():
    """主函数"""
    tester = VLMLocalizationTester()
    try:
        await tester.run_interactive_test()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
        if tester.test_data:
            print("保存已收集的数据...")
            tester.print_statistics()
            tester.save_results()
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
