# Baxter-Claw 完整架构文档

## 文档导航

本文档是 Baxter-Claw 项目的完整架构和技术文档，分为 6 个部分，涵盖了从项目概述到部署测试的所有内容。

---

## 📚 文档目录

### [第1节：项目概述](ARCHITECTURE_COMPLETE_01_OVERVIEW.md)
- 项目简介和核心特性
- 技术栈
- 系统架构层次
- 项目目录结构
- 版本历史
- 设计理念

**适合读者**：所有人，快速了解项目

---

### [第2节：核心架构详解](ARCHITECTURE_COMPLETE_02_CORE.md)
- Bridge Server (FastAPI 服务器)
- ArmManager (生命周期管理)
- Primitives (动作原语)
- Driver 层 (硬件抽象)
- RealSense 深度相机驱动

**适合读者**：开发者，理解核心组件

---

### [第3节：视觉系统](ARCHITECTURE_COMPLETE_03_VISION.md)
- 视觉系统概述
- VLM Client (视觉语言模型)
- Multi-View VLM (多视角定位)
- Camera Transforms (坐标变换)
- Image Processor (图像处理)
- 性能指标

**适合读者**：视觉算法开发者

---

### [第4节：OpenClaw 插件系统](ARCHITECTURE_COMPLETE_04_OPENCLAW.md)
- OpenClaw 架构演进
- Skills.md 技能系统
- BaxterClawPlugin 实现
- Web 界面
- 使用示例
- 多语言支持

**适合读者**：用户、插件开发者

---

### [第5节：安全系统](ARCHITECTURE_COMPLETE_05_SAFETY.md)
- 安全架构概述
- SafetyValidator (工作空间限制)
- CollisionDetector (碰撞检测)
- GraspVerifier (抓取验证)
- IK Solver 增强
- 安全配置

**适合读者**：安全工程师、系统集成者

---

### [第6节：部署和测试](ARCHITECTURE_COMPLETE_06_DEPLOYMENT.md)
- 系统部署
- 测试框架
- 性能指标
- 故障排查
- 最佳实践
- 扩展开发

**适合读者**：运维人员、测试工程师

---

## 🚀 快速开始

如果你是第一次接触本项目，建议按以下顺序阅读：

1. **了解项目** → [第1节：项目概述](ARCHITECTURE_COMPLETE_01_OVERVIEW.md)
2. **快速上手** → [QUICKSTART.md](../QUICKSTART.md)
3. **理解架构** → [第2节：核心架构](ARCHITECTURE_COMPLETE_02_CORE.md)
4. **使用系统** → [第4节：OpenClaw 插件](ARCHITECTURE_COMPLETE_04_OPENCLAW.md)
5. **深入开发** → 其他章节

---

## 📖 其他文档

### 用户文档
- [README.md](../README.md) - 项目主文档
- [QUICKSTART.md](../QUICKSTART.md) - 快速开始指南
- [WEB_INTERFACE_GUIDE.md](../WEB_INTERFACE_GUIDE.md) - Web 界面使用
- [SKILLS.md](../SKILLS.md) - 技能系统说明

### 开发文档
- [ARCHITECTURE_SWITCH.md](../ARCHITECTURE_SWITCH.md) - 架构切换指南
- [GRASP_VERIFICATION.md](../GRASP_VERIFICATION.md) - 抓取验证功能
- [CONTRIBUTING.md](../CONTRIBUTING.md) - 贡献指南

### API 文档
- [docs/api.md](api.md) - REST API 参考
- [docs/vision.md](vision.md) - 视觉系统 API
- [docs/safety.md](safety.md) - 安全系统 API

### 部署文档
- [INSTALL.md](../INSTALL.md) - 安装指南
- [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) - 部署指南
- [DEPLOYMENT_CHECKLIST.md](../DEPLOYMENT_CHECKLIST.md) - 部署检查清单

---

## 🎯 按角色阅读

### 我是用户
1. [第1节：项目概述](ARCHITECTURE_COMPLETE_01_OVERVIEW.md)
2. [QUICKSTART.md](../QUICKSTART.md)
3. [第4节：OpenClaw 插件](ARCHITECTURE_COMPLETE_04_OPENCLAW.md)
4. [WEB_INTERFACE_GUIDE.md](../WEB_INTERFACE_GUIDE.md)

