#!/bin/bash
# 启动脚本：先启动ROS和Baxter，然后运行多视角VLM测试

echo "=========================================="
echo "启动多视角VLM测试系统"
echo "=========================================="

# 1. 检查ROS环境
echo ""
echo "[1] 检查ROS环境..."
if [ -z "$ROS_MASTER_URI" ]; then
    echo "错误：ROS环境未设置"
    echo "请先运行: source /opt/ros/noetic/setup.bash"
    exit 1
fi

# 2. 检查ROS master
echo ""
echo "[2] 检查ROS master..."
if ! rostopic list &>/dev/null; then
    echo "ROS master未运行，正在启动..."
    roscore &
    ROSCORE_PID=$!
    sleep 3
    echo "ROS master已启动 (PID: $ROSCORE_PID)"
else
    echo "ROS master已运行"
fi

# 3. 检查Baxter连接
echo ""
echo "[3] 检查Baxter连接..."
if ! rostopic list | grep -q "/robot/state"; then
    echo "警告：Baxter未连接"
    echo "请确保："
    echo "  1. Baxter机器人已开机"
    echo "  2. 网络连接正常"
    echo "  3. 已设置 ROS_MASTER_URI 指向Baxter"
    echo ""
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "Baxter已连接"
fi

# 4. 运行测试
echo ""
echo "[4] 运行多视角VLM测试..."
echo "=========================================="
echo ""

python -u test_multiview_vlm.py

# 清理
if [ ! -z "$ROSCORE_PID" ]; then
    echo ""
    echo "清理：关闭ROS master..."
    kill $ROSCORE_PID 2>/dev/null
fi
