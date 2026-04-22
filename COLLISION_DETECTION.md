# 碰撞检测功能文档

## 概述

碰撞检测功能通过监控机械臂运动过程中的位置变化，检测机械臂是否与障碍物发生碰撞。当机械臂位置在一段时间内保持不变（停滞）时，系统会判断为发生碰撞并停止运动。

## 特性

- **解耦设计**：完全独立的模块，可以随时启用/禁用，不影响核心功能
- **安全可靠**：保守的阈值设置，避免误判
- **非侵入式**：在后台线程运行，不阻塞主程序
- **可配置**：所有参数都可以通过配置文件或代码动态调整

## 配置

在 `config/baxter.yaml` 中添加以下配置：

```yaml
# 碰撞检测（实验性功能）
collision_detection:
  enabled: false              # 设置为 true 启用碰撞检测
  position_threshold: 0.005   # 5mm - 判断为移动的最小位置变化
  stagnation_duration: 2.0    # 2秒 - 停滞多久后判断为碰撞
  sample_interval: 0.2        # 200ms - 采样频率
  min_samples: 3              # 最少连续停滞采样次数
  debug: false                # 启用调试日志
```

### 参数说明

- **enabled**: 是否启用碰撞检测（默认：false）
- **position_threshold**: 位置变化阈值（米），小于此值认为位置未变化（默认：0.005m = 5mm）
- **stagnation_duration**: 停滞时间阈值（秒），超过此时间判断为碰撞（默认：2.0秒）
- **sample_interval**: 采样间隔（秒），多久检查一次位置（默认：0.2秒）
- **min_samples**: 最少连续停滞采样次数，避免瞬时停顿误判（默认：3次）
- **debug**: 是否输出调试信息（默认：false）

## 使用方法

### 方法1：通过配置文件启用（推荐）

1. 编辑 `config/baxter.yaml`，设置 `collision_detection.enabled: true`
2. 正常使用机械臂，碰撞检测会自动工作

```python
from bridge.arm_manager import ArmManager

# 初始化（会自动加载配置）
manager = ArmManager(config_path='config/baxter.yaml')

# 碰撞检测已根据配置文件自动启用/禁用
```

### 方法2：代码中动态启用

```python
from bridge.arm_manager import ArmManager

# 初始化
manager = ArmManager(config_path='config/baxter.yaml')

# 动态启用碰撞检测
manager.collision_detector.enable()

# 或者更新配置
manager.collision_detector.update_config(
    enabled=True,
    position_threshold=0.003,  # 更敏感：3mm
    stagnation_duration=1.5,   # 更快响应：1.5秒
    debug=True                 # 启用调试输出
)
```

### 方法3：手动监控特定运动

```python
from bridge.arm_manager import ArmManager

manager = ArmManager(config_path='config/baxter.yaml')
manager.connect()
manager.enable()

# 定义碰撞回调
def on_collision():
    print("检测到碰撞！停止运动")
    manager.driver.emergency_stop()

# 定义位置获取函数
def get_arm_position():
    pose = manager.driver.get_endpoint_pose('right')
    return pose[:3] if pose else None

# 启用碰撞检测
manager.collision_detector.enable()

# 开始监控
manager.collision_detector.start_monitoring(
    arm='right',
    get_position_func=get_arm_position,
    on_collision=on_collision
)

# 执行运动
manager.primitives.move_to('right', [0.6, 0.0, 0.0])

# 停止监控并获取结果
result = manager.collision_detector.stop_monitoring()
print(f"碰撞检测结果: {result}")
```

## 工作原理

1. **启动监控**：在运动开始前启动位置监控线程
2. **周期采样**：按配置的间隔（默认200ms）采样机械臂位置
3. **计算变化**：计算当前位置与上次位置的欧氏距离
4. **判断停滞**：如果位置变化小于阈值，计数器+1，记录停滞开始时间
5. **触发检测**：当连续停滞次数 ≥ min_samples 且停滞时间 ≥ stagnation_duration 时，触发碰撞检测
6. **执行回调**：调用用户提供的碰撞回调函数（如果有）
7. **停止监控**：自动停止监控线程

