#!/bin/bash
# 一键修复 API key 问题

echo "=========================================="
echo "修复 QWEN_API_KEY 配置"
echo "=========================================="
echo ""

CORRECT_KEY="sk-fdb3645b56b44749a3c4a3f86af2edb0"
WRONG_KEY="sk-bd990626c84a4142b9581f13c5317522"

echo "正确的 API key: ${CORRECT_KEY:0:15}..."
echo "错误的 API key: ${WRONG_KEY:0:15}..."
echo ""

# 1. 修复当前 shell
echo "[1/4] 修复当前 shell 环境变量..."
export QWEN_API_KEY="$CORRECT_KEY"
echo "✓ 当前 shell 已设置正确的 key"
echo ""

# 2. 检查并修复 ~/.bashrc
echo "[2/4] 检查 ~/.bashrc..."
if grep -q "$WRONG_KEY" ~/.bashrc; then
    echo "⚠ 发现错误的 key，正在修复..."
    sed -i "s/$WRONG_KEY/$CORRECT_KEY/g" ~/.bashrc
    echo "✓ ~/.bashrc 已修复"
else
    echo "✓ ~/.bashrc 正确"
fi
echo ""

# 3. 检查并修复所有配置文件
echo "[3/4] 检查项目配置文件..."

# config/baxter.yaml
if grep -q "$WRONG_KEY" config/baxter.yaml 2>/dev/null; then
    echo "⚠ 修复 config/baxter.yaml..."
    sed -i "s/$WRONG_KEY/$CORRECT_KEY/g" config/baxter.yaml
    echo "✓ config/baxter.yaml 已修复"
fi

# openclaw_plugin/config.yaml
if grep -q "$WRONG_KEY" openclaw_plugin/config.yaml 2>/dev/null; then
    echo "⚠ 修复 openclaw_plugin/config.yaml..."
    sed -i "s/$WRONG_KEY/$CORRECT_KEY/g" openclaw_plugin/config.yaml
    echo "✓ openclaw_plugin/config.yaml 已修复"
fi

# openclaw_plugin/web_interface.py
if grep -q "$WRONG_KEY" openclaw_plugin/web_interface.py 2>/dev/null; then
    echo "⚠ 修复 openclaw_plugin/web_interface.py..."
    sed -i "s/$WRONG_KEY/$CORRECT_KEY/g" openclaw_plugin/web_interface.py
    echo "✓ openclaw_plugin/web_interface.py 已修复"
fi

echo "✓ 所有配置文件检查完成"
echo ""

# 4. 验证
echo "[4/4] 验证修复结果..."
echo "当前环境变量: ${QWEN_API_KEY:0:15}..."

if [ "$QWEN_API_KEY" = "$CORRECT_KEY" ]; then
    echo "✓ API key 正确"
else
    echo "✗ API key 仍然错误"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ 修复完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 重启 Bridge Server: ./start_bridge.sh"
echo "  2. 重启 Web 界面: python openclaw_plugin/web_interface.py"
echo ""
echo "如果还有问题，请运行："
echo "  source ~/.bashrc"
echo "  然后重新启动服务"
echo ""
