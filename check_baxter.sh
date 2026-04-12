#!/bin/bash
# Baxter 连接快速检查脚本

echo "=========================================="
echo "Baxter 连接快速检查"
echo "=========================================="
echo ""

# 检查 1: Baxter 网络连接
echo "检查 1: Baxter 网络连接..."
if ping -c 2 011A08P0014.local > /dev/null 2>&1; then
    echo "  ✓ Baxter 网络连接正常 (192.168.1.100)"
else
    echo "  ✗ 无法连接到 Baxter"
    echo "  请确认 Baxter 已开机"
    exit 1
fi

# 检查 2: D455 深度相机
echo ""
echo "检查 2: D455 深度相机..."
if lsusb | grep -q "8086:0b5c"; then
    echo "  ✓ D455 已连接"
else
    echo "  ✗ D455 未检测到"
    echo "  请检查 USB 连接"
fi

# 检查 3: ROS 环境
echo ""
echo "检查 3: ROS 环境..."
if [ -f ~/catkin_ws/baxter.sh ]; then
    echo "  ✓ baxter.sh 存在"
else
    echo "  ✗ baxter.sh 不存在"
    exit 1
fi

# 检查 4: Conda 环境
echo ""
echo "检查 4: Conda 环境..."
if [ -d /home/cothink/miniconda3/envs/baxter-claw ]; then
    echo "  ✓ baxter-claw 环境存在"
else
    echo "  ✗ baxter-claw 环境不存在"
    exit 1
fi

echo ""
echo "=========================================="
echo "基础检查完成"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 确认 Baxter 已完全启动"
echo "2. 运行以下命令测试 ROS 连接："
echo ""
echo "   cd ~/catkin_ws"
echo "   ./baxter.sh"
echo "   rostopic list"
echo ""
echo "3. 如果看到 /robot/... 话题，说明连接成功！"
echo ""