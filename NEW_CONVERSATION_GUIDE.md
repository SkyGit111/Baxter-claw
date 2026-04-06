# 新对话快速启动指南

## 🚀 如何在新对话中继续这个项目

### 方法 1：使用项目上下文文件（最简单）

直接告诉 Claude：

```
我有一个 Baxter 机器人控制项目，请先阅读以下文件了解项目：
- d:\Users\Sky\Desktop\baxter-claw\PROJECT_CONTEXT.md

然后帮我 [你的具体需求]
```

### 方法 2：简短描述 + 指向文档

```
我在开发 baxter-claw 项目（位置：d:\Users\Sky\Desktop\baxter-claw），
这是一个基于 OpenClaw 的 Baxter 机器人自然语言控制系统。

项目已实现：
- 基础运动控制（pick/place/move_to/home）
- 视觉功能（VLM 集成，物体识别和定位）
- 双臂协调（bimanual_pick/handover/synchronized_move）
- 增强 IK 求解器
- 完整的安全系统

请查看 README.md 和 FEATURES.md 了解详情，然后帮我 [具体任务]
```

### 方法 3：针对特定任务

**如果要继续开发新功能：**
```
我的 baxter-claw 项目（d:\Users\Sky\Desktop\baxter-claw）需要添加 [新功能]。

项目架构：
- bridge/ - Python 后端（FastAPI）
- plugin/ - OpenClaw TypeScript 插件
- 已有 15 个高层原语和 20+ API 端点

请先阅读 docs/architecture.md 和 bridge/primitives.py，
然后帮我实现 [具体功能]
```

**如果要调试问题：**
```
我的 baxter-claw 项目遇到问题：[描述问题]

项目位置：d:\Users\Sky\Desktop\baxter-claw
相关文件：[列出相关文件]

请帮我诊断和修复。
```

**如果要部署：**
```
我要将 baxter-claw 项目部署到 Baxter 控制主机。

请阅读 DEPLOYMENT_CHECKLIST.md，然后指导我完成部署。
```

## 📋 关键文件清单

新对话时，根据任务让 Claude 阅读相应文件：

### 了解项目整体
- `PROJECT_CONTEXT.md` - **最重要**，包含完整上下文
- `README.md` - 项目概览
- `FEATURES.md` - 功能列表

### 开发相关
- `docs/architecture.md` - 架构设计
- `bridge/primitives.py` - 核心原语实现
- `bridge/server.py` - API 端点
- `plugin/index.ts` - OpenClaw 工具

### 部署相关
- `DEPLOYMENT_CHECKLIST.md` - 部署步骤
- `INSTALL.md` - 安装指南
- `config/baxter.example.yaml` - 配置模板

### 特定功能
- `docs/vision.md` - 视觉功能文档
- `bridge/vlm_client.py` - VLM 客户端
- `bridge/ik_solver.py` - IK 求解器
- `tests/test_dualarm.py` - 双臂测试

## 💡 提示词模板

### 模板 1：继续开发
```
我在开发 baxter-claw 项目（d:\Users\Sky\Desktop\baxter-claw），
这是一个 Baxter 机器人的自然语言控制系统。

请阅读：
1. PROJECT_CONTEXT.md - 了解项目背景
2. [相关文件] - 了解具体实现

然后帮我实现：[具体需求]

要求：
- 保持代码风格一致
- 不影响现有功能
- 添加相应的测试
- 更新文档
```

### 模板 2：问题诊断
```
baxter-claw 项目（d:\Users\Sky\Desktop\baxter-claw）遇到问题：

问题描述：[详细描述]
相关文件：[列出文件]
错误信息：[如果有]

请先阅读 PROJECT_CONTEXT.md 了解项目，然后帮我诊断。
```

### 模板 3：代码审查
```
请审查 baxter-claw 项目的 [具体模块]：

项目位置：d:\Users\Sky\Desktop\baxter-claw
审查重点：[性能/安全/代码质量/等]

先阅读 PROJECT_CONTEXT.md 了解背景，然后给出改进建议。
```

### 模板 4：添加测试
```
为 baxter-claw 项目的 [功能] 添加测试。

项目位置：d:\Users\Sky\Desktop\baxter-claw
现有测试：tests/ 目录
测试框架：pytest

请先查看现有测试风格，然后编写新测试。
```

## 🎯 常见任务的快速启动

### 任务：添加新的原语
```
baxter-claw 项目需要添加新原语：[原语名称]

功能描述：[详细描述]

请：
1. 阅读 bridge/primitives.py 了解现有原语
2. 在 BaxterPrimitives 类中添加新方法
3. 在 bridge/server.py 添加 API 端点
4. 在 plugin/index.ts 添加工具
5. 添加测试
6. 更新文档
```

### 任务：优化性能
```
优化 baxter-claw 项目的性能。

项目位置：d:\Users\Sky\Desktop\baxter-claw

请：
1. 阅读 PROJECT_CONTEXT.md
2. 分析性能瓶颈
3. 提出优化方案
4. 实现优化（如果可行）
```

### 任务：集成新功能
```
为 baxter-claw 集成 [新功能]。

项目架构：
- Python 后端（FastAPI）
- TypeScript 插件（OpenClaw）
- 模块化设计

请：
1. 阅读 docs/architecture.md
2. 设计集成方案
3. 实现功能
4. 添加测试和文档
```

## 📝 注意事项

1. **始终先让 Claude 阅读 PROJECT_CONTEXT.md**
   - 这是最重要的文件，包含完整背景

2. **明确指出项目位置**
   - `d:\Users\Sky\Desktop\baxter-claw`

3. **说明具体需求**
   - 越具体越好，包括期望的行为和约束

4. **提及相关文件**
   - 帮助 Claude 快速定位

5. **说明是否需要保持兼容性**
   - 如果不能破坏现有功能，要明确说明

## 🔄 项目状态快照（2026-04-06）

**版本**: v0.3.0  
**状态**: MVP 完成，可部署  
**代码行数**: ~4,000 行  
**功能**: 15 个原语，20+ API 端点，12 个 OpenClaw 工具  
**测试**: 50+ 测试用例  
**文档**: 13 份完整文档  

**最近完成**:
- ✅ 视觉功能（VLM 集成）
- ✅ 双臂协调
- ✅ 增强 IK 求解器
- ✅ 碰撞检测

**待部署**:
- 需要在 Baxter 控制主机上安装 OpenClaw
- 需要配置 VLM API 密钥
- 需要在真实硬件上测试

## 🆘 如果遇到问题

如果新对话中 Claude 不理解项目背景：

1. 让它先阅读 `PROJECT_CONTEXT.md`
2. 指向具体的文档文件
3. 提供相关代码片段
4. 说明你想要什么结果

示例：
```
你似乎不了解这个项目。请先仔细阅读：
d:\Users\Sky\Desktop\baxter-claw\PROJECT_CONTEXT.md

这个文件包含了项目的完整背景、架构、已实现功能等信息。

读完后，再帮我 [具体任务]
```

## ✅ 检查清单

在新对话开始前，确保：
- [ ] 项目文件都在 `d:\Users\Sky\Desktop\baxter-claw`
- [ ] `PROJECT_CONTEXT.md` 存在且最新
- [ ] 明确你要做什么
- [ ] 准备好相关文件路径
- [ ] 知道哪些功能不能破坏

---

**祝你在新对话中顺利继续项目！** 🚀
