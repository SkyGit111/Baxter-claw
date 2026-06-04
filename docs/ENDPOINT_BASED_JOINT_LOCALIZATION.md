# Endpoint-Based Joint Localization Implementation

## 概述

实现了新的关节定位方案：通过VLM定位6个尺段端部中点，然后计算中心线交点来获得关节位置，替代了直接定位小圆点的不稳定方法。

## 核心改进

### 旧方案的问题
- 直接让VLM定位绿色/橙色小圆点
- 关节太小，VLM经常返回 `found: false`
- 定位不稳定，成功率低

### 新方案的优势
- VLM只定位6个更容易识别的尺段端部中点
- 通过几何计算获得关节位置（中心线交点）
- 所有关键点（grasp, push, joints）都从6个端点计算得到
- 更稳定，更鲁棒

## 修改文件清单

### 1. 配置文件
**文件**: `config/ruler_task.yaml`

**修改内容**:
- 移除了直接定位关节的prompt
- 移除了单独定位grasp/push点的prompt
- 添加了6个端部中点的prompt：
  - `red.endpoint_near_prompt`
  - `red.endpoint_far_prompt`
  - `yellow.endpoint_near_red_prompt`
  - `yellow.endpoint_near_blue_prompt`
  - `blue.endpoint_near_prompt`
  - `blue.endpoint_far_prompt`
- 添加了关节计算参数：
  - `joints.calculation_method: "centerline_intersection"`
  - `joints.min_segment_length: 0.05`
  - `joints.max_intersection_distance: 0.10`
  - `joints.parallel_threshold: 0.087`

### 2. 核心算法
**文件**: `bridge/primitives.py`

**新增函数**:

1. **`line_intersection_2d(p1, p2, q1, q2, eps=1e-6)`**
   - 计算两条无限直线的交点
   - 使用标准的2D直线交点公式
   - 检测平行线（denom < eps）
   - 返回交点 `[x, y]` 或 `None`

2. **`midpoint_2d(p1, p2)`**
   - 计算两点的中点
   - 用于计算尺段中心（grasp/push位置）

3. **`locate_ruler_endpoints_and_calculate_joints(segments_config, joints_config, motion_z)`**
   - 主要的端点定位和计算方法
   - 步骤：
     1. 定位6个端部中点（调用VLM 6次）
     2. 转换到motion坐标系（固定Z）
     3. 验证尺段长度
     4. 计算中心线交点（green_joint, orange_joint）
     5. 验证交点距离
     6. 计算grasp/push位置（尺段中点）
   - 返回所有计算结果和debug信息

**修改的方法**:

4. **`bimanual_shape_ruler()`**
   - Stage 2 & 3 合并，调用新的端点定位方法
   - 不再单独定位4个点（R, G, O, B）
   - 改为定位6个端点，计算得到所有位置
   - 更新返回结果，包含端点信息和验证距离

## 技术细节

### 端部中点定义
每个尺段有两个端部中点：
- **端部中点** = 尺段短边的几何中点
- **不是**矩形角点
- **不是**长边上的点
- **是**中心线与端部短边的交点

### Prompt设计
```
"midpoint of the short end edge of the [color] segment that [connects to/is far from] the [other color] segment"
```

关键词：
- `midpoint` - 中点
- `short end edge` - 短边
- 避免VLM定位到角点或边缘

### 中心线计算
```python
# 红色尺段中心线
red_centerline = Line(red_endpoint_near, red_endpoint_far)

# 黄色尺段中心线  
yellow_centerline = Line(yellow_endpoint_near_red, yellow_endpoint_near_blue)

# 蓝色尺段中心线
blue_centerline = Line(blue_endpoint_near, blue_endpoint_far)
```

### 关节位置计算
```python
# 绿色关节 = 红色中心线 ∩ 黄色中心线
green_joint_xy = line_intersection_2d(
    red_endpoint_near, red_endpoint_far,
    yellow_endpoint_near_red, yellow_endpoint_near_blue
)

# 橙色关节 = 蓝色中心线 ∩ 黄色中心线
orange_joint_xy = line_intersection_2d(
    blue_endpoint_near, blue_endpoint_far,
    yellow_endpoint_near_red, yellow_endpoint_near_blue
)
```

