# 碰撞检测功能使用手册

## 目录

1. [功能概述](#功能概述)
2. [工作原理](#工作原理)
3. [配置说明](#配置说明)
4. [使用方法](#使用方法)
5. [参数调优](#参数调优)
6. [实际案例](#实际案例)
7. [故障排除](#故障排除)
8. [API 参考](#api-参考)

---

## 功能概述

碰撞检测功能通过监控机械臂运动过程中的位置变化，自动检测机械臂是否与障碍物发生碰撞。当机械臂位置在一段时间内保持不变（停滞）时，系统会判断为发生碰撞并停止运动。

### 核心特性

- ✅ **完全解耦**：独立模块，可随时启用/禁用，不影响核心功能
- ✅ **安全可靠**：保守的默认阈值，避免误判
- ✅ **非侵入式**：后台线程运行，不阻塞主程序
- ✅ **灵活配置**：所有参数可通过配置文件或代码动态调整
- ✅ **易于使用**：提供 3 种使用方式，适应不同场景

### 适用场景

1. **桌面挤压检测** - 机械臂下降到桌面时持续施力
2. **障碍物检测** - 运动过程中遇到意外障碍物
3. **卡住检测** - 物体被卡住无法移动
4. **过载保护** - 负载过重导致运动停滞

---

## 工作原理

### 检测流程

```
1. 启动监控
   ↓
2. 周期采样位置 (每 200ms)
   ↓
3. 计算位置变化 (欧氏距离)
   ↓
4. 判断是否停滞 (变化 < 5mm)
   ↓
5. 累积停滞时间和次数
   ↓
6. 满足条件？(≥3次 且 ≥2秒)
   ↓ 是
7. 触发碰撞检测
   ↓
8. 执行回调函数
   ↓
9. 停止监控
```

### 核心逻辑

**判断条件**（同时满足）：
- 位置变化 < `position_threshold`（默认 5mm）
- 连续停滞次数 ≥ `min_samples`（默认 3 次）
- 停滞持续时间 ≥ `stagnation_duration`（默认 2 秒）

**关键点**：
- IK 求解成功
- 运动命令执行正常
- 但机械臂位置长时间不变
- → 判断为碰撞

---

## 配置说明

### 配置文件位置

`config/baxter.yaml`

### 配置参数

```yaml
# 碰撞检测（实验性功能）
collision_detection:
  enabled: false              # 是否启用碰撞检测
  position_threshold: 0.005   # 位置变化阈值（米）
  stagnation_duration: 2.0    # 停滞时间阈值（秒）
  sample_interval: 0.2        # 采样间隔（秒）
  min_samples: 3              # 最少连续停滞采样次数
  debug: false                # 是否输出调试日志
```

### 参数详解

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | `false` | 是否启用碰撞检测。默认禁用，需手动启用 |
| `position_threshold` | float | `0.005` | 位置变化阈值（米）。小于此值认为位置未变化。<br>- 降低：更敏感，更容易检测碰撞<br>- 提高：更保守，减少误报 |
| `stagnation_duration` | float | `2.0` | 停滞时间阈值（秒）。超过此时间判断为碰撞。<br>- 降低：更快响应<br>- 提高：更保守，避免误判 |
| `sample_interval` | float | `0.2` | 采样间隔（秒）。多久检查一次位置。<br>- 降低：更高频率，更快检测<br>- 提高：降低 CPU 占用 |
| `min_samples` | int | `3` | 最少连续停滞采样次数。避免瞬时停顿误判。<br>- 降低：更快触发<br>- 提高：更保守 |
| `debug` | bool | `false` | 是否输出调试日志。用于调试和参数调优 |

### 预设配置方案

#### 1. 保守模式（低误报）

适用于：精细操作、避免误报

```yaml
collision_detection:
  enabled: true
  position_threshold: 0.008   # 8mm
  stagnation_duration: 3.0    # 3秒
  min_samples: 5              # 5次
  sample_interval: 0.2
  debug: false
```

#### 2. 平衡模式（推荐）

适用于：一般使用场景

```yaml
collision_detection:
  enabled: true
  position_threshold: 0.005   # 5mm
  stagnation_duration: 2.0    # 2秒
  min_samples: 3              # 3次
  sample_interval: 0.2
  debug: false
```

#### 3. 敏感模式（快速响应）

适用于：安全关键场景、快速响应

```yaml
collision_detection:
  enabled: true
  position_threshold: 0.003   # 3mm
  stagnation_duration: 1.0    # 1秒
  min_samples: 2              # 2次
  sample_interval: 0.15       # 150ms
  debug: false
```

---

## 使用方法

### 方法 1：配置文件启用（推荐）

**适用场景**：长期使用，系统级配置

**步骤**：

1. 编辑配置文件 `config/baxter.yaml`：

```yaml
collision_detection:
  enabled: true  # 改为 true
```

2. 启动系统，碰撞检测自动生效：

```python
from bridge.arm_manager import ArmManager

# 初始化（自动加载配置）
manager = ArmManager(config_path='config/baxter.yaml')
manager.connect()
manager.enable()

# 正常使用，碰撞检测已自动启用
result = manager.primitives.pick('right', [0.6, 0.2, 0.0])
```

**优点**：
- 一次配置，永久生效
- 无需修改代码
- 适合生产环境

---

### 方法 2：代码动态启用

**适用场景**：临时测试，特定任务

**步骤**：

```python
from bridge.arm_manager import ArmManager

# 初始化
manager = ArmManager(config_path='config/baxter.yaml')
manager.connect()
manager.enable()

# 动态启用碰撞检测
manager.collision_detector.enable()

# 或者更新配置参数
manager.collision_detector.update_config(
    enabled=True,
    position_threshold=0.003,  # 更敏感
    stagnation_duration=1.5,   # 更快响应
    debug=True                 # 启用调试
)

# 执行操作
result = manager.primitives.pick('right', [0.6, 0.2, 0.0])

# 可以随时禁用
manager.collision_detector.disable()
```

**优点**：
- 灵活控制
- 可动态调整参数
- 适合测试和调试

---

### 方法 3：手动监控特定运动

**适用场景**：精细控制，自定义碰撞处理

**步骤**：

```python
from bridge.arm_manager import ArmManager

manager = ArmManager(config_path='config/baxter.yaml')
manager.connect()
manager.enable()

# 1. 定义碰撞回调函数
def on_collision():
    print("⚠ 检测到碰撞！")
    # 自定义处理逻辑
    manager.driver.emergency_stop()  # 紧急停止
    # 或者：收回机械臂
    # 或者：发送警报

# 2. 定义位置获取函数
def get_arm_position():
    pose = manager.driver.get_endpoint_pose('right')
    return pose[:3] if pose else None  # 返回 [x, y, z]

# 3. 启用碰撞检测
manager.collision_detector.enable()

# 4. 开始监控
manager.collision_detector.start_monitoring(
    arm='right',
    get_position_func=get_arm_position,
    on_collision=on_collision
)

# 5. 执行运动
result = manager.primitives.move_to('right', [0.6, 0.0, 0.0])

# 6. 停止监控并获取结果
collision_result = manager.collision_detector.stop_monitoring()

print(f"碰撞检测结果: {collision_result}")
# 输出: {'collision_detected': True/False, 'message': '...'}
```

**优点**：
- 完全控制
- 自定义碰撞处理
- 适合复杂场景

---

## 参数调优

### 调优流程

1. **启用调试模式**

```yaml
collision_detection:
  enabled: true
  debug: true  # 启用调试输出
```

2. **观察日志输出**

```
[CollisionDetector] right position change: 0.010000m (threshold: 0.005000m)
[CollisionDetector] right position change: 0.000000m (threshold: 0.005000m)
[CollisionDetector] Stagnation started
[CollisionDetector] Stagnant count: 1/3, duration: 0.00/2.00s
...
```

3. **根据实际情况调整参数**

### 常见问题和调优方案

#### 问题 1：频繁误报（正常运动被判断为碰撞）

**原因**：参数过于敏感

**解决方案**：

```yaml
collision_detection:
  position_threshold: 0.008   # 提高阈值（原 0.005）
  stagnation_duration: 3.0    # 延长时间（原 2.0）
  min_samples: 5              # 增加次数（原 3）
```

#### 问题 2：检测太慢（碰撞发生很久才检测到）

**原因**：参数过于保守

**解决方案**：

```yaml
collision_detection:
  position_threshold: 0.003   # 降低阈值（原 0.005）
  stagnation_duration: 1.0    # 缩短时间（原 2.0）
  sample_interval: 0.1        # 提高频率（原 0.2）
  min_samples: 2              # 减少次数（原 3）
```

#### 问题 3：慢速运动被误判

**原因**：运动速度慢，位置变化小

**解决方案**：

```yaml
collision_detection:
  position_threshold: 0.002   # 降低阈值以适应慢速
  stagnation_duration: 3.0    # 延长时间避免误判
```

#### 问题 4：快速运动检测不到

**原因**：采样频率不够

**解决方案**：

```yaml
collision_detection:
  sample_interval: 0.1        # 提高采样频率
  stagnation_duration: 1.0    # 缩短检测时间
```

---

## 实际案例

### 案例 1：桌面挤压检测

**场景**：机械臂下降到桌面，如果继续施力会损坏

**代码**：

```python
from bridge.arm_manager import ArmManager

# 初始化并启用碰撞检测
manager = ArmManager(config_path='config/baxter.yaml')
manager.collision_detector.update_config(
    enabled=True,
    position_threshold=0.005,
    stagnation_duration=2.0
)

manager.connect()
manager.enable()

# 尝试下降到桌面
print("下降到桌面...")
result = manager.primitives.move_to('right', [0.6, 0.0, -0.20])

# 检查是否发生碰撞
if manager.collision_detector.collision_detected():
    print("⚠ 检测到与桌面碰撞，已停止")
    print("机械臂已安全停止，未造成损坏")
else:
    print("✓ 运动完成，无碰撞")
```

---

### 案例 2：抓取时障碍物检测

**场景**：抓取物体时，路径上有障碍物

**代码**：

```python
from bridge.arm_manager import ArmManager
import asyncio

async def safe_pick():
    manager = ArmManager(config_path='config/baxter.yaml')
    
    # 启用敏感模式（快速响应）
    manager.collision_detector.update_config(
        enabled=True,
        position_threshold=0.003,
        stagnation_duration=1.5,
        debug=True
    )
    
    manager.connect()
    manager.enable()
    
    # 尝试抓取
    print("开始抓取...")
    result = await manager.primitives.pick_by_name(
        arm='right',
        object_name='red block',
        speed=0.2
    )
    
    # 检查结果
    if not result['success']:
        if manager.collision_detector.collision_detected():
            print("⚠ 抓取失败：检测到障碍物")
            print("建议：清理工作区域或调整抓取路径")
        else:
            print("✗ 抓取失败：其他原因")
    else:
        print("✓ 抓取成功")
    
    manager.disconnect()

asyncio.run(safe_pick())
```

---

### 案例 3：自定义碰撞处理

**场景**：碰撞后自动收回机械臂

**代码**：

```python
from bridge.arm_manager import ArmManager

manager = ArmManager(config_path='config/baxter.yaml')
manager.connect()
manager.enable()

# 定义碰撞处理函数
def handle_collision():
    print("⚠ 碰撞检测！执行安全收回...")
    
    # 1. 停止当前运动
    manager.driver.emergency_stop()
    
    # 2. 获取当前位置
    current_pose = manager.driver.get_endpoint_pose('right')
    if current_pose:
        # 3. 向上收回 10cm
        safe_pose = current_pose.copy()
        safe_pose[2] += 0.10  # Z 轴 +10cm
        
        # 4. 移动到安全位置
        manager.driver.enable()  # 重新启用
        manager.primitives.move_to('right', safe_pose[:3])
        
    print("✓ 已收回到安全位置")

# 启用碰撞检测
manager.collision_detector.enable()

# 定义位置获取函数
def get_position():
    pose = manager.driver.get_endpoint_pose('right')
    return pose[:3] if pose else None

# 开始监控
manager.collision_detector.start_monitoring(
    arm='right',
    get_position_func=get_position,
    on_collision=handle_collision
)

# 执行运动
result = manager.primitives.move_to('right', [0.8, 0.0, 0.0])

# 停止监控
manager.collision_detector.stop_monitoring()
manager.disconnect()
```

---

## 故障排除

### 问题：碰撞检测不工作

**症状**：明显碰撞但未检测到

**排查步骤**：

1. 检查是否启用：

```python
print(manager.collision_detector.get_config())
# 确认 'enabled': True
```

2. 检查位置获取函数：

```python
def get_position():
    pose = manager.driver.get_endpoint_pose('right')
    print(f"当前位置: {pose}")  # 添加调试输出
    return pose[:3] if pose else None
```

3. 启用调试模式：

```yaml
collision_detection:
  debug: true
```

4. 查看日志输出，确认采样正常

---

### 问题：频繁误报

**症状**：正常运动被判断为碰撞

**解决方案**：

1. 提高位置阈值：

```yaml
position_threshold: 0.008  # 从 0.005 提高到 0.008
```

2. 延长停滞时间：

```yaml
stagnation_duration: 3.0  # 从 2.0 延长到 3.0
```

3. 增加最少采样次数：

```yaml
min_samples: 5  # 从 3 增加到 5
```

---

### 问题：检测延迟太大

**症状**：碰撞发生后很久才检测到

**解决方案**：

1. 提高采样频率：

```yaml
sample_interval: 0.1  # 从 0.2 降低到 0.1
```

2. 缩短停滞时间：

```yaml
stagnation_duration: 1.0  # 从 2.0 缩短到 1.0
```

3. 降低位置阈值：

```yaml
position_threshold: 0.003  # 从 0.005 降低到 0.003
```

---

## API 参考

### CollisionDetector 类

#### 初始化

```python
from bridge.collision_detector import CollisionDetector

detector = CollisionDetector(
    enabled=False,              # 是否启用
    position_threshold=0.005,   # 位置阈值（米）
    stagnation_duration=2.0,    # 停滞时间（秒）
    sample_interval=0.2,        # 采样间隔（秒）
    min_samples=3,              # 最少采样次数
    debug=False                 # 调试模式
)
```

#### 方法

##### enable()

启用碰撞检测

```python
manager.collision_detector.enable()
```

##### disable()

禁用碰撞检测

```python
manager.collision_detector.disable()
```

##### start_monitoring(arm, get_position_func, on_collision)

开始监控机械臂位置

**参数**：
- `arm` (str): 机械臂标识（'left' 或 'right'）
- `get_position_func` (callable): 获取位置的函数，返回 [x, y, z]
- `on_collision` (callable, optional): 碰撞回调函数

**返回**：
- `bool`: 是否成功启动监控

**示例**：

```python
def get_position():
    pose = manager.driver.get_endpoint_pose('right')
    return pose[:3] if pose else None

def on_collision():
    print("碰撞检测！")

manager.collision_detector.start_monitoring(
    arm='right',
    get_position_func=get_position,
    on_collision=on_collision
)
```

##### stop_monitoring()

停止监控并返回结果

**返回**：
- `dict`: 包含 'collision_detected' (bool) 和 'message' (str)

**示例**：

```python
result = manager.collision_detector.stop_monitoring()
print(result)
# {'collision_detected': True, 'message': 'Collision detected'}
```

##### is_monitoring()

检查是否正在监控

**返回**：
- `bool`: 是否正在监控

##### collision_detected()

检查是否检测到碰撞

**返回**：
- `bool`: 是否检测到碰撞

##### get_config()

获取当前配置

**返回**：
- `dict`: 当前配置参数

**示例**：

```python
config = manager.collision_detector.get_config()
print(config)
# {
#     'enabled': True,
#     'position_threshold': 0.005,
#     'stagnation_duration': 2.0,
#     'sample_interval': 0.2,
#     'min_samples': 3,
#     'debug': False
# }
```

##### update_config(**kwargs)

更新配置参数

**参数**：
- `enabled` (bool, optional): 是否启用
- `position_threshold` (float, optional): 位置阈值
- `stagnation_duration` (float, optional): 停滞时间
- `sample_interval` (float, optional): 采样间隔
- `min_samples` (int, optional): 最少采样次数
- `debug` (bool, optional): 调试模式

**示例**：

```python
manager.collision_detector.update_config(
    enabled=True,
    position_threshold=0.003,
    debug=True
)
```

---

## 测试

### 运行单元测试

```bash
python test_collision_detection.py
```

**测试内容**：
- ✓ 默认禁用状态
- ✓ 碰撞检测功能
- ✓ 无误报（正常运动）
- ✓ 动态配置更新

### 运行演示程序

```bash
python demo_collision_detection.py
```

**演示内容**：
1. 配置对比
2. 抓取操作碰撞检测
3. 移动操作障碍物检测
4. 桌面挤压检测

---

## 注意事项

### 重要提示

1. **实验性功能**：这是一个实验性功能，建议在测试环境中充分验证后再用于生产
2. **默认禁用**：为了安全，默认是禁用状态，需要手动启用
3. **不影响核心功能**：即使碰撞检测模块出错，也不会影响机械臂的正常运动
4. **基于位置检测**：不是真正的力控，无法检测轻微接触

### 限制

1. **检测延迟**：存在一定延迟（默认约 2 秒），不适合需要瞬时响应的场景
2. **慢速运动**：对于非常慢的运动，可能需要调整参数以避免误判
3. **快速运动**：对于快速运动，建议降低 `sample_interval` 以提高检测频率
4. **无力感知**：无法检测轻微接触或力的大小，只能检测位置停滞

### 最佳实践

1. **先测试后部署**：在测试环境充分验证参数设置
2. **启用调试模式**：调试时启用 `debug: true` 观察详细日志
3. **根据场景调整**：不同场景使用不同的参数配置
4. **定期检查**：定期检查碰撞检测是否正常工作
5. **结合其他安全措施**：碰撞检测是辅助手段，不能替代其他安全措施

---

## 未来改进

- [ ] 集成力传感器（真正的力控）
- [ ] 自适应阈值调整
- [ ] 碰撞后自动恢复策略
- [ ] 碰撞位置和方向分析
- [ ] 不同运动阶段的不同阈值
- [ ] 机器学习优化参数

---

## 相关文档

- [主文档](README_CN.md)
- [安装指南](INSTALL.md)
- [API 参考](docs/api.md)
- [安全指南](docs/safety.md)

---

**最后更新**：2026-04-22
