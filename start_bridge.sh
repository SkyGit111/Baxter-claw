#!/bin/bash
# Baxter-Claw 简化启动脚本
# 假设ROS和Conda环境已经配置好

echo "=========================================="
echo "Baxter-Claw Bridge Server 启动"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查是否在项目根目录
if [ ! -f "bridge/server.py" ]; then
    echo -e "${RED}✗ 错误: 请在 Baxter-claw 项目根目录运行此脚本${NC}"
    exit 1
fi

# 显示当前环境
echo -e "${BLUE}当前环境:${NC}"
echo "  工作目录: $(pwd)"
echo "  Python: $(which python)"
echo "  Conda环境: ${CONDA_DEFAULT_ENV:-未激活}"
echo "  ROS_MASTER_URI: ${ROS_MASTER_URI:-未设置}"
echo ""

# 检查ROS环境
if [ -z "$ROS_MASTER_URI" ]; then
    echo -e "${RED}✗ ROS环境未配置${NC}"
    echo "  请先运行: source ~/catkin_ws/baxter.sh"
    exit 1
fi

# 检查Conda环境
if [ "$CONDA_DEFAULT_ENV" != "baxter-claw" ]; then
    echo -e "${YELLOW}⚠ 警告: 当前不在 baxter-claw 环境${NC}"
    echo "  当前环境: ${CONDA_DEFAULT_ENV:-base}"
    echo "  建议运行: conda activate baxter-claw"
    echo ""
    read -p "是否继续? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 快速检查（不阻塞）
echo -e "${BLUE}快速检查:${NC}"

# 检查Python依赖
echo -n "  检查Python依赖... "
if python -c "import fastapi, uvicorn, httpx" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ 缺少依赖${NC}"
    echo "  运行: pip install fastapi uvicorn httpx"
    exit 1
fi

# 检查配置文件
echo -n "  检查配置文件... "
if [ -f "config/baxter.yaml" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ 配置文件不存在${NC}"
    exit 1
fi

# 检查端口占用
echo -n "  检查端口8420... "
if lsof -i :8420 >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ 端口已被占用${NC}"
    echo ""
    echo "  端口8420已被占用，可能Bridge Server已在运行"
    read -p "  是否停止现有进程? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        PID=$(lsof -ti :8420)
        kill $PID 2>/dev/null
        sleep 1
        echo "  已停止进程 $PID"
    else
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}启动 Bridge Server${NC}"
echo "=========================================="
echo ""

# 设置API key
export QWEN_API_KEY=sk-fdb3645b56b44749a3c4a3f86af2edb0

echo "配置信息:"
echo "  - 驱动类型: baxter (真机)"
echo "  - 服务器端口: 8420"
echo "  - API文档: http://localhost:8420/docs"
echo ""
echo "启动后可以:"
echo "  1. 测试API: curl http://localhost:8420/health"
echo "  2. 运行测试: python run_system_test.py"
echo "  3. 启动Web界面: python openclaw_plugin/web_interface.py"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""
echo "=========================================="
echo ""

# 启动Bridge Server
python -m bridge.server --config config/baxter.yaml

# 如果服务器退出
echo ""
echo "=========================================="
echo "Bridge Server 已停止"
echo "=========================================="
