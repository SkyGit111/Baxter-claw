# Simplified Arc-Pushing Implementation

## 概述

完全重构了`bimanual_shape_ruler`任务，放弃所有复杂的关节定位和几何计算，改为最简单的"抓住红色+推动蓝色沿圆弧"的开环控制方案。

## 核心简化

### 放弃的复杂逻辑 ❌
- ❌ 绿色旋转关节定位
- ❌ 橙色旋转关节定位
- ❌ 6个尺段端部中点定位
- ❌ 尺段中心线拟合
- ❌ 中心线交点计算
- ❌ 二连杆角度计算
- ❌ theta1/theta2插值
- ❌ 右臂闭合夹爪抓取

### 新的简化方案 ✅
- ✅ VLM只定位2个点：红色抓取位置、蓝色推动位置
- ✅ 左臂抓住红色尺段并保持固定
- ✅ 右臂夹爪保持张开，推动蓝色尺段
- ✅ 右臂沿90°圆弧轨迹推动
- ✅ 圆心=红色抓取位置，起点=蓝色推动位置
- ✅ 开环控制，无反馈，简单稳定

## 修改文件

### 1. config/ruler_task.yaml
**完全重写**，只保留必要配置：

```yaml
articulated_ruler:
  # VLM定位prompt（只需2个）
  red_grasp_prompt: "the center of the grasping area on the red segment"
  blue_push_prompt: "the center of the pushing area on the blue segment"

  # 圆弧运动参数
  arc_motion:
    angle_degrees: 90              # 圆弧角度
    direction: "clockwise"         # 方向
    num_waypoints: 20              # 路径点数量
    push_z: -0.16                  # 推动高度
    approach_z_offset: 0.08        # 接近偏移
    push_speed_scale: 0.2          # 速度比例
    min_radius: 0.08               # 最小半径
    max_radius: 0.40               # 最大半径

  # 抓取参数
  grasp:
    grasp_z: -0.16                 # 抓取高度
    approach_z_offset: 0.08        # 接近偏移
    grasp_force: 30.0              # 抓取力
```

### 2. bridge/primitives.py

**新增函数**：

```python
def generate_arc_waypoints(
    center_xy, start_xy, angle_degrees, direction,
    num_waypoints, z, orientation
) -> Dict
```
- 生成圆弧轨迹waypoints
- 输入：圆心、起点、角度、方向、点数、Z高度、姿态
- 输出：waypoints列表
- 使用2D旋转公式生成圆弧

**完全重写方法**：

```python
async def bimanual_shape_ruler(
    fixed_arm, moving_arm, target_shape,
    l_shape_blue_turn_direction, config_path, dry_run
) -> Dict
```
- 从约500行简化到约350行
- 移除所有关节定位逻辑
- 移除所有端点定位逻辑
- 移除所有几何计算逻辑
- 只保留2点定位+圆弧推动

## 执行流程

```
1. 加载配置
2. VLM定位红色抓取位置
3. VLM定位蓝色推动位置
4. 准备运动坐标（XY来自VLM，Z来自配置）
5. 生成圆弧waypoints
6. 验证所有姿态（工作空间+IK）
7. [Dry run退出]
8. 左臂移动到红色抓取位置上方
9. 左臂下降
10. 左臂闭合夹爪，抓住红色尺段
11. 右臂夹爪打开（保持打开！）
12. 右臂移动到蓝色推动位置上方
13. 右臂下降到推动高度
14. 右臂沿圆弧waypoints推动（20个点）
15. 右臂抬起撤离
16. 左臂松开夹爪
17. 完成
```

## 圆弧生成算法

```python
# 输入
center = (cx, cy)  # 红色抓取位置
start = (sx, sy)   # 蓝色推动位置

# 计算向量和半径
v = start - center = (vx, vy)
r = sqrt(vx^2 + vy^2)

# 生成waypoints
for i in range(num_waypoints + 1):
    alpha = direction_sign * angle_rad * i / num_waypoints
    
    # 2D旋转
    x_i = cx + cos(alpha) * vx - sin(alpha) * vy
    y_i = cy + sin(alpha) * vx + cos(alpha) * vy
    z_i = push_z
    
    waypoint = [x_i, y_i, z_i] + orientation
```

其中：
- `direction_sign = -1` (clockwise) 或 `+1` (counterclockwise)
- `angle_rad = 90° * π/180 = 1.5708 rad`

## 关键特性

### 1. 只定位2个点
- **红色抓取位置**：VLM定位，XY用于计算，Z使用配置
- **蓝色推动位置**：VLM定位，XY用于计算，Z使用配置

### 2. 圆弧推动
- 圆心 = 红色抓取位置（左臂固定点）
- 起点 = 蓝色推动位置
- 角度 = 90°（可配置）
- 方向 = clockwise/counterclockwise（可配置）

### 3. 右臂推动模式
- 夹爪保持张开
- 不闭合夹爪
- 通过接触推动，不是抓取

### 4. 固定Z坐标
- 抓取Z = -0.16m（配置）
- 推动Z = -0.16m（配置）
- 不使用VLM推断的Z

### 5. 验证检查
- 圆弧半径范围：0.08m ~ 0.40m
- 所有姿态工作空间检查
- 所有姿态IK可达性检查

## 使用方法

### 运行测试
```bash
cd /home/cothink/Baxter-claw
python examples/shape_ruler_demo.py
```

### Dry Run
```bash
python examples/shape_ruler_demo.py  # 默认dry_run=False
```

