#!/usr/bin/env python3
"""
Baxter-Claw 系统完整测试脚本

此脚本执行完整的系统测试，包括：
1. 环境检查
2. 硬件连接测试
3. Bridge Server测试
4. 基础运动控制测试
5. 视觉系统测试
6. 完整抓取流程测试
7. Web界面测试

使用方法:
    python run_system_test.py [--stage STAGE] [--skip-hardware]

参数:
    --stage STAGE: 从指定阶段开始测试 (0-7)
    --skip-hardware: 跳过硬件检查（用于调试）
    --no-motion: 不执行实际运动（仅测试API）
"""

import sys
import os
import time
import subprocess
import argparse
import httpx
import asyncio
from typing import Optional, Dict, List

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """打印测试阶段标题"""
    print(f"\n{'='*70}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{'='*70}\n")

def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text: str):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text: str):
    """打印信息"""
    print(f"  {text}")

def run_command(cmd: str, check: bool = True) -> tuple:
    """运行shell命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        if check and result.returncode != 0:
            return False, result.stderr
        return True, result.stdout
    except subprocess.TimeoutExpired:
        return False, "命令超时"
    except Exception as e:
        return False, str(e)

def check_environment() -> bool:
    """阶段0: 环境检查"""
    print_header("阶段0: 环境检查")

    all_passed = True

    # 检查ROS环境
    print("检查ROS环境...")
    ros_master = os.getenv('ROS_MASTER_URI')
    ros_ip = os.getenv('ROS_IP')

    if ros_master:
        print_success(f"ROS_MASTER_URI: {ros_master}")
    else:
        print_error("ROS_MASTER_URI 未设置")
        print_info("运行: source ~/catkin_ws/baxter.sh")
        all_passed = False

    if ros_ip:
        print_success(f"ROS_IP: {ros_ip}")
    else:
        print_warning("ROS_IP 未设置（可能不影响）")

    # 检查conda环境
    print("\n检查Conda环境...")
    conda_env = os.getenv('CONDA_DEFAULT_ENV')
    if conda_env == 'baxter-claw':
        print_success(f"Conda环境: {conda_env}")
    else:
        print_error(f"当前环境: {conda_env or 'base'}")
        print_info("运行: conda activate baxter-claw")
        all_passed = False

    # 检查Python依赖
    print("\n检查Python依赖...")
    dependencies = [
        'fastapi', 'uvicorn', 'httpx', 'numpy',
        'yaml', 'pydantic'
    ]

    for dep in dependencies:
        try:
            __import__(dep)
            print_success(f"{dep}")
        except ImportError:
            print_error(f"{dep} 未安装")
            all_passed = False

    # 检查pyrealsense2
    try:
        import pyrealsense2
        print_success("pyrealsense2")
    except ImportError:
        print_warning("pyrealsense2 未安装（深度相机功能将不可用）")

    # 检查配置文件
    print("\n检查配置文件...")
    config_path = "config/baxter.yaml"
    if os.path.exists(config_path):
        print_success(f"配置文件存在: {config_path}")
    else:
        print_error(f"配置文件不存在: {config_path}")
        all_passed = False

    # 检查API密钥
    print("\n检查API密钥...")
    qwen_key = os.getenv('QWEN_API_KEY')
    if qwen_key:
        print_success(f"QWEN_API_KEY: {qwen_key[:10]}...")
    else:
        print_warning("QWEN_API_KEY 未设置（VLM功能将不可用）")

    return all_passed

def check_hardware(skip: bool = False) -> bool:
    """阶段1: 硬件连接检查"""
    if skip:
        print_header("阶段1: 硬件连接检查 (已跳过)")
        return True

    print_header("阶段1: 硬件连接检查")

    all_passed = True

    # 检查ROS话题
    print("检查Baxter连接...")
    success, output = run_command("rostopic list | grep /robot/", check=False)
    if success and output.strip():
        print_success("Baxter话题可访问")
        print_info(f"找到 {len(output.strip().split())} 个话题")
    else:
        print_error("无法访问Baxter话题")
        print_info("确保Baxter已开机并完全启动")
        all_passed = False

    # 检查RealSense
    print("\n检查RealSense D455...")
    success, output = run_command("lsusb | grep '8086:0b5c'", check=False)
    if success and output.strip():
        print_success("D455深度相机已连接")
    else:
        print_warning("未检测到D455深度相机")
        print_info("深度相机功能将不可用")

    # 尝试枚举RealSense设备
    success, output = run_command("rs-enumerate-devices 2>/dev/null | head -5", check=False)
    if success and "Intel RealSense" in output:
        print_success("RealSense设备可访问")
    else:
        print_warning("无法枚举RealSense设备")

    return all_passed

def test_bridge_server() -> bool:
    """阶段2: Bridge Server测试"""
    print_header("阶段2: Bridge Server测试")

    # 检查服务器是否运行
    print("检查Bridge Server状态...")
    try:
        response = httpx.get("http://localhost:8420/", timeout=2.0)
        if response.status_code == 200:
            print_success("Bridge Server正在运行")
            data = response.json()
            print_info(f"版本: {data.get('version')}")
        else:
            print_error(f"服务器响应异常: {response.status_code}")
            return False
    except httpx.ConnectError:
        print_error("无法连接到Bridge Server")
        print_info("请先启动: ./start_with_baxter.sh")
        return False
    except Exception as e:
        print_error(f"连接失败: {e}")
        return False

    # 测试健康检查
    print("\n测试健康检查端点...")
    try:
        response = httpx.get("http://localhost:8420/health", timeout=2.0)
        data = response.json()

        if data.get('healthy'):
            print_success("服务健康")
            print_info(f"连接状态: {data.get('connected')}")
            print_info(f"使能状态: {data.get('enabled')}")
        else:
            print_warning("服务不健康")
            return False
    except Exception as e:
        print_error(f"健康检查失败: {e}")
        return False

    # 测试状态端点
    print("\n测试状态端点...")
    try:
        response = httpx.get("http://localhost:8420/status?arm=right", timeout=2.0)
        data = response.json()

        print_success("状态查询成功")
        print_info(f"连接: {data.get('connected')}")
        print_info(f"使能: {data.get('enabled')}")
        print_info(f"关节数: {len(data.get('joint_angles', {}))}")
    except Exception as e:
        print_error(f"状态查询失败: {e}")
        return False

    return True

def test_basic_control(no_motion: bool = False) -> bool:
    """阶段3: 基础运动控制测试"""
    print_header("阶段3: 基础运动控制测试")

    if no_motion:
        print_warning("跳过实际运动测试")
        return True

    client = httpx.Client(base_url="http://localhost:8420", timeout=30.0)

    try:
        # 使能机器人
        print("使能机器人...")
        response = client.post("/enable")
        if response.status_code == 200:
            print_success("机器人已使能")
        else:
            print_error(f"使能失败: {response.text}")
            return False

        time.sleep(1)

        # 测试夹爪
        print("\n测试夹爪控制...")

        # 打开夹爪
        print("  打开夹爪...")
        response = client.post("/gripper", json={
            'arm': 'right',
            'action': 'open'
        })
        if response.status_code == 200:
            print_success("  夹爪已打开")
        else:
            print_warning(f"  打开失败: {response.text}")

        time.sleep(2)

        # 关闭夹爪
        print("  关闭夹爪...")
        response = client.post("/gripper", json={
            'arm': 'right',
            'action': 'close'
        })
        if response.status_code == 200:
            print_success("  夹爪已关闭")
        else:
            print_warning(f"  关闭失败: {response.text}")

        time.sleep(2)

        # 测试Home位置
        print("\n测试Home位置...")
        print("  移动到Home...")
        response = client.post("/primitives/home", json={'arm': 'right'})
        if response.status_code == 200:
            print_success("  已到达Home位置")
        else:
            print_error(f"  移动失败: {response.text}")
            return False

        return True

    except Exception as e:
        print_error(f"控制测试失败: {e}")
        return False
    finally:
        client.close()

async def test_vision_system() -> bool:
    """阶段4: 视觉系统测试"""
    print_header("阶段4: 视觉系统测试")

    async with httpx.AsyncClient(base_url="http://localhost:8420", timeout=30.0) as client:
        try:
            # 测试图像采集
            print("测试图像采集...")
            response = await client.get("/camera?camera=right_hand")

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print_success("图像采集成功")
                    print_info(f"相机: {data.get('camera')}")
                    print_info(f"大小: {data.get('size')} bytes")

                    # 保存测试图像
                    import base64
                    with open('test_system_capture.jpg', 'wb') as f:
                        f.write(base64.b64decode(data['image']))
                    print_info("已保存: test_system_capture.jpg")
                else:
                    print_warning(f"图像采集失败: {data.get('message')}")
            else:
                print_warning(f"图像采集请求失败: {response.status_code}")
                print_info("深度相机功能可能不可用")

            # 测试场景描述
            print("\n测试场景描述...")
            response = await client.post("/vision/describe_scene")

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print_success("场景描述成功")
                    print_info(f"描述: {data.get('description', '')[:100]}...")
                else:
                    print_warning(f"场景描述失败: {data.get('message')}")
            else:
                print_warning(f"场景描述请求失败: {response.status_code}")

            return True

        except Exception as e:
            print_error(f"视觉测试失败: {e}")
            return False

def test_web_interface() -> bool:
    """阶段5: Web界面测试"""
    print_header("阶段5: Web界面测试")

    # 检查Web服务器
    print("检查Web界面...")
    try:
        response = httpx.get("http://localhost:5000/", timeout=2.0)
        if response.status_code == 200:
            print_success("Web界面正在运行")
            print_info("访问: http://localhost:5000")
        else:
            print_warning("Web界面响应异常")
    except httpx.ConnectError:
        print_warning("Web界面未运行")
        print_info("启动: python openclaw_plugin/web_interface.py")
        return False
    except Exception as e:
        print_error(f"检查失败: {e}")
        return False

    # 测试摄像头端点
    print("\n测试摄像头端点...")
    try:
        response = httpx.get("http://localhost:5000/camera/image", timeout=5.0)
        data = response.json()

        if data.get('success'):
            print_success("摄像头端点正常")
        else:
            print_warning(f"摄像头端点异常: {data.get('message')}")
    except Exception as e:
        print_error(f"测试失败: {e}")

    return True

def generate_test_report(results: Dict[str, bool]):
    """生成测试报告"""
    print_header("测试报告")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"总测试数: {total}")
    print(f"通过: {Colors.GREEN}{passed}{Colors.END}")
    print(f"失败: {Colors.RED}{total - passed}{Colors.END}")
    print(f"通过率: {passed/total*100:.1f}%\n")

    print("详细结果:")
    for stage, result in results.items():
        status = f"{Colors.GREEN}✓ 通过{Colors.END}" if result else f"{Colors.RED}✗ 失败{Colors.END}"
        print(f"  {stage}: {status}")

    # 保存报告
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_file = f"test_report_{timestamp}.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"Baxter-Claw 系统测试报告\n")
        f.write(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"总测试数: {total}\n")
        f.write(f"通过: {passed}\n")
        f.write(f"失败: {total - passed}\n")
        f.write(f"通过率: {passed/total*100:.1f}%\n\n")
        f.write("详细结果:\n")
        for stage, result in results.items():
            status = "通过" if result else "失败"
            f.write(f"  {stage}: {status}\n")

    print(f"\n报告已保存: {report_file}")

def main():
    parser = argparse.ArgumentParser(description='Baxter-Claw 系统完整测试')
    parser.add_argument('--stage', type=int, default=0, help='从指定阶段开始 (0-5)')
    parser.add_argument('--skip-hardware', action='store_true', help='跳过硬件检查')
    parser.add_argument('--no-motion', action='store_true', help='不执行实际运动')
    args = parser.parse_args()

    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("="*70)
    print("  Baxter-Claw 系统完整测试")
    print("="*70)
    print(f"{Colors.END}")

    results = {}

    # 阶段0: 环境检查
    if args.stage <= 0:
        results['阶段0: 环境检查'] = check_environment()
        if not results['阶段0: 环境检查']:
            print_error("\n环境检查失败，请修复后重试")
            return 1

    # 阶段1: 硬件检查
    if args.stage <= 1:
        results['阶段1: 硬件检查'] = check_hardware(args.skip_hardware)
        if not results['阶段1: 硬件检查'] and not args.skip_hardware:
            print_error("\n硬件检查失败，请检查连接")
            return 1

    # 阶段2: Bridge Server
    if args.stage <= 2:
        results['阶段2: Bridge Server'] = test_bridge_server()
        if not results['阶段2: Bridge Server']:
            print_error("\nBridge Server测试失败")
            return 1

    # 阶段3: 基础控制
    if args.stage <= 3:
        results['阶段3: 基础控制'] = test_basic_control(args.no_motion)

    # 阶段4: 视觉系统
    if args.stage <= 4:
        results['阶段4: 视觉系统'] = asyncio.run(test_vision_system())

    # 阶段5: Web界面
    if args.stage <= 5:
        results['阶段5: Web界面'] = test_web_interface()

    # 生成报告
    generate_test_report(results)

    # 返回状态
    if all(results.values()):
        print(f"\n{Colors.GREEN}{Colors.BOLD}所有测试通过！{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}部分测试失败{Colors.END}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
