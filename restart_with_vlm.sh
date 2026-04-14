#!/bin/bash
# 设置环境变量并重启Bridge Server

echo "=========================================="
echo "设置QWEN_API_KEY并重启服务"
echo "=========================================="
echo ""

# 设置API密钥
export QWEN_API_KEY="sk-bd990626c84a4142b9581f13c5317522"
echo "✓ QWEN_API_KEY已设置"

# 检查Bridge Server是否运行
if lsof -i :8420 >/dev/null 2>&1; then
    echo ""
    echo "停止现有Bridge Server..."
    PID=$(lsof -ti :8420)
    kill $PID 2>/dev/null
    sleep 2
    echo "✓ 已停止进程 $PID"
fi

echo ""
echo "启动Bridge Server（带VLM支持）..."
echo ""

# 启动Bridge Server
cd ~/Baxter-claw
python -m bridge.server
