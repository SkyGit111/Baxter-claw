#!/bin/bash
# Baxter-Claw 快速启动脚本
# 用于真机测试的一键启动

# 不使用 set -e，手动处理错误

echo "=========================================="
echo "Baxter-Claw 快速启动"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否在项目根目录
if [ ! -f "bridge/server.py" ]; then
    echo -e "${RED}✗ 错误: 请在 Baxter-claw 项目根目录运行此脚本${NC}"
    exit 1
fi

# 步骤1: 配置ROS环境
echo "步骤 1/5: 配置ROS环境..."

# 检查ROS环境是否已配置
if [ -z "$ROS_MASTER_URI" ]; then
    echo -e "${YELLOW}⚠ ROS环境未配置，尝试自动配置...${NC}"
    if [ -f ~/catkin_ws/baxter.sh ]; then
        cd ~/catkin_ws
        source ./baxter.sh
        cd - > /dev/null
    else
        echo -e "${RED}✗ 错误: ~/catkin_ws/baxter.sh 不存在${NC}"
        echo "  请手动运行: source ~/catkin_ws/baxter.sh"
        exit 1
    fi
fi

echo -e "${GREEN}✓ ROS环境已配置${NC}"
echo "  ROS_MASTER_URI: $ROS_MASTER_URI"
echo "  ROS_IP: $ROS_IP"

# 步骤2: 激活conda环境
echo ""
echo "步骤 2/5: 激活conda环境..."

# 检查conda环境是否已激活
if [ "$CONDA_DEFAULT_ENV" = "baxter-claw" ]; then
    echo -e "${GREEN}✓ Conda环境已激活: $CONDA_DEFAULT_ENV${NC}"
elif [ -d ~/miniconda3/envs/baxter-claw ]; then
    source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null || true
    conda activate baxter-claw 2>/dev/null || true
    if [ "$CONDA_DEFAULT_ENV" = "baxter-claw" ]; then
        echo -e "${GREEN}✓ Conda环境已激活: $CONDA_DEFAULT_ENV${NC}"
    else
        echo -e "${YELLOW}⚠ 警告: 无法激活conda环境${NC}"
        echo "  当前环境: $CONDA_DEFAULT_ENV"
    fi
else
    echo -e "${RED}✗ 错误: baxter-claw conda环境不存在${NC}"
    echo "  创建环境: conda create -n baxter-claw python=3.8"
    exit 1
fi

# 步骤3: 检查Baxter连接
echo ""
echo "步骤 3/5: 检查Baxter连接..."
if timeout 3 rostopic list 2>/dev/null | grep -q "/robot/"; then
    echo -e "${GREEN}✓ Baxter连接正常${NC}"
    TOPIC_COUNT=$(rostopic list 2>/dev/null | grep "/robot/" | wc -l)
    echo "  检测到 $TOPIC_COUNT 个Baxter话题"
else
    echo -e "${YELLOW}⚠ 警告: 未检测到Baxter话题${NC}"
    echo "  请确认:"
    echo "  1. Baxter已开机并完全启动（约5分钟）"
    echo "  2. 网络连接正常"
    echo "  3. ROS_MASTER_URI指向正确的Baxter IP"
    echo ""
    read -p "是否继续? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 步骤4: 检查深度相机
echo ""
echo "步骤 4/5: 检查深度相机..."
if lsusb | grep -q "8086:0b5c"; then
    echo -e "${GREEN}✓ D455深度相机已连接${NC}"
else
    echo -e "${YELLOW}⚠ 警告: 未检测到D455深度相机${NC}"
    echo "  系统将在没有深度相机的情况下运行"
fi

# 步骤5: 检查API密钥
echo ""
echo "步骤 5/5: 检查配置..."
if [ -z "$QWEN_API_KEY" ]; then
    echo -e "${YELLOW}⚠ 警告: QWEN_API_KEY未设置${NC}"
    echo "  VLM功能将不可用"
    echo "  设置方法: export QWEN_API_KEY='your-key'"
else
    echo -e "${GREEN}✓ QWEN_API_KEY已设置${NC}"
fi

# 检查配置文件
if [ -f "config/baxter.yaml" ]; then
    echo -e "${GREEN}✓ 配置文件存在${NC}"
else
    echo -e "${RED}✗ 错误: config/baxter.yaml 不存在${NC}"
    exit 1
fi

echo ""
echo "=========================================="
echo "准备启动Bridge Server"
echo "=========================================="
echo ""
echo "配置信息:"
echo "  - 驱动类型: baxter (真机)"
echo "  - 深度相机: 已启用"
echo "  - VLM提供商: qwen"
echo "  - 服务器端口: 8420"
echo ""
echo "启动后可以:"
echo "  1. 运行测试: python run_system_test.py"
echo "  2. 启动Web界面: python openclaw_plugin/web_interface.py"
echo "  3. 查看API文档: http://localhost:8420/docs"
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
