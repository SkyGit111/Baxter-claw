# Baxter-Claw

通过 OpenClaw LLM 智能体平台实现 Baxter 双臂机器人的自然语言控制。

[English](README.md) | 简体中文

## 概述

Baxter-Claw 让你能够通过自然语言与 Baxter 研究型机器人进行直观交互。基于 [OpenClaw](https://openclaw.ai/) 构建，提供了高层动作原语（pick、place、move_to、home），实现语义化的机器人操作。

**核心特性**：
- 🤖 高层动作原语：`pick`（抓取）、`place`（放置）、`move_to`（移动）、`home`（归位）
- 🔌 基于插件的 OpenClaw 集成
- 🛡️ 内置安全验证
- 🎯 单臂控制（右臂），双臂接口已预留
- 📷 相机接口（预留用于未来视觉集成）
- 🧪 Mock 驱动，无需硬件即可测试

## 快速开始

### 前置要求

**在 Baxter 控制主机上（Linux + ROS）**：
- Ubuntu 18.04/20.04 with ROS Melodic/Noetic
- 已安装 Baxter SDK (`baxter_interface`)
- Python 3.8+
- 已安装并运行 OpenClaw

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/baxter-claw.git
cd baxter-claw

# 安装 Python 依赖
pip install -e .

# 配置 Baxter 环境
cd ~/ros_ws
./baxter.sh

# 启动 Bridge 服务器
baxter-claw-bridge --config config/baxter.yaml
```

### 安装 OpenClaw 插件

```bash
cd plugin
npm install
npm run build

# 复制到 OpenClaw 插件目录
cp -r . ~/.openclaw/plugins/baxter-claw
```

### 使用示例

启动 OpenClaw 后，你可以用自然语言控制机器人：

```
用户: "启用机器人"
助手: [调用 robot_enable 工具] 机器人已成功启用。

用户: "在位置 x=0.6, y=0.2, z=0.1 抓取物体"
助手: [调用 pick 工具] 移动到预抓取位置... 抓取中... 成功抬起物体。

用户: "把它放到 x=0.5, y=-0.3, z=0.15"
助手: [调用 place 工具] 移动到目标位置... 放置中... 已释放物体。

用户: "回到初始位置"
助手: [调用 home 工具] 右臂已返回初始位置。
```

## 架构

```
用户（自然语言）
      ↓
OpenClaw LLM 智能体
      ↓ (HTTP 工具调用)
Bridge 服务器 (FastAPI)
      ↓
BaxterDriver (baxter_interface SDK)
      ↓ (ROS Topics/Services)
Baxter 机器人
```

## 动作原语

### pick(arm, position, approach_height)
在指定位置抓取物体。
- 移动到预抓取姿态（目标上方）
- 打开夹爪
- 下降到目标位置
- 闭合夹爪
- 抬起物体

### place(arm, position, approach_height)
在指定位置放置物体。
- 移动到预放置姿态（目标上方）
- 下降到目标位置
- 打开夹爪
- 向上收回

### move_to(arm, position, orientation)
移动末端执行器到指定位姿。
- 验证工作空间安全性
- 执行笛卡尔运动

### home(arm)
返回到预定义的初始位置。

## 文档

- [快速开始指南](docs/quickstart.md)
- [架构文档](docs/architecture.md)
- [API 参考](docs/api.md)
- [安全指南](docs/safety.md)

## 开发

### 使用 Mock 驱动测试

```bash
# 编辑 config/baxter.yaml: driver.type = "mock"
baxter-claw-bridge --config config/baxter.yaml

# 测试 API
curl http://localhost:8420/health
curl -X POST http://localhost:8420/primitives/pick \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "position": [0.6, 0.2, 0.1]}'
```

### 运行测试

```bash
pytest tests/
```

## 路线图

- [x] 高层原语（pick, place, move_to, home）
- [x] 单臂控制（右臂）
- [x] Mock 驱动用于测试
- [ ] 视觉集成（基于 VLM 的物体定位）
- [ ] 双臂协调原语
- [ ] 中层运动原语
- [ ] Skill 模式（代码生成）
- [ ] 轨迹规划和优化

## 安全

⚠️ **重要安全提示**：
- 始终在 mock 模式下先测试
- 保持急停按钮可触及
- 部署前验证工作空间限制
- 自主操作期间监控机器人
- 详见 [docs/safety.md](docs/safety.md)

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 致谢

- 灵感来自 [ClawArm](https://github.com/agilexrobotics/clawarm)
- 基于 [OpenClaw](https://openclaw.ai/) 智能体平台
- 使用 [Baxter SDK](http://sdk.rethinkrobotics.com/)

## 贡献

欢迎贡献！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 引用

如果你在研究中使用了 Baxter-Claw，请引用：

```bibtex
@software{baxter_claw_2026,
  title = {Baxter-Claw: Natural Language Control for Baxter Robot},
  author = {Your Name},
  year = {2026},
  url = {https://github.com/yourusername/baxter-claw}
}
```