修改demo脚本设置`dry_run=True`可以只计算不执行。

## 预期输出

```
======================================================================
BIMANUAL SHAPE RULER - SIMPLIFIED ARC-PUSHING
======================================================================
Fixed arm: left (grasp red segment)
Moving arm: right (push blue segment, gripper OPEN)
Arc direction: clockwise
Config: config/ruler_task.yaml
Dry run: False
======================================================================

[Stage 1] Loading configuration...
  ✓ Configuration loaded

[Stage 2] VLM Localization (2 points only)...
  [2.1] Locating red grasp position...
       ✓ Red grasp (raw): [0.63, 0.12, -0.07]
  [2.2] Locating blue push position...
       ✓ Blue push (raw): [0.72, 0.18, -0.08]
  ✓ All localization complete

[Stage 3] Preparing motion coordinates...
  ✓ Red grasp: [0.63, 0.12, -0.16]
  ✓ Blue push: [0.72, 0.18, -0.16]
  Grasp Z: -0.16m, Push Z: -0.16m

[Stage 4] Generating arc waypoints...
  ✓ Arc generated
    Center: [0.63, 0.12]
    Start: [0.72, 0.18]
    Radius: 0.108m
    Angle: 90°
    Direction: clockwise
    Waypoints: 21

[Stage 5] Validating all poses...
  ✓ All poses validated

[Stage 7] Starting robot execution...
  ⚠ Robot will now move

[Stage 8] Moving left arm to red grasp approach...
  ✓ At approach position

[Stage 9] Opening left gripper...

[Stage 10] Moving down to grasp red segment...

[Stage 11] Closing left gripper to hold red segment...
  ✓ Red segment grasped and held

[Stage 12] Opening right gripper (for pushing)...
  ✓ right gripper open

[Stage 13] Moving right arm to push approach...

[Stage 14] Moving down to push start position...
  ✓ At push start position

[Stage 15] Executing arc pushing motion...
  Pushing along 21 waypoints at speed 0.2
  Waypoint 1/21
  Waypoint 6/21
  Waypoint 11/21
  Waypoint 16/21
  Waypoint 21/21
  ✓ Arc pushing complete

[Stage 16] Retreating right arm...

[Stage 17] Releasing left gripper...

======================================================================
✓ TASK COMPLETE
======================================================================
  Arc pushing executed successfully
  left arm held red segment
  right arm pushed blue segment along 90° arc
======================================================================
```

## 错误处理

可能的失败情况：

1. **配置加载失败**
   - `failed_stage: "load_config"`

2. **VLM定位失败**
   - `failed_stage: "localization_red_grasp"`
   - `failed_stage: "localization_blue_push"`

3. **圆弧生成失败**
   - `failed_stage: "arc_generation"`
   - 原因：方向参数错误

4. **圆弧验证失败**
   - `failed_stage: "arc_validation"`
   - 原因：半径过小或过大

5. **姿态验证失败**
   - `failed_stage: "pose_validation"`
   - 原因：工作空间外或IK不可达

6. **执行失败**
   - `failed_stage: "fixed_arm_approach/grasp"`
   - `failed_stage: "moving_arm_approach/push_start"`
   - `failed_stage: "arc_execution"`
   - 包含`failed_waypoint`索引

## 调试信息

返回结果包含：
- `red_grasp_position` - 红色抓取位置
- `blue_push_position` - 蓝色推动位置
- `arc_center` - 圆弧中心
- `arc_radius` - 圆弧半径
- `arc_angle_degrees` - 圆弧角度
- `arc_direction` - 圆弧方向
- `arc_waypoints` - 所有圆弧waypoints
- `num_waypoints` - waypoint数量

## 参数调整

### 如果推动方向反了
修改配置：
```yaml
arc_motion:
  direction: "counterclockwise"  # 改为逆时针
```

或在调用时传入：
```python
l_shape_blue_turn_direction="counterclockwise"
```

### 如果推动太快
修改配置：
```yaml
arc_motion:
  push_speed_scale: 0.1  # 降低速度
  num_waypoints: 30      # 增加waypoint数量
```

### 如果圆弧半径不合适
修改配置：
```yaml
arc_motion:
  min_radius: 0.05  # 调整最小半径
  max_radius: 0.50  # 调整最大半径
```

### 如果推动角度需要调整
修改配置：
```yaml
arc_motion:
  angle_degrees: 120  # 改为120度
```

## 优势

✅ **极简**：只定位2个点，无复杂几何  
✅ **稳定**：开环控制，不依赖关节定位  
✅ **可调**：所有参数可配置  
✅ **可调试**：清晰的阶段划分和日志  
✅ **实用**：优先保证能在真实机器人上运行  

## 局限性

⚠️ **开环控制**：无反馈，依赖初始定位准确性  
⚠️ **固定角度**：默认90°，不自适应  
⚠️ **无力控**：推动过程无力反馈  
⚠️ **平面运动**：只在XY平面，Z固定  

## 后续改进建议

如果基础版本运行稳定，可以考虑：

1. **添加力反馈**：检测推动阻力
2. **添加视觉伺服**：推动过程中实时调整
3. **自适应角度**：根据初始构型计算目标角度
4. **多段圆弧**：支持更复杂的轨迹

但现在的目标是：**先让最简单的版本跑通！**

---

**实现日期**: 2026-05-17  
**版本**: v3.0 (Simplified Arc-Pushing)  
**状态**: 已实现，待测试  
**优先级**: 稳定性 > 精确性