## 调优建议

### 提高灵敏度（更容易检测碰撞）

```yaml
collision_detection:
  enabled: true
  position_threshold: 0.003   # 降低阈值：3mm
  stagnation_duration: 1.0    # 缩短时间：1秒
  min_samples: 2              # 减少采样次数
```

### 降低误报（更保守）

```yaml
collision_detection:
  enabled: true
  position_threshold: 0.008   # 提高阈值：8mm
  stagnation_duration: 3.0    # 延长时间：3秒
  min_samples: 5              # 增加采样次数
```

### 快速响应（高频采样）

```yaml
collision_detection:
  enabled: true
  sample_interval: 0.1        # 100ms采样一次
  stagnation_duration: 1.0    # 1秒检测
```

## 注意事项

1. **实验性功能**：这是一个实验性功能，建议在测试环境中充分验证后再用于生产
2. **默认禁用**：为了安全，默认是禁用状态，需要手动启用
3. **不影响核心功能**：即使碰撞检测模块出错，也不会影响机械臂的正常运动
4. **慢速运动**：对于非常慢的运动，可能需要调整参数以避免误判
5. **快速运动**：对于快速运动，建议降低 `sample_interval` 以提高检测频率
6. **力控不可用**：此方法基于位置检测，不是真正的力控，无法检测轻微接触

## 测试

运行测试脚本验证功能：

```bash
python test_collision_detection.py
```

测试包括：
- 默认禁用状态测试
- 碰撞检测功能测试
- 无误报测试（正常运动不触发）
- 动态配置更新测试

## 示例场景

### 场景1：桌面挤压检测

机械臂下降到桌面时，如果继续施加力，会被检测为碰撞：

```python
manager = ArmManager(config_path='config/baxter.yaml')
manager.collision_detector.enable()

# 尝试下降到桌面
result = manager.primitives.move_to('right', [0.6, 0.0, -0.2])

# 检查是否发生碰撞
if manager.collision_detector.collision_detected():
    print("检测到与桌面碰撞，已停止")
```

### 场景2：障碍物检测

机械臂移动过程中遇到障碍物：

```python
manager = ArmManager(config_path='config/baxter.yaml')
manager.collision_detector.update_config(
    enabled=True,
    stagnation_duration=1.5,  # 快速响应
    debug=True
)

# 执行运动
result = manager.primitives.pick('right', [0.7, 0.2, 0.0])

# 检查结果
if not result['success']:
    if manager.collision_detector.collision_detected():
        print("运动失败：检测到碰撞")
```

## API 参考

### CollisionDetector 类

#### 方法

- `enable()`: 启用碰撞检测
- `disable()`: 禁用碰撞检测
- `start_monitoring(arm, get_position_func, on_collision)`: 开始监控
- `stop_monitoring()`: 停止监控并返回结果
- `is_monitoring()`: 检查是否正在监控
- `collision_detected()`: 检查是否检测到碰撞
- `get_config()`: 获取当前配置
- `update_config(**kwargs)`: 更新配置参数

#### 返回值

`stop_monitoring()` 返回字典：
```python
{
    'collision_detected': bool,  # 是否检测到碰撞
    'message': str               # 描述信息
}
```

## 故障排除

### 问题：碰撞检测不工作

**解决方案**：
1. 检查配置文件中 `enabled: true`
2. 确认 `get_position_func` 返回有效位置
3. 启用 `debug: true` 查看详细日志

### 问题：频繁误报

**解决方案**：
1. 增加 `position_threshold`（如 0.008）
2. 增加 `stagnation_duration`（如 3.0）
3. 增加 `min_samples`（如 5）

### 问题：检测太慢

**解决方案**：
1. 减少 `sample_interval`（如 0.1）
2. 减少 `stagnation_duration`（如 1.0）
3. 减少 `min_samples`（如 2）

## 未来改进

- [ ] 支持力传感器集成（真正的力控）
- [ ] 支持不同运动阶段的不同阈值
- [ ] 自动学习和调整参数
- [ ] 碰撞后的自动恢复策略
- [ ] 碰撞位置和方向分析