### 2D直线交点公式
```python
# 给定两条直线：
# Line 1: 通过 p1=(x1,y1) 和 p2=(x2,y2)
# Line 2: 通过 q1=(x3,y3) 和 q2=(x4,y4)

denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)

if abs(denom) < eps:
    return None  # 平行线

px = ((x1*y2-y1*x2)*(x3-x4) - (x1-x2)*(x3*y4-y3*x4)) / denom
py = ((x1*y2-y1*x2)*(y3-y4) - (y1-y2)*(x3*y4-y3*x4)) / denom

return [px, py]
```

### 验证检查

1. **尺段长度检查**
   ```python
   if segment_length < min_segment_length:
       return error  # 端点定位失败
   ```

2. **平行线检查**
   ```python
   if intersection is None:
       return error  # 中心线平行
   ```

3. **交点距离检查**
   ```python
   if dist_to_nearby_endpoints > max_intersection_distance:
       return error  # 交点太远
   ```

## 数据流

```
[VLM定位6个端点]
    ↓
red_near, red_far
yellow_near_red, yellow_near_blue
blue_near, blue_far
    ↓
[转换到motion坐标系]
    ↓
[验证尺段长度]
    ↓
[计算中心线交点]
    ↓
green_joint = red_centerline ∩ yellow_centerline
orange_joint = blue_centerline ∩ yellow_centerline
    ↓
[验证交点距离]
    ↓
[计算grasp/push位置]
    ↓
red_grasp = midpoint(red_near, red_far)
blue_push = midpoint(blue_near, blue_far)
    ↓
[后续动作执行]
```

## 使用方法

### 运行测试
```bash
cd /home/cothink/Baxter-claw
python examples/shape_ruler_demo.py
```

### 预期输出
```
[Endpoint Localization] Locating 6 segment endpoints...

  [1/6] Locating red segment endpoint (near yellow)...
       ✓ Red near: [0.63, 0.12, -0.07]

  [2/6] Locating red segment endpoint (far from yellow)...
       ✓ Red far: [0.68, 0.15, -0.08]

  ... (4 more endpoints)

  ✓ All 6 endpoints located

[Coordinate Conversion] Converting to motion coordinates (Z=-0.16)...

[Validation] Checking segment lengths...
  Red segment length: 0.152m
  Yellow segment length: 0.148m
  Blue segment length: 0.151m
  ✓ All segments valid

[Centerline Intersection] Calculating joint positions...
  ✓ Green joint: [0.65, 0.13, -0.16]
  ✓ Orange joint: [0.72, 0.18, -0.16]

[Intersection Validation] Checking joint positions...
  Green joint to red_near: 0.025m
  Green joint to yellow_near_red: 0.018m
  Orange joint to blue_near: 0.022m
  Orange joint to yellow_near_blue: 0.020m
  ✓ Joint positions valid

[Position Calculation] Calculating grasp/push positions...
  ✓ Red grasp: [0.655, 0.135, -0.16]
  ✓ Blue push: [0.725, 0.185, -0.16]

  ✓ All positions calculated from endpoints
```

## Debug信息

返回结果中包含：
- `endpoints_raw`: 6个端点的原始坐标
- `endpoints_motion`: 6个端点的motion坐标
- `segment_lengths`: 三个尺段的长度
- `green_joint_distances`: 绿色关节到相邻端点的距离
- `orange_joint_distances`: 橙色关节到相邻端点的距离

## 错误处理

可能的失败情况：
1. **端点定位失败**: VLM未找到某个端点
   - 返回: `failed_point: "red_endpoint_near"`
2. **尺段太短**: 两个端点距离过小
   - 返回: `failed_check: "red_segment_length"`
3. **中心线平行**: 无法计算交点
   - 返回: `failed_check: "green_joint_parallel"`
4. **交点太远**: 计算的关节位置不合理
   - 返回: `failed_check: "green_joint_distance"`

## 优势总结

1. **更稳定**: 端部中点比小圆点更容易识别
2. **更鲁棒**: 即使关节标记不清晰也能工作
3. **更准确**: 几何计算比VLM直接定位更精确
4. **可验证**: 多重检查确保结果合理
5. **可调试**: 详细的中间结果便于问题诊断

## 后续改进建议

1. 如果端点定位仍然不稳定，可以：
   - 进一步简化prompt
   - 使用更明显的端点标记
   - 添加多次定位取平均

2. 可以添加更多验证：
   - 检查三个尺段是否近似共线
   - 检查关节角度是否合理
   - 使用历史数据进行异常检测

3. 性能优化：
   - 可以并行定位6个端点
   - 缓存VLM结果避免重复调用

---

**实现日期**: 2026-05-17  
**版本**: v2.0 (Endpoint-based)  
**状态**: 已实现，待测试
