# Baxter-Claw 使用手册

## 系统概述

Baxter-Claw 是基于 OpenClaw 平台的 Baxter 机器人自然语言控制系统，通过高级动作原语实现直观的机器人操作。

**核心架构**：用户自然语言 → OpenClaw LLM → Bridge Server (FastAPI) → Baxter 机器人

## 快速开始

### 1. 安装配置

```bash
# 克隆仓库
git clone https://github.com/yourusername/baxter-claw.git
cd baxter-claw

# 安装依赖
pip install -e .

# 配置文件
cp config/baxter.example.yaml config/baxter.yaml
# 编辑 config/baxter.yaml 设置驱动类型和参数
```

### 2. 启动系统

```bash
# 基础启动
baxter-claw-bridge --config config/baxter.yaml

# 启用抓取验证（实验性）
baxter-claw-bridge --config config/baxter.yaml --enable-grasp-verification

# 自定义端口
baxter-claw-bridge --config config/baxter.yaml --port 8421
```

### 3. 安装 OpenClaw 插件

```bash
cd plugin
npm install && npm run build
cp -r . ~/.openclaw/plugins/baxter-claw
```

## 配置说明

编辑 `config/baxter.yaml`：

```yaml
# 驱动配置
driver:
  type: "mock"  # "baxter" (真实硬件) 或 "mock" (模拟测试)

# 机器人配置
robot:
  arms: ["right"]  # 当前支持右臂

# 视觉功能（可选）
vlm:
  enabled: false  # 启用视觉定位功能
  provider: "claude"  # "claude" 或 "openai"
  api_key: null  # API 密钥

# 安全限制
safety:
  workspace:
    x: [0.3, 0.9]    # 前后范围（米）
    y: [-0.7, 0.7]   # 左右范围（米）
    z: [-0.2, 0.5]   # 高度范围（米）
  max_speed: 0.5     # 最大速度比例

# 动作参数
primitives:
  approach_height: 0.1  # 预抓取高度（米）
  grasp_force: 30.0     # 抓取力度
  default_speed: 0.3    # 默认速度

# 实验性功能
experimental:
  # 碰撞检测
  collision_detection:
    enabled: false              # 启用碰撞检测
    position_threshold: 0.005   # 位置变化阈值（米）
    stagnation_duration: 2.0    # 停滞时长阈值（秒）
    sample_interval: 0.2        # 采样间隔（秒）
    min_samples: 3              # 最小连续停滞采样数
    debug: false                # 启用调试日志

  # 抓取验证
  grasp_verification:
    enabled: false   # 启用抓取验证
    max_retries: 2   # 最大重试次数
    debug: true      # 保存调试图像
```

## 基础动作原语

### pick - 抓取物体

```
用户: "抓取位置 x=0.6, y=0.2, z=0.1 的物体"
```

**执行流程**：
1. 移动到预抓取位置（目标上方）
2. 打开夹爪
3. 下降到目标位置
4. 闭合夹爪
5. 提升物体

**参数**：
- `position`: 目标位置 [x, y, z]（米）
- `approach_height`: 预抓取高度偏移（默认 0.1 米）
- `speed`: 运动速度比例（0-1，默认 0.3）

### place - 放置物体

```
用户: "把物体放到 x=0.5, y=-0.3, z=0.15"
```

**执行流程**：
1. 提升到安全高度
2. 水平移动到目标上方
3. 下降到目标位置
4. 打开夹爪
5. 向上撤回

### move_to - 移动到指定位置

```
用户: "移动到位置 x=0.7, y=0.0, z=0.3"
```

**参数**：
- `position`: 目标位置 [x, y, z]
- `orientation`: 姿态 [roll, pitch, yaw]（可选，默认夹爪向下）

### home - 回到初始位置

```
用户: "回到初始位置"
```

支持单臂或双臂：`arm: "left" | "right" | "both"`

## 视觉功能（需启用 VLM）

### pick_by_name - 按名称抓取

```
用户: "抓取红色杯子"
```

**功能**：使用视觉定位物体后自动抓取

**参数**：
- `object_name`: 物体名称（如 "红色杯子"、"蓝色方块"）
- `use_d455`: 使用深度相机（推荐，更精确）
- `arm`: "left" | "right" | "auto"（自动选择）

### locate_object - 定位物体

```
用户: "找到黄色方块的位置"
```

**功能**：仅定位物体，不移动机器人

### describe_scene - 描述场景

```
用户: "描述当前场景"
```

**功能**：获取工作区域的视觉描述

## 实验性功能

### 1. 碰撞检测

**功能**：监测机械臂运动时的位置停滞，检测潜在碰撞

**启动方式**：

方式一：配置文件启用（推荐）
```yaml
# config/baxter.yaml
experimental:
  collision_detection:
    enabled: true
    position_threshold: 0.005   # 位置变化阈值（米）
    stagnation_duration: 2.0    # 停滞时长阈值（秒）
    sample_interval: 0.2        # 采样间隔（秒）
    min_samples: 3              # 最小连续停滞采样数
    debug: false                # 启用调试日志
```

