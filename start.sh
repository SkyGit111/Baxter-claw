#!/bin/bash
# Baxter-Claw 快速启动脚本

echo "=========================================="
echo "Baxter-Claw 快速启动"
echo "=========================================="

# 激活 conda 环境
echo "1. 激活 conda 环境..."
source /home/cothink/miniconda3/etc/profile.d/conda.sh
conda activate baxter-claw

# 进入项目目录
cd /home/cothink/Baxter-claw

# 检查 Bridge Server 是否已运行
if pgrep -f "bridge.server" > /dev/null; then
    echo "2. Bridge Server 已在运行"
    echo "   进程 ID: $(pgrep -f 'bridge.server')"
else
    echo "2. 启动 Bridge Server..."
    python -m bridge.server --config config/baxter.yaml &
    sleep 3

    if pgrep -f "bridge.server" > /dev/null; then
        echo "   ✓ Bridge Server 启动成功"
    else
        echo "   ✗ Bridge Server 启动失败"
        exit 1
    fi
fi

# 测试连接
echo "3. 测试 Bridge Server 连接..."
if curl -s http://localhost:8420/health > /dev/null; then
    echo "   ✓ Bridge Server 响应正常"
    curl -s http://localhost:8420/health | python3 -m json.tool
else
    echo "   ✗ Bridge Server 无响应"
    exit 1
fi

echo ""
echo "=========================================="
echo "启动完成！"
echo "=========================================="
echo ""
echo "Bridge Server: http://localhost:8420"
echo "API 文档: http://localhost:8420/docs"
echo ""
echo "下一步："
echo "1. 启动 OpenClaw (如果未运行)"
echo "2. 使用自然语言控制机器人"
echo ""
echo "示例命令："
echo '  "Enable the robot"'
echo '  "Move to position [0.7, -0.2, 0.3]"'
echo '  "Pick up object at [0.6, -0.3, 0.0]"'
echo '  "Return to home"'
echo ""