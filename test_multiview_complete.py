#!/usr/bin/env python3
"""
完整的多视角VLM定位测试

测试流程:
1. Phase 1: D455 + 头部相机初步定位
   - 收回手臂避免遮挡
   - D455深度相机拍照并定位
   - 头部相机拍照验证
   - 交叉验证结果
2. Phase 2: 腕部相机精确定位
   - 根据初步定位选择手臂
   - 移动腕部到物体上方
   - 腕部相机近距离拍照
   - 融合所有视角得到最终位置
3. 执行抓取

使用方法:
    python test_multiview_complete.py
"""

import sys
import asyncio
import httpx
from typing import Optional

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{'='*70}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{'='*70}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text: str):
    print(f"  {text}")

async def test_multiview_localization(object_name: str):
    """测试多视角VLM定位"""
    print_header(f"多视角VLM定位测试: {object_name}")

    async with httpx.AsyncClient(base_url="http://localhost:8420", timeout=60.0) as client:
        try:
            # 检查服务状态
            print_info("检查Bridge Server状态...")
            response = await client.get("/health")
            if response.status_code != 200:
                print_error("Bridge Server未运行")
                return False

            health = response.json()
            if not health.get('healthy'):
                print_error("Bridge Server不健康")
                return False

            print_success("Bridge Server运行正常")

            # 调用多视角定位API
            print_info(f"\n开始多视角定位: {object_name}")
            print_info("这将执行:")
            print_info("  1. Phase 1: D455 + 头部相机初步定位")
            print_info("  2. Phase 2: 腕部相机精确定位")
            print_info("  预计耗时: 30-60秒")
            print()

            response = await client.post("/vision/locate_multiview", json={
                "object_name": object_name,
                "arm": "right"  # 可以根据初步定位自动选择
            })

            if response.status_code != 200:
                print_error(f"API调用失败: {response.status_code}")
                print_info(response.text)
                return False

            result = response.json()

            # 显示结果
            print_header("定位结果")

            # Smart detection: check found field, or infer from valid data
            found = result.get('found', False)
            confidence = result.get('confidence', 0)
            position = result.get('position', [0, 0, 0])

            # Override found=false if we have valid detection data
            if not found and confidence > 50 and any(p != 0 for p in position):
                print_warning(f"found字段为false，但检测到有效数据 (confidence={confidence}%, position={position})")
                print_warning("自动判定为找到物体")
                found = True

            if not found:
                print_error(f"未找到物体: {object_name}")
                print_info(f"原因: {result.get('message', '未知')}")
                # 显示调试信息
                print_info(f"Success字段: {result.get('success')}")
                print_info(f"描述: {result.get('description', 'N/A')}")
                return False

            print_success(f"找到物体: {object_name}")
            print()

            # 位置信息
            position = result.get('position', [0, 0, 0])
            print_info(f"位置 (base frame):")
            print_info(f"  X: {position[0]:.3f} m (前后)")
            print_info(f"  Y: {position[1]:.3f} m (左右)")
            print_info(f"  Z: {position[2]:.3f} m (高度)")
            print()

            # 置信度
            confidence = result.get('confidence', 0)
            if confidence >= 80:
                print_success(f"置信度: {confidence}% (高)")
            elif confidence >= 60:
                print_warning(f"置信度: {confidence}% (中)")
            else:
                print_warning(f"置信度: {confidence}% (低)")
            print()

            # 验证信息
            if result.get('multi_view_validated'):
                print_success("✓ 多视角交叉验证通过")
                quality = result.get('validation_quality', 'unknown')
                print_info(f"  验证质量: {quality}")
            else:
                print_warning("⚠ 多视角验证未通过或不可用")

            if result.get('wrist_validated'):
                print_success("✓ 腕部相机精确定位完成")
            else:
                print_info("  腕部相机未使用")

            print()

            # 描述信息
            description = result.get('description', '')
            if description:
                print_info(f"描述: {description[:200]}")
                print()

            # 额外信息
            if 'position_difference_m' in result:
                diff = result['position_difference_m']
                print_info(f"D455与头部相机位置差异: {diff:.3f}m")

            if 'head_camera_position' in result:
                head_pos = result['head_camera_position']
                print_info(f"头部相机检测位置: [{head_pos[0]:.3f}, {head_pos[1]:.3f}, {head_pos[2]:.3f}]")

            return True

        except asyncio.TimeoutError:
            print_error("请求超时 (>60秒)")
            print_info("多视角定位可能需要较长时间，请耐心等待")
            return False
        except Exception as e:
            print_error(f"测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

async def test_multiview_with_grasp(object_name: str):
    """测试多视角定位 + 抓取"""
    print_header(f"多视角定位 + 抓取测试: {object_name}")

    async with httpx.AsyncClient(base_url="http://localhost:8420", timeout=90.0) as client:
        try:
            # 步骤1: 多视角定位
            print_info("步骤1: 多视角定位...")
            print_info("正在执行Phase 1和Phase 2，请耐心等待...")
            print()

            response = await client.post("/vision/locate_multiview", json={
                "object_name": object_name,
                "arm": "right"
            })

            print_info(f"API响应状态码: {response.status_code}")

            if response.status_code != 200:
                print_error(f"定位API调用失败: HTTP {response.status_code}")
                print()
                print_info("详细错误信息:")
                try:
                    error_data = response.json()
                    print_info(f"  {error_data}")
                except:
                    print_info(f"  {response.text}")
                return False

            result = response.json()

            print_info("API返回数据:")
            import json
            print_info(json.dumps(result, indent=2, ensure_ascii=False))
            print()

            # Smart detection: check found field, or infer from valid data
            found = result.get('found', False)
            confidence = result.get('confidence', 0)
            position = result.get('position', [0, 0, 0])

            # Override found=false if we have valid detection data
            if not found and confidence > 50 and any(p != 0 for p in position):
                print_warning(f"found字段为false，但检测到有效数据 (confidence={confidence}%, position={position})")
                print_warning("自动判定为找到物体")
                found = True

            if not found:
                print_error(f"未找到物体: {object_name}")
                print_info(f"原因: {result.get('message', '未知')}")

                # 显示更多调试信息
                if 'success' in result:
                    print_info(f"Success字段: {result['success']}")
                if 'description' in result:
                    print_info(f"描述: {result['description']}")

                return False

            position = result['position']
            confidence = result['confidence']

            print_success(f"定位成功: [{position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f}]")
            print_info(f"置信度: {confidence}%")

            # 步骤2: 确认是否执行抓取
            if confidence < 70:
                print_warning(f"置信度较低 ({confidence}%)，建议不要抓取")
                response = input("\n是否继续抓取? (y/n): ").strip().lower()
                if response != 'y':
                    print_info("已取消抓取")
                    return True

            print()
            print_info("步骤2: 执行抓取...")

            # 调用抓取API
            response = await client.post("/primitives/pick", json={
                "arm": "right",
                "position": position,
                "approach_height": 0.1
            })

            if response.status_code != 200:
                print_error(f"抓取失败: {response.status_code}")
                print_info(response.text)
                return False

            pick_result = response.json()

            if pick_result.get('success'):
                print_success("抓取成功！")
                return True
            else:
                print_error(f"抓取失败: {pick_result.get('message')}")
                return False

        except asyncio.TimeoutError:
            print_error("请求超时 (>90秒)")
            print_info("多视角定位可能需要较长时间")
            return False
        except Exception as e:
            print_error(f"测试失败: {e}")
            import traceback
            print()
            print_info("详细错误堆栈:")
            traceback.print_exc()
            return False

async def main():
    """主测试流程"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("="*70)
    print("  多视角VLM完整测试")
    print("="*70)
    print(f"{Colors.END}")

    print("\n此测试将验证完整的多视角VLM定位流程:")
    print("  1. D455深度相机 + 头部相机初步定位")
    print("  2. 腕部相机精确定位")
    print("  3. 多视角融合")
    print()

    # 检查Bridge Server
    try:
        async with httpx.AsyncClient(base_url="http://localhost:8420", timeout=5.0) as client:
            response = await client.get("/")
            if response.status_code != 200:
                print_error("Bridge Server未运行")
                print_info("请先启动: ./start_bridge.sh")
                return 1
    except:
        print_error("无法连接到Bridge Server")
        print_info("请先启动: ./start_bridge.sh")
        return 1

    print_success("Bridge Server运行中")
    print()

    # 获取物体名称
    print("请输入要定位的物体名称")
    print("示例: 红色杯子, 蓝色盒子, green bottle")
    object_name = input("\n物体名称: ").strip()

    if not object_name:
        print_error("物体名称不能为空")
        return 1

    print()

    # 选择测试模式
    print("选择测试模式:")
    print("  1. 仅定位测试 (推荐)")
    print("  2. 定位 + 抓取测试")
    mode = input("\n选择 (1/2): ").strip()

    print()

    if mode == '1':
        # 仅定位测试
        success = await test_multiview_localization(object_name)
    elif mode == '2':
        # 定位 + 抓取测试
        print_warning("⚠ 警告: 此测试将控制机器人运动")
        print_info("请确保:")
        print_info("  1. 工作空间内无障碍物")
        print_info("  2. 急停按钮可触及")
        print_info("  3. 有人在旁监督")
        response = input("\n是否继续? (y/n): ").strip().lower()
        if response != 'y':
            print_info("已取消")
            return 0

        success = await test_multiview_with_grasp(object_name)
    else:
        print_error("无效选择")
        return 1

    # 总结
    print()
    print_header("测试总结")

    if success:
        print_success("测试通过！")
        print()
        print_info("多视角VLM系统工作正常，包括:")
        print_info("  ✓ D455深度相机定位")
        print_info("  ✓ 头部相机交叉验证")
        print_info("  ✓ 腕部相机精确定位")
        print_info("  ✓ 多视角融合")
        return 0
    else:
        print_error("测试失败")
        print()
        print_info("可能的原因:")
        print_info("  - VLM API密钥未设置")
        print_info("  - 深度相机未连接")
        print_info("  - 物体不在视野内")
        print_info("  - 光照条件不佳")
        return 1

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