方式二：运行时动态启用（通过 API）
```python
# 通过 API 调用启用/禁用
```

**工作原理**：
- 周期性采样机械臂位置
- 检测位置变化是否低于阈值
- 连续停滞超过设定时间则触发碰撞检测
- 自动停止运动并返回碰撞信号

**参数说明**：
- `enabled`: 是否启用（默认 false）
- `position_threshold`: 位置变化阈值，低于此值视为停滞（默认 0.005 米）
- `stagnation_duration`: 停滞多久触发碰撞检测（默认 2.0 秒）
- `sample_interval`: 采样间隔（默认 0.2 秒）
- `min_samples`: 最小连续停滞采样数（默认 3）
- `debug`: 是否输出调试日志（默认 false）

**注意事项**：
- 默认禁用，需手动启用
- 可能产生误报，建议先在模拟环境测试
- 采用保守阈值以避免误触发
- 完全解耦，禁用时不影响原有功能

### 2. 抓取成功检测

**功能**：抓取后使用腕部相机验证是否成功抓住物体，失败时自动重试

**前置条件**：
- 需要启用 VLM 功能（`vlm.enabled: true`）
- 需要腕部相机可用

**启动方式**：

方式一：配置文件启用（推荐）
```yaml
# config/baxter.yaml
vlm:
  enabled: true
  provider: "claude"
  api_key: "your-api-key"

experimental:
  grasp_verification:
    enabled: true    # 启用抓取验证
    max_retries: 2   # 最大重试次数
    debug: true      # 保存调试图像到 debug/grasp_verification/
```

方式二：命令行参数（覆盖配置文件）
```bash
baxter-claw-bridge --config config/baxter.yaml --enable-grasp-verification --grasp-verify-retries 3
```

**工作流程**：
1. 执行抓取动作
2. 使用腕部相机拍摄夹爪
3. VLM 分析是否成功抓住物体
4. 失败则自动重试（最多 N 次）
5. 返回验证结果

**参数说明**：
- `enabled`: 是否启用（默认 false）
- `max_retries`: 最大重试次数（默认 2）
- `debug`: 是否保存调试图像（默认 true）
  - 启用后，每次验证的图像会保存到 `debug/grasp_verification/` 目录
  - 文件名格式：`grasp_verify_{arm}_{timestamp}.jpg`
  - 可用于检查相机视角和VLM识别效果

**注意事项**：
- 会增加抓取时间（每次验证约 2-3 秒）
- 实验性功能，准确率取决于 VLM 性能
- 完全解耦，禁用时不影响原有功能
- 命令行参数优先级高于配置文件
- 调试图像会占用磁盘空间，建议定期清理

## 命令行参数

```bash
baxter-claw-bridge [选项]

选项：
  --config PATH                    配置文件路径
  --host HOST                      绑定主机（默认 0.0.0.0）
  --port PORT                      绑定端口（默认 8420）
  --enable-grasp-verification      启用抓取验证（覆盖配置文件）
  --grasp-verify-retries N         抓取验证最大重试次数（覆盖配置文件）
```

**注意**：命令行参数优先级高于配置文件，可用于临时覆盖配置。

## 测试模式

### 使用 Mock 驱动测试

```yaml
# config/baxter.yaml
driver:
  type: "mock"
```

```bash
# 启动服务
baxter-claw-bridge --config config/baxter.yaml

# 运行测试
pytest tests/ -v

# 测试动作原语
python examples/test_primitives.py

# 测试碰撞检测
python test_collision_detection.py
```

## 安全注意事项

1. **首次使用必须在 mock 模式下测试**
2. **确保工作空间内无障碍物和人员**
3. **保持急停按钮可触及**
4. **验证工作空间限制配置正确**
5. **监控机器人自主运行过程**
6. **实验性功能需充分测试后再用于生产**

## 故障排查

### 连接失败
- 检查 ROS 环境是否正确配置
- 确认 Baxter SDK 已安装
- 验证机器人网络连接

### 动作执行失败
- 检查目标位置是否在工作空间内
- 确认机械臂未处于错误状态
- 查看日志中的详细错误信息

### 视觉功能不可用
- 确认 `vlm.enabled: true`
- 检查 API 密钥配置
- 验证相机连接正常

### 抓取验证失败
- 确保腕部相机可用
- 检查 VLM 配置正确
- 查看验证日志中的推理信息

## 更多信息

- 完整文档：[docs/](docs/)
- API 参考：[docs/api.md](docs/api.md)
- 架构说明：[docs/architecture.md](docs/architecture.md)
- 碰撞检测详细说明：[COLLISION_DETECTION.md](COLLISION_DETECTION.md)
- 抓取验证详细说明：[GRASP_VERIFICATION.md](GRASP_VERIFICATION.md)