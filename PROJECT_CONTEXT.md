# Baxter-Claw 项目上下文摘要

## 项目概述

**项目名称**: Baxter-Claw  
**位置**: `d:\Users\Sky\Desktop\baxter-claw`  
**目标**: 为 Baxter 双臂机器人实现基于自然语言的控制系统

## 核心架构

```
用户（自然语言）
    ↓
OpenClaw (LLM Agent Platform)
    ↓ HTTP 工具调用
Bridge Server (FastAPI, Python)
    ↓ baxter_interface SDK
Baxter 机器人（ROS）
```

## 已实现功能（v0.3.0）

### 1. 基础运动控制
- `pick(arm, position)` - 抓取
- `place(arm, position)` - 放置
- `move_to(arm, position, orientation)` - 移动到指定位姿
- `home(arm)` - 返回初始位置

### 2. 视觉功能（VLM 集成）
- `pick_by_name(arm, object_name)` - 通过名称抓取物体
- `locate_object(object_name)` - 定位物体
- `describe_scene()` - 场景描述
- `identify_objects()` - 识别所有物体
- 支持 Claude 和 GPT-4V

### 3. 双臂协调
- `bimanual_pick(object_position)` - 双手抓取大物体
- `handover(from_arm, to_arm)` - 手臂间传递物体
- `synchronized_move(left_pos, right_pos)` - 同步移动双臂
- 碰撞检测（最小距离 15cm）

### 4. 增强 IK 求解器
- 5 种回退策略
- 多种种子位置
- 轨迹平滑
- 速度限制验证

### 5. 安全系统
- 工作空间边界验证
- 关节限制检查
- 速度约束
- 双臂碰撞检测

## 项目结构

```
baxter-claw/
├── bridge/                    # Python 后端
│   ├── drivers/
│   │   ├── base.py           # 驱动抽象接口
│   │   ├── baxter_driver.py  # 真实硬件驱动
│   │   └── mock_driver.py    # 模拟驱动
│   ├── primitives.py         # 15 个高层原语
│   ├── safety.py             # 安全验证
│   ├── vlm_client.py         # VLM 客户端
│   ├── ik_solver.py          # 增强 IK 求解器
│   ├── models.py             # Pydantic 模型
│   ├── arm_manager.py        # 机器人生命周期管理
│   └── server.py             # FastAPI 服务器（20+ 端点）
├── plugin/                    # OpenClaw TypeScript 插件
│   ├── openclaw.plugin.json  # 插件配置（12 个工具）
│   ├── index.ts              # 插件入口
│   └── src/
│       └── bridge-client.ts  # HTTP 客户端
├── config/
│   └── baxter.example.yaml   # 配置模板
├── docs/                      # 13 份文档
│   ├── architecture.md
│   ├── api.md
│   ├── vision.md
│   └── ...
├── examples/                  # 示例脚本
│   ├── test_primitives.py
│   ├── vision_demo.py
│   └── dualarm_demo.py
├── tests/                     # 测试（50+ 测试用例）
│   ├── test_primitives.py
│   ├── test_safety.py
│   ├── test_mock_driver.py
│   └── test_dualarm.py
├── README.md                  # 项目概览
├── FEATURES.md                # 完整功能列表
├── DEPLOYMENT_CHECKLIST.md    # 部署指南
└── pyproject.toml             # Python 包配置
```

## 技术栈

**后端:**
- Python 3.8+
- FastAPI (REST API)
- Pydantic (数据验证)
- baxter_interface (ROS SDK)
- httpx (异步 HTTP)

**前端插件:**
- TypeScript
- Node.js 18+
- Axios (HTTP 客户端)

**视觉:**
- OpenCV (图像处理)
- cv_bridge (ROS-OpenCV 桥接)
- Claude API / OpenAI API (VLM)

**测试:**
- pytest
- pytest-asyncio

## 关键设计决策

1. **模块化架构**: Driver → Primitives → API → Plugin
2. **安全优先**: 多层验证，保守的默认参数
3. **Mock 驱动**: 无需硬件即可开发测试
4. **增强 IK**: 5 种回退策略提高成功率
5. **VLM 集成**: 支持多个提供商（Claude/OpenAI）
6. **碰撞检测**: 双臂操作时自动检查

## 当前状态

**完成度**: 100% (MVP 完成)  
**代码行数**: ~4,000 行  
**测试覆盖**: 50+ 测试用例  
**文档**: 13 份完整文档  