### 我是开发者
1. [第1节：项目概述](ARCHITECTURE_COMPLETE_01_OVERVIEW.md)
2. [第2节：核心架构](ARCHITECTURE_COMPLETE_02_CORE.md)
3. [第3节：视觉系统](ARCHITECTURE_COMPLETE_03_VISION.md)
4. [第4节：OpenClaw 插件](ARCHITECTURE_COMPLETE_04_OPENCLAW.md)
5. [docs/api.md](api.md)

### 我是运维人员
1. [第1节：项目概述](ARCHITECTURE_COMPLETE_01_OVERVIEW.md)
2. [INSTALL.md](../INSTALL.md)
3. [第6节：部署和测试](ARCHITECTURE_COMPLETE_06_DEPLOYMENT.md)
4. [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)

### 我是安全工程师
1. [第1节：项目概述](ARCHITECTURE_COMPLETE_01_OVERVIEW.md)
2. [第5节：安全系统](ARCHITECTURE_COMPLETE_05_SAFETY.md)
3. [docs/safety.md](safety.md)

---

## 🔍 按主题查找

### 架构设计
- [第1节：系统架构层次](ARCHITECTURE_COMPLETE_01_OVERVIEW.md#13-系统架构层次)
- [第2节：核心架构组件](ARCHITECTURE_COMPLETE_02_CORE.md#2-核心架构组件)
- [第4节：OpenClaw 架构演进](ARCHITECTURE_COMPLETE_04_OPENCLAW.md#41-openclaw-架构概述)

### 视觉系统
- [第3节：视觉系统架构](ARCHITECTURE_COMPLETE_03_VISION.md#3-视觉系统架构)
- [第3节：VLM Client](ARCHITECTURE_COMPLETE_03_VISION.md#32-vlm-client)
- [第3节：坐标变换](ARCHITECTURE_COMPLETE_03_VISION.md#34-camera-transforms)

### 安全机制
- [第5节：安全架构](ARCHITECTURE_COMPLETE_05_SAFETY.md#51-安全架构概述)
- [第5节：工作空间限制](ARCHITECTURE_COMPLETE_05_SAFETY.md#52-safetyvalidator)
- [第5节：碰撞检测](ARCHITECTURE_COMPLETE_05_SAFETY.md#53-collisiondetector)
- [第5节：抓取验证](ARCHITECTURE_COMPLETE_05_SAFETY.md#54-graspverifier)

### 技能系统
- [第4节：Skills.md 技能系统](ARCHITECTURE_COMPLETE_04_OPENCLAW.md#42-skillsmd-技能系统)
- [第4节：技能选择](ARCHITECTURE_COMPLETE_04_OPENCLAW.md#432-技能选择-select_skill)
- [第4节：技能执行](ARCHITECTURE_COMPLETE_04_OPENCLAW.md#433-技能执行-execute_skill)

### 部署运维
- [第6节：系统部署](ARCHITECTURE_COMPLETE_06_DEPLOYMENT.md#61-系统部署)
- [第6节：测试框架](ARCHITECTURE_COMPLETE_06_DEPLOYMENT.md#62-测试框架)
- [第6节：故障排查](ARCHITECTURE_COMPLETE_06_DEPLOYMENT.md#64-故障排查)

---

## 📊 文档统计

- **总页数**：约 150 页
- **代码示例**：100+ 个
- **架构图**：10+ 个
- **配置示例**：20+ 个

---

## 🤝 贡献

发现文档问题或有改进建议？

1. 提交 Issue: https://github.com/SkyGit111/Baxter-claw/issues
2. 提交 PR: https://github.com/SkyGit111/Baxter-claw/pulls
3. 参考 [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## 📝 版本信息

- **文档版本**：v1.0
- **对应代码版本**：v0.4.1
- **最后更新**：2026-04-28
- **维护者**：Baxter-Claw Team

---

## 📧 联系方式

- **GitHub**: https://github.com/SkyGit111/Baxter-claw
- **Issues**: https://github.com/SkyGit111/Baxter-claw/issues

---

**开始阅读** → [第1节：项目概述](ARCHITECTURE_COMPLETE_01_OVERVIEW.md)
