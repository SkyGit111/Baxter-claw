#!/bin/bash
# 停止 Baxter-Claw Bridge Server

echo "停止 Bridge Server..."

if pgrep -f "bridge.server" > /dev/null; then
    pkill -f "bridge.server"
    sleep 1

    if pgrep -f "bridge.server" > /dev/null; then
        echo "✗ 无法停止 Bridge Server，尝试强制终止..."
        pkill -9 -f "bridge.server"
    else
        echo "✓ Bridge Server 已停止"
    fi
else
    echo "Bridge Server 未运行"
fi