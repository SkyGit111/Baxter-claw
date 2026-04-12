# Baxter-Claw 快速参考指南

## 🚀 快速启动

### 启动 Bridge Server
```bash
cd /home/cothink/Baxter-claw
./start.sh
```

### 停止 Bridge Server
```bash
cd /home/cothink/Baxter-claw
./stop.sh
```

### 手动启动（如果需要）
```bash
source /home/cothink/miniconda3/etc/profile.d/conda.sh
conda activate baxter-claw
cd /home/cothink/Baxter-claw
python -m bridge.server --config config/baxter.yaml
```

## 📋 系统状态检查

### 检查 Bridge Server
```bash
curl http://localhost:8420/health
curl http://localhost:8420/status
```

### 运行完整测试
```bash
source /home/cothink/miniconda3/etc/profile.d/conda.sh
conda activate baxter-claw
cd /home/cothink/Baxter-claw
python test_deployment.py
```

## 🤖 使用 OpenClaw 控制机器人

### 启动 OpenClaw
```bash
openclaw
```

### 自然语言命令示例

**基础控制：**
- "Enable the robot"
- "Show me the robot status"
- "Disable the robot"

**运动控制：**
- "Move the right arm to position [0.7, -0.2, 0.3]"
- "Return to home position"
- "Move to [0.6, -0.3, 0.2]"

**抓取操作：**
- "Pick up an object at [0.6, -0.3, 0.0]"
- "Place the object at [0.5, -0.4, 0.0]"

**视觉功能：**
- "Describe what you see"
- "Identify all objects in the scene"
- "Locate the red cup"
- "Pick up the blue box"

**夹爪控制：**
- "Open the gripper"
- "Close the gripper with 50% force"

**紧急情况：**
- "Emergency stop!"

## 🔧 配置文件

### Bridge 配置
文件：`/home/cothink/Baxter-claw/config/baxter.yaml`

**切换到真实机器人：**
```yaml
driver:
  type: "baxter"  # 从 "mock" 改为 "baxter"
```

**启用/禁用视觉功能：**
```yaml
vlm:
  enabled: true  # true 启用，false 禁用
  provider: "qwen"  # "claude", "openai", "qwen"
  api_key: "your-api-key"
```

### OpenClaw 配置
文件：`/home/cothink/.openclaw/openclaw.json`

插件已配置在：
```json
"plugins": {
  "entries": {
    "baxter-claw": {
      "enabled": true,
      "path": "/home/cothink/Baxter-claw/plugin"
    }
  }
}
```

## 📊 可用的 API 端点

### 基础控制
- `POST /enable` - 启用机器人
- `POST /disable` - 禁用机器人
- `GET /status?arm=right` - 查询状态
- `POST /stop` - 紧急停止
- `GET /health` - 健康检查

### 运动原语
- `POST /primitives/pick` - 抓取
- `POST /primitives/place` - 放置
- `POST /primitives/move_to` - 移动到位置
- `POST /primitives/home` - 回到初始位置

### 夹爪控制
- `POST /gripper/open` - 打开夹爪
- `POST /gripper/close` - 关闭夹爪
- `POST /gripper/calibrate` - 校准夹爪

### 视觉功能
- `POST /vision/pick_by_name` - 通过名称抓取物体
- `POST /vision/locate_object` - 定位物体
- `POST /vision/describe_scene` - 描述场景
- `POST /vision/identify_objects` - 识别所有物体
- `GET /camera?name=right_hand` - 获取相机图像

### 双臂协调
- `POST /dualarm/bimanual_pick` - 双手抓取
- `POST /dualarm/handover` - 手臂间传递
- `POST /dualarm/synchronized_move` - 同步移动

## 🛠️ 故障排除

### Bridge Server 无法启动
```bash
# 检查端口占用
lsof -i :8420

# 查看进程
ps aux | grep bridge.server

# 强制停止
pkill -9 -f bridge.server
```

### OpenClaw 找不到插件
```bash
# 检查插件编译
cd /home/cothink/Baxter-claw/plugin
npm run build

# 检查配置
cat ~/.openclaw/openclaw.json | grep baxter-claw
```

### 真实机器人连接失败
```bash
# 检查 ROS 环境
echo $ROS_DISTRO
roscore &

# 检查 Baxter 接口
python3 -c "import baxter_interface; print('OK')"

# 检查网络
ping <baxter-ip>
```

## 📁 重要文件位置

### 配置
- Bridge 配置: `config/baxter.yaml`
- OpenClaw 配置: `~/.openclaw/openclaw.json`

### 代码
- Python 后端: `bridge/`
- TypeScript 插件: `plugin/`
- 测试: `tests/`
- 示例: `examples/`

### 脚本
- 启动脚本: `start.sh`
- 停止脚本: `stop.sh`
- 测试脚本: `test_deployment.py`

### 文档
- 项目概览: `README.md`
- 功能列表: `FEATURES.md`
- 部署指南: `DEPLOYMENT_CHECKLIST.md`
- 部署报告: `DEPLOYMENT_SUCCESS.md`
- 本指南: `QUICKSTART.md`

## 🔐 安全注意事项

### 使用 Mock 驱动时
- 完全安全，可以随意测试
- 不会影响真实硬件

### 使用真实机器人时
- ⚠️ 确保工作空间内无人
- ⚠️ 保持紧急停止按钮可用
- ⚠️ 从简单动作开始测试
- ⚠️ 注意工作空间边界
- ⚠️ 监控机器人运动

### 工作空间限制（默认）
```yaml
workspace:
  x: [0.3, 0.9]    # 前后 30-90cm
  y: [-0.7, 0.7]   # 左右 ±70cm
  z: [-0.2, 0.5]   # 高度 -20 到 50cm
```

## 📞 获取帮助

### 查看日志
```bash
# Bridge Server 日志
tail -f /tmp/claude-1000/.../tasks/*.output

# OpenClaw 日志
tail -f ~/.openclaw/logs/*.log
```

### API 文档
浏览器访问: http://localhost:8420/docs

### 运行示例
```bash
source /home/cothink/miniconda3/etc/profile.d/conda.sh
conda activate baxter-claw
cd /home/cothink/Baxter-claw

# 基础原语测试
python examples/test_primitives.py

# 视觉功能演示
python examples/vision_demo.py

# 双臂协调演示
python examples/dualarm_demo.py
```

## ✅ 部署检查清单

- [x] Python 环境配置完成
- [x] 所有依赖已安装
- [x] 配置文件已创建
- [x] Qwen VLM 支持已添加
- [x] Bridge Server 测试通过
- [x] OpenClaw 插件已配置
- [x] 启动脚本已创建
- [ ] 真实机器人连接（待测试）

## 🎯 下一步

### 选项 1: 继续使用 Mock 驱动
1. 启动 OpenClaw
2. 测试所有自然语言命令
3. 验证视觉功能

### 选项 2: 连接真实 Baxter
1. 修改 `config/baxter.yaml` 中的驱动类型
2. 确认 Baxter 已开机
3. 重启 Bridge Server
4. 小心测试基础动作

---
**版本**: v0.3.0  
**最后更新**: 2026-04-06