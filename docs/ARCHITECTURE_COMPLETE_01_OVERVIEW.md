# Baxter-Claw 完整架构文档 - 第1节：项目概述

## 1. 项目简介

Baxter-Claw 是一个基于 Baxter 双臂机器人的智能操作系统，通过自然语言实现机器人控制。项目整合了视觉感知、运动规划、安全验证和 LLM 决策，提供了从底层驱动到高层语义控制的完整解决方案。

### 1.1 核心特性

- **自然语言控制**：通过 LLM 理解用户意图，自动选择和执行技能
- **视觉引导操作**：集成 D455 深度相机和手腕相机，实现精确的物体定位
- **双臂协同**：支持左右臂独立或协同操作
- **技能化架构**：基于 skills.md 的可扩展技能系统
- **安全保障**：多层安全验证，包括工作空间限制、碰撞检测、可达性检查
- **实验性功能**：抓取验证、碰撞检测等可选功能

### 1.2 技术栈

**机器人平台**：
- Baxter Research Robot (双臂协作机器人)
- ROS Noetic (机器人操作系统)
- Baxter SDK (Python API)

**视觉系统**：
- Intel RealSense D455 深度相机 (主视觉)
- Baxter 手腕相机 (辅助视觉)
- OpenCV (图像处理)

**AI/LLM**：
- 通义千问 (Qwen) - 主要 LLM 提供商
- 支持 OpenAI GPT-4、Claude (可选)
- VLM (Vision-Language Model) 用于物体识别和定位

**后端框架**：
- FastAPI (REST API 服务器)
- asyncio (异步处理)
- httpx (HTTP 客户端)

**前端**：
- Flask (Web 界面)
- HTML/CSS/JavaScript (实时控制面板)

### 1.3 系统架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                    用户交互层 (User Layer)                    │
│  - Web 界面 (Flask)                                          │
│  - 自然语言输入                                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  OpenClaw 插件层 (Plugin Layer)              │
│  - LLM 意图识别                                              │
│  - Skills.md 技能选择                                        │
│  - 参数提取和验证                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                Bridge Server (API Layer)                     │
│  - FastAPI REST API                                          │
│  - 请求路由和验证                                            │
│  - 状态管理                                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Primitives 层 (Primitive Actions)               │
│  - pick / place / move_to / home                            │
│  - pick_by_name / place_by_name (视觉引导)                  │
│  - 双臂协同动作                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Driver 层 (Hardware Layer)                  │
│  - BaxterDriver (真机驱动)                                   │
│  - MockDriver (仿真驱动)                                     │
│  - 运动控制、夹爪控制、相机控制                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    硬件层 (Hardware)                         │
│  - Baxter Robot                                              │
│  - RealSense D455                                            │
│  - Wrist Cameras                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 项目目录结构

```
Baxter-claw/
├── bridge/                      # 核心 Bridge Server
│   ├── server.py               # FastAPI 服务器入口
│   ├── arm_manager.py          # 机器人生命周期管理
│   ├── primitives.py           # 动作原语实现
│   ├── safety.py               # 安全验证器
│   ├── vlm_client.py           # VLM 客户端
│   ├── multi_view_vlm.py       # 多视角视觉定位
│   ├── grasp_verifier.py       # 抓取验证 (实验性)
│   ├── collision_detector.py   # 碰撞检测 (实验性)
│   ├── models.py               # API 数据模型
│   ├── ik_solver.py            # 增强 IK 求解器
│   ├── camera_transforms.py    # 相机坐标变换
│   ├── image_processor.py      # 图像处理
│   └── drivers/                # 硬件驱动
│       ├── base.py             # 驱动基类
│       ├── baxter_driver.py    # Baxter 真机驱动
│       ├── mock_driver.py      # 仿真驱动
│       └── realsense_driver.py # RealSense 相机驱动
│
├── openclaw_plugin/             # OpenClaw 自然语言控制插件
│   ├── baxter_claw_plugin.py   # 主插件实现
│   ├── skills.md               # 技能定义文档
│   ├── web_interface.py        # Web 控制界面
│   ├── LANGUAGE_SUPPORT.md     # 多语言支持文档
│   └── README.md               # 插件使用说明
│
├── tests/                       # 单元测试
│   ├── test_primitives.py
│   ├── test_safety.py
│   ├── test_bridge_api.py
│   └── test_dualarm.py
│
├── examples/                    # 示例代码
│   ├── test_primitives.py      # 动作原语测试
│   ├── vision_demo.py          # 视觉功能演示
│   └── dualarm_demo.py         # 双臂协同演示
│
├── docs/                        # 文档
│   ├── api.md                  # API 文档
│   ├── architecture.md         # 架构文档
│   ├── quickstart.md           # 快速开始
│   ├── safety.md               # 安全指南
│   └── vision.md               # 视觉系统文档
│
├── config/                      # 配置文件
│   └── baxter.yaml             # Baxter 配置
│
├── archived/                    # 归档文件
│   ├── docs/                   # 历史文档
│   ├── scripts/                # 调试脚本
│   └── test_reports/           # 测试报告
│
├── start_server.py             # 启动脚本
├── run_system_test.py          # 系统测试
├── README.md                   # 项目主文档
├── QUICKSTART.md               # 快速开始指南
├── ARCHITECTURE_SWITCH.md      # 架构切换指南
├── GRASP_VERIFICATION.md       # 抓取验证文档
└── SKILLS.md                   # 技能系统文档
```

### 1.5 版本历史

- **v0.1.0** (2026-04-07): 初始版本，基础动作原语
- **v0.2.0** (2026-04-14): 添加 D455 深度相机支持
- **v0.3.0** (2026-04-20): LLM 意图识别，动态工作流
- **v0.4.0** (2026-04-22): Skills.md 架构，提升可控性
- **v0.4.1** (2026-04-28): 抓取验证、碰撞检测 (实验性)

### 1.6 设计理念

**1. 分层解耦**
- 每层职责明确，接口清晰
- 上层不直接访问硬件，通过 Driver 抽象
- 便于测试、维护和扩展

**2. 安全第一**
- 多层安全验证（工作空间、碰撞、可达性）
- 失败安全设计（Fail-safe）
- 实验性功能隔离，不影响核心功能

**3. 可扩展性**
- 技能化架构，易于添加新技能
- 插件式设计，支持多种 LLM 和相机
- 配置驱动，无需修改代码

**4. 用户友好**
- 自然语言控制，降低使用门槛
- Web 界面实时反馈
- 详细的日志和错误提示

---

**下一节**：[第2节：核心架构详解](ARCHITECTURE_COMPLETE_02_CORE.md)
