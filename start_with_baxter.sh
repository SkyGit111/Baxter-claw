#!/bin/bash
# Baxter-Claw 启动脚本
# 此脚本会自动配置 ROS 环境并启动 Bridge Server

echo "=========================================="
echo "Baxter-Claw 启动脚本"
echo "=========================================="
echo ""

# 检查是否在正确的目录
if [ ! -f "bridge/server.py" ]; then
    echo "✗ 错误: 请在 Baxter-claw 项目根目录运行此脚本"
    exit 1
fi

# 检查 baxter.sh 是否存在
if [ ! -f ~/catkin_ws/baxter.sh ]; then
    echo "✗ 错误: ~/catkin_ws/baxter.sh 不存在"
    echo "  请确认 ROS 工作空间已正确配置"
    exit 1
fi

# 检查 conda 环境
if [ ! -d ~/miniconda3/envs/baxter-claw ]; then
    echo "✗ 错误: baxter-claw conda 环境不存在"
    echo "  请先创建环境: conda create -n baxter-claw python=3.8"
    exit 1
fi

echo "步骤 1: 配置 ROS 环境..."
cd ~/catkin_ws
source ./baxter.sh
echo "  ✓ ROS 环境已配置"

echo ""
echo "步骤 2: 激活 conda 环境..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate baxter-claw
echo "  ✓ conda 环境已激活"

echo ""
echo "步骤 3: 返回项目目录..."
cd ~/Baxter-claw
echo "  ✓ 当前目录: $(pwd)"

echo ""
echo "步骤 4: 检查 Baxter 连接..."
if rostopic list | grep -q "/robot/"; then
    echo "  ✓ Baxter 连接正常"
else
    echo "  ✗ 警告: 未检测到 Baxter 话题"
    echo "  请确认 Baxter 已开机并完全启动"
    echo ""
    echo "  继续启动? (y/n): "
    read -r response
    if [ "$response" != "y" ]; then
        echo "  启动已取消"
        exit 1
    fi
fi

echo ""
echo "步骤 5: 检查深度相机..."
if lsusb | grep -q "8086:0b5c"; then
    echo "  ✓ D455 深度相机已连接"
else
    echo "  ⚠ 警告: 未检测到 D455 深度相机"
    echo "  系统将在没有深度相机的情况下运行"
fi

echo ""
echo "=========================================="
echo "启动 Bridge Server"
echo "=========================================="
echo ""
echo "配置信息:"
echo "  - 驱动类型: baxter (真机)"
echo "  - 深度相机: 已启用"
echo "  - VLM 提供商: qwen"
echo "  - 服务器端口: 8420"
echo ""
echo "启动中..."
echo ""

# 启动 Bridge Server
python -m bridge.server

# 如果服务器退出
echo ""
echo "=========================================="
echo "Bridge Server 已停止"
echo "=========================================="