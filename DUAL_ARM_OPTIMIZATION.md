# 双臂支持优化文档

## 概述

本次优化为 Baxter-Claw 项目添加了完整的双臂支持，使 LLM 能够智能地选择和控制左臂、右臂或双臂协作。

**优化日期**: 2026-04-13  
**版本**: v0.3.1

## 主要改进

### 1. 扩展的动作原语集合

#### 单臂动作（支持左/右臂选择）
- `pick_by_name` - 抓取物体，支持 `arm` 参数：
  - `"left"` - 使用左臂
  - `"right"` - 使用右臂
  - `"auto"` - 自动选择（基于物体位置）
  
- `place` - 放置物体，支持 `arm` 参数
- `move_to` - 移动到指定位置，需要指定 `arm`
- `home` - 回到原位，支持 `arm` 参数：
  - `"left"` / `"right"` - 单臂回原位
  - `"both"` - 双臂同时回原位
  
- `gripper_open` / `gripper_close` - 夹爪控制，支持 `arm` 参数：
  - `"left"` / `"right"` - 单个夹爪
  - `"both"` - 两个夹爪同时操作

#### 双臂协作动作
- `bimanual_pick` - 双臂同时抓取大物体
  - 参数：`object_name`
  - 自动计算左右臂的抓取位置
  
- `handover` - 臂间传递物体
  - 参数：`from_arm`, `to_arm`
  - 自动协调两个臂的动作

### 2. 智能臂选择逻辑

#### 基于物体位置的自动选择
当 `arm` 参数设置为 `"auto"` 时，系统会：
1. 首先使用 VLM 定位物体
2. 根据物体的 y 坐标判断位置：
   - `y > 0.05m` → 物体在左侧，使用左臂
   - `y < -0.05m` → 物体在右侧，使用右臂
   - `-0.05m ≤ y ≤ 0.05m` → 物体在中间，默认使用右臂

#### 实现代码
```python
def _choose_arm_by_position(self, position: list) -> str:
    """根据物体位置选择手臂"""
    y = position[1] if len(position) > 1 else 0.0
    
    if y > 0.05:  # 左侧
        return 'left'
    elif y < -0.05:  # 右侧
        return 'right'
    else:  # 中间，默认右臂
        return 'right'
```

### 3. 机器人状态跟踪

系统现在维护每个臂的状态：

```python
robot_state = {
    'left_arm': {
        'holding_object': False,  # 是否持有物体
        'object_name': None,      # 持有的物体名称
        'last_position': None     # 最后位置
    },
    'right_arm': {
        'holding_object': False,
        'object_name': None,
        'last_position': None
    }
}
```

#### 状态更新规则
- **pick_by_name 成功** → 对应臂的 `holding_object = True`
- **place 成功** → 对应臂的 `holding_object = False`
- **bimanual_pick 成功** → 两个臂都设置为持有物体
- **handover 成功** → 从源臂移除，添加到目标臂

### 4. 增强的 LLM 意图识别

#### 新的 Prompt 特性
- 明确告知 LLM 机器人有两个臂
- 提供臂选择规则和示例
- 包含当前机器人状态（哪个臂持有物体）
- 支持识别双臂协作意图

#### 示例对话
```
用户: "帮我拿一下红色的杯子"
LLM: {"action": "pick_by_name", "params": {"object_name": "红色的杯子", "arm": "auto"}}
系统: [自动选择] 物体在 [0.6, 0.15, 0.1]，选择左臂

用户: "用右手拿白色盒子"
LLM: {"action": "pick_by_name", "params": {"object_name": "白色盒子", "arm": "right"}}

用户: "用两只手拿那个大箱子"
LLM: {"action": "bimanual_pick", "params": {"object_name": "大箱子"}}

用户: "把物体从右手传到左手"
LLM: {"action": "handover", "params": {"from_arm": "right", "to_arm": "left"}}

用户: "两只手都回原位"
LLM: {"action": "home", "params": {"arm": "both"}}
```

## 技术实现细节

### 修改的文件
- `openclaw_plugin/baxter_claw_plugin.py` - 主要修改文件

### 关键方法

#### 1. `_choose_arm_by_position(position)`
根据物体位置自动选择手臂

#### 2. `execute_action(action, params)`
扩展支持所有新动作类型：
- 处理 `arm` 参数（left/right/auto/both）
- 调用相应的 Bridge API
- 返回包含 `arm_used` 的结果