**已知限制:**
1. 左臂接口已实现但未充分测试（重点在右臂）
2. IK 求解器虽已增强但不如 MoveIt 强大
3. VLM 的 3D 位置估计有固有限制
4. 轨迹规划使用线性插值（可用样条增强）

## 部署状态

**开发环境**: Windows (d:\Users\Sky\Desktop\baxter-claw)  
**目标环境**: Baxter 控制主机 (Linux + ROS)  

**部署步骤**:
1. 传输项目到 Baxter 主机
2. 安装依赖 (`pip install -e .`)
3. 安装 OpenClaw
4. 配置 VLM API 密钥
5. 启动 Bridge Server
6. 启动 OpenClaw
7. 通过自然语言控制

详见 `DEPLOYMENT_CHECKLIST.md`

## 下一步可能的工作

**优先级高:**
- [ ] 在真实 Baxter 上测试所有功能
- [ ] 左臂功能完整测试
- [ ] 性能优化和延迟降低
- [ ] 更多示例和教程

**优先级中:**
- [ ] MoveIt 集成（更好的路径规划）
- [ ] 深度估计（立体相机）
- [ ] 物体跟踪
- [ ] 抓取姿态估计

**优先级低:**
- [ ] 力控制原语
- [ ] 柔顺运动
- [ ] 学习型抓取
- [ ] 任务规划

## 重要文件速查

**理解项目:**
- `README.md` - 快速了解
- `FEATURES.md` - 完整功能列表
- `docs/architecture.md` - 架构设计

**开发:**
- `bridge/primitives.py` - 核心原语实现
- `bridge/server.py` - API 端点
- `plugin/index.ts` - OpenClaw 工具

**部署:**
- `DEPLOYMENT_CHECKLIST.md` - 部署步骤
- `config/baxter.example.yaml` - 配置模板
- `INSTALL.md` - 安装指南

**测试:**
- `tests/` - 所有测试
- `examples/` - 示例脚本

## 配置要点

**VLM 配置** (`config/baxter.yaml`):
```yaml
vlm:
  enabled: true
  provider: "claude"  # 或 "openai"
  api_key: "${ANTHROPIC_API_KEY}"
```

**驱动配置**:
```yaml
driver:
  type: "baxter"  # 真实硬件
  # type: "mock"  # 模拟测试
```

**安全参数**:
```yaml
safety:
  workspace:
    x: [0.3, 0.9]
    y: [-0.7, 0.7]
    z: [-0.2, 0.5]
  max_speed: 0.5
```

## API 端点速查

**基础控制:**
- `POST /enable` - 启用机器人
- `POST /disable` - 禁用机器人
- `GET /status?arm=right` - 查询状态
- `POST /stop` - 紧急停止

**原语:**
- `POST /primitives/pick` - 抓取
- `POST /primitives/place` - 放置
- `POST /primitives/move_to` - 移动
- `POST /primitives/home` - 回家

**视觉:**
- `POST /vision/pick_by_name` - 视觉抓取
- `POST /vision/locate_object` - 定位物体
- `POST /vision/describe_scene` - 场景描述
- `POST /vision/identify_objects` - 识别物体

**双臂:**
- `POST /dualarm/bimanual_pick` - 双手抓取
- `POST /dualarm/handover` - 传递物体
- `POST /dualarm/synchronized_move` - 同步移动

## 常见问题

**Q: 如何测试而不需要真实机器人？**  
A: 使用 Mock 驱动，设置 `driver.type: "mock"`

**Q: 如何启用视觉功能？**  
A: 配置 VLM，设置 `vlm.enabled: true` 和 API 密钥

**Q: 双臂功能是否完全可用？**  
A: 接口已实现，但主要测试在右臂，左臂需要更多测试

**Q: IK 求解失败怎么办？**  
A: 增强 IK 有 5 种回退策略，如仍失败可调整目标位姿或考虑 MoveIt

**Q: 如何添加新的原语？**  
A: 在 `primitives.py` 添加方法 → 在 `server.py` 添加端点 → 在 `plugin/` 添加工具

## 联系信息

**项目位置**: `d:\Users\Sky\Desktop\baxter-claw`  
**参考项目**: ClawArm (d:\Users\Sky\Desktop\Clawarm-main)  
**用户**: Sky  
**机器人**: Baxter 双臂机器人（使用 Python SDK 控制）

---

**在新对话中使用此文件:**

```
"我有一个 Baxter 机器人项目，请阅读 d:\Users\Sky\Desktop\baxter-claw\PROJECT_CONTEXT.md 
了解项目背景，然后帮我 [具体任务]"
```