#### 3. `_execute_workflow(context)`
增强的工作流执行：
- 维护 `robot_state`
- 根据动作结果更新状态
- 将状态传递给 LLM 用于决策

#### 4. `_build_workflow_prompt(context)`
增强的 prompt 构建：
- 包含机器人状态信息
- 提供双臂动作选项
- 给出臂选择建议

## 使用示例

### 基本单臂操作
```python
plugin = BaxterClawPlugin()

# 自动选择手臂
response = plugin.handle_message("拿一下桌上的红杯子")

# 指定使用左臂
response = plugin.handle_message("用左手拿蓝色盒子")

# 指定使用右臂
response = plugin.handle_message("用右臂放到前面")
```

### 双臂协作
```python
# 双臂抓取大物体
response = plugin.handle_message("用两只手拿那个大箱子")

# 臂间传递
response = plugin.handle_message("把物体从右手传到左手")

# 双臂同时回原位
response = plugin.handle_message("两只手都回到原位")
```

### 夹爪控制
```python
# 打开左臂夹爪
response = plugin.handle_message("打开左边夹爪")

# 同时打开两个夹爪
response = plugin.handle_message("打开两个夹爪")
```

## API 端点

所有现有的 Bridge API 端点都已支持 `arm` 参数：

### 单臂原语
```bash
# Pick
POST /primitives/pick
{
  "arm": "left",  # or "right"
  "position": [0.6, 0.2, 0.1],
  "approach_height": 0.1
}

# Place
POST /primitives/place
{
  "arm": "right",
  "position": [0.7, -0.3, 0.15]
}

# Home
POST /primitives/home
{
  "arm": "left"  # or "right"
}
```

### 双臂协作
```bash
# Bimanual Pick
POST /dualarm/bimanual_pick
{
  "object_position": [0.6, 0.0, 0.1],
  "left_offset": [-0.05, 0.0, 0.0],
  "right_offset": [0.05, 0.0, 0.0]
}

# Handover
POST /dualarm/handover
{
  "from_arm": "right",
  "to_arm": "left",
  "handover_position": [0.6, 0.0, 0.3]
}
```

## 优势

### 1. 智能化
- 自动根据物体位置选择最优手臂
- 减少不必要的臂移动
- 提高操作效率

### 2. 灵活性
- 支持明确指定手臂
- 支持自动选择
- 支持双臂协作

### 3. 状态感知
- 跟踪每个臂的状态
- LLM 可以基于状态做决策
- 避免冲突操作

### 4. 用户友好
- 自然语言支持中英文
- 支持多种表达方式
- 智能理解用户意图

## 未来改进方向

1. **更智能的臂选择**
   - 考虑臂的当前位置
   - 考虑运动学可达性
   - 避免奇异点

2. **碰撞检测**
   - 预测两个臂的运动轨迹
   - 避免臂间碰撞
   - 动态调整路径

3. **负载均衡**
   - 根据物体重量选择臂
   - 考虑臂的疲劳度
   - 优化任务分配

4. **更复杂的协作**
   - 一个臂固定，另一个操作
   - 协调装配任务
   - 双臂同步轨迹

## 测试建议

### 单臂测试
```python
# 测试自动选择
test_messages = [
    "拿左边的红杯子",      # 应该选择左臂
    "拿右边的蓝盒子",      # 应该选择右臂
    "拿中间的绿瓶子",      # 应该选择右臂（默认）
]

# 测试明确指定
test_messages = [
    "用左手拿杯子",
    "用右臂放到前面",
    "左边夹爪打开",
]
```

### 双臂测试
```python
test_messages = [
    "用两只手拿大箱子",
    "把物体从右手传到左手",
    "两只手都回原位",
    "打开两个夹爪",
]
```

## 配置

无需额外配置，所有功能开箱即用。底层的 Bridge Server 和驱动已经支持双臂。

## 兼容性

- 向后兼容：未指定 `arm` 参数时默认使用右臂
- 所有现有代码无需修改
- 新功能通过参数扩展实现

## 总结

本次优化实现了完整的双臂支持，核心改进包括：

1. ✅ 扩展动作原语支持左臂、右臂、双臂
2. ✅ 基于 VLM 定位结果的智能臂选择
3. ✅ 机器人状态跟踪（左右臂状态）
4. ✅ 增强的 LLM 意图识别
5. ✅ 双臂协作动作（bimanual_pick, handover）

系统现在能够智能地理解用户意图，自动选择最优手臂，并支持复杂的双臂协作任务。