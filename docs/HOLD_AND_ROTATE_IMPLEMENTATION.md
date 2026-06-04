# Bimanual Hold-and-Rotate Implementation

## 概述

成功实现了一个新的上层技能 `bimanual_hold_and_rotate`，用于完成"一只机械臂固定折叠尺的一段，另一只机械臂带动另一段绕旋转关节做平面旋转"的双臂协同任务。

## 修改文件清单

### 1. 数据模型 (bridge/models.py)
**新增**：
- `BimanualHoldAndRotateRequest`: 请求模型，包含所有任务参数
- `HoldAndRotateResponse`: 响应模型，包含完整执行结果

### 2. 动作原语 (bridge/primitives.py)
**新增方法**：
- `rotate_point_around_center_xy()`: 2D平面点旋转
- `plan_arc_waypoints_xy()`: 圆弧路径规划
- `estimate_hinge_center_from_two_midpoints_and_observed_joint()`: 旋转中心计算
- `locate_named_point()`: VLM定位helper
- `follow_arc_waypoints()`: 圆弧轨迹跟随
- `bimanual_hold_and_rotate()`: 主执行方法（约300行）

### 3. API端点 (bridge/server.py)
**新增**：
- `POST /dualarm/hold_and_rotate`: REST API端点

### 4. 技能定义 (openclaw_plugin/skills.md)
**新增**：
- Skill 13: `bimanual_hold_and_rotate` 完整定义

### 5. 插件执行 (openclaw_plugin/baxter_claw_plugin.py)
**新增**：
- `_execute_bimanual_hold_and_rotate()`: 插件层执行方法

### 6. 测试脚本
**新增**：
- `tests/test_hold_and_rotate_geometry.py`: 几何单元测试
- `examples/hold_and_rotate_demo.py`: 演示脚本

## 技术实现详解

### 1. VLM定位逻辑

系统在机器人动作开始前完成所有视觉定位：

```python
# 定位5个关键点
1. fixed_grasp_position: 固定段抓取点
   描述: "{fixed_color} segment grasp block center away from {moving_color} segment"

2. moving_grasp_position: 旋转段抓取点
   描述: "{moving_color} segment grasp block center away from {fixed_color} segment"

3. fixed_segment_midpoint: 固定段中点
   描述: "{fixed_color} segment geometric midpoint"

4. moving_segment_midpoint: 旋转段中点
   描述: "{moving_color} segment geometric midpoint"

5. hinge_observed_position: 连接关节
   描述: "connection point between {fixed_color} segment and {moving_color} segment"
```

**关键特性**：
- 通过颜色明确指定参与任务的两个尺段
- 对于3段2关节物体，VLM根据颜色定位正确的连接关节
- 不依赖第三段或中间段进行几何消歧

### 2. 旋转中心几何计算

**理论基础**：
- 每段尺子长度 L = 0.15m
- 中点到关节距离 r = L/2 = 0.075m
- 两个相邻尺段共享一个旋转关节H
- H必须满足：distance(H, A) = r AND distance(H, B) = r

**计算流程**：
```python
1. 以midpoint_a为圆心，r为半径画圆
2. 以midpoint_b为圆心，r为半径画圆
3. 求两圆交点，得到两个候选hinge位置
4. 计算两个候选点到VLM观测hinge的距离
5. 选择距离更近的候选点作为最终hinge_position
```

**视觉噪声处理**：
- 如果两中点距离略大于2r（但在tolerance内），进行clamp处理
- 如果距离明显不合理，返回清晰错误
- 对最终hinge进行一致性验证

### 3. 通过VLM观测消除二义性

**问题**：两圆交点产生两个候选hinge位置

**解决方案**：
```python
# VLM额外定位两个指定颜色尺段之间的连接点
hinge_observed = VLM.locate("connection point between blue and yellow segments")

# 选择距离观测点更近的候选
if distance(candidate1, hinge_observed) < distance(candidate2, hinge_observed):
    selected_hinge = candidate1
else:
    selected_hinge = candidate2
```

**优势**：
- 不依赖第三段尺子
- 支持2段1关节物体
- 对于3段2关节物体，根据颜色定位正确关节

### 4. 目标点计算

```python
# 2D旋转公式
dx = moving_grasp_x - hinge_x
dy = moving_grasp_y - hinge_y

theta = radians(signed_angle)  # counterclockwise=+, clockwise=-

target_x = hinge_x + cos(theta) * dx - sin(theta) * dy
target_y = hinge_y + sin(theta) * dx + cos(theta) * dy
target_z = moving_grasp_z  # Z保持不变
```

### 5. 圆弧路径规划

```python
# 生成waypoints
num_steps = max(5, ceil(angle_degrees / waypoint_angle_step))
angle_step = angle_degrees / num_steps

for i in range(num_steps + 1):
    current_angle = i * angle_step
    waypoint = rotate_point(start, center, current_angle, direction)
    waypoints.append(waypoint)
```

**特性**：
- 至少5个waypoints
- 推荐每10度一个点
- 90度旋转生成约10个点
- 所有waypoints在执行前验证安全性和可达性

### 6. 执行流程

```
阶段1: 参数验证
  ├─ 检查fixed_arm != moving_arm
  └─ 检查fixed_color != moving_color

阶段2: 预定位（所有点在动作前定位）
  ├─ 定位fixed_grasp_position
  ├─ 定位moving_grasp_position
  ├─ 定位fixed_segment_midpoint
  ├─ 定位moving_segment_midpoint
  └─ 定位hinge_observed_position

阶段3: 几何计算
  ├─ 计算候选hinge位置
  ├─ 选择最终hinge_position
  ├─ 计算target_position
  └─ 生成waypoints

阶段4: 预检查
  ├─ 检查fixed_grasp工作空间
  ├─ 检查moving_grasp工作空间
  ├─ 检查所有waypoints工作空间
  └─ 如果dry_run=True，返回plan

阶段5: 机器人执行
  ├─ fixed_arm移动到pre-grasp
  ├─ fixed_arm下降并抓取
  ├─ moving_arm移动到pre-grasp
  ├─ moving_arm下降并抓取
  ├─ moving_arm沿waypoints旋转
  ├─ moving_arm释放
  └─ fixed_arm释放

阶段6: 返回结果
  └─ 包含所有定位、计算、执行信息
```

## 使用方法

### 1. Dry Run测试（推荐先测试）

```bash
cd /home/cothink/Baxter-claw
python examples/hold_and_rotate_demo.py \
  --fixed-color blue \
  --moving-color yellow \
  --angle 90 \
  --direction clockwise
```

输出包含：
- 所有VLM定位结果
- 候选hinge位置
- 选择的hinge及原因
- 完整waypoints列表
- 警告信息

### 2. 实机执行

```bash
python examples/hold_and_rotate_demo.py \
  --fixed-color blue \
  --moving-color yellow \
  --angle 90 \
  --direction clockwise \
  --execute
```

### 3. 通过OpenClaw自然语言

```
用户输入：
"用左手固定蓝色尺段，用右手把黄色尺段顺时针旋转90度"

LLM识别为：
{
  "skill": "bimanual_hold_and_rotate",
  "fixed_arm": "left",
  "moving_arm": "right",
  "fixed_segment_color": "blue",
  "moving_segment_color": "yellow",
  "angle_degrees": 90,
  "direction": "clockwise"
}
```

### 4. 直接API调用

```python
import httpx

response = httpx.post(
    "http://localhost:8420/dualarm/hold_and_rotate",
    json={
        "fixed_arm": "left",
        "moving_arm": "right",
        "fixed_segment_color": "blue",
        "moving_segment_color": "yellow",
        "angle_degrees": 90,
        "direction": "clockwise",
        "segment_length": 0.15,
        "dry_run": True  # 先测试
    },
    timeout=300.0
)
result = response.json()
```

## 几何单元测试

```bash
cd /home/cothink/Baxter-claw
python tests/test_hold_and_rotate_geometry.py
```

测试覆盖：
- ✓ 2D点旋转（逆时针、顺时针、180度、非原点中心）
- ✓ 圆弧waypoints生成（数量、半径、Z不变）
- ✓ Hinge中心估计（正常情况、距离过远）

## 安全注意事项

1. **首次使用必须dry_run**
   - 验证所有定位结果合理
   - 检查waypoints在工作空间内
   - 确认hinge位置正确

2. **速度设置**
   - 默认speed=0.10（10%）
   - 旋转过程保持低速避免拉偏尺子

3. **工作空间**
   - 所有waypoints自动验证
   - 超出工作空间会在执行前失败

4. **物体要求**
   - 两个尺段必须相邻（共享关节）
   - 每段长度15cm
   - 通过不同颜色胶带区分

5. **VLM定位**
   - 置信度<70%会产生警告
   - Hinge距离观测点>3cm会产生警告
   - 中点距离与理论值偏差>2cm会产生警告

## 当前实现的已知限制

1. **平面运动限制**
   - 仅支持XY平面旋转
   - Z坐标保持不变
   - 不支持3D空间旋转

2. **路径规划**
   - 使用简单圆弧waypoints
   - 未集成MoveIt/RRT
   - 适合桌面平面操作

3. **VLM依赖**
   - 需要VLM能识别颜色和几何特征
   - 光照条件影响定位精度
   - 小物体或遮挡可能失败

4. **固定段约束**
   - 固定臂保持静止但无主动力控制
   - 依赖夹爪摩擦力
   - 大角度旋转可能导致固定段移动

5. **尺段长度**
   - 默认15cm，可配置
   - 但VLM定位精度可能不适合很小的尺段

## 未来改进方向

1. **力控集成**
   - 固定臂主动施加保持力
   - 旋转臂力矩反馈

2. **视觉伺服**
   - 旋转过程中实时视觉反馈
   - 闭环修正轨迹

3. **多关节支持**
   - 同时操作多个关节
   - 复杂铰接物体

4. **自适应规划**
   - 根据物体刚度调整速度
   - 碰撞检测和恢复

5. **MoveIt集成**
   - 使用MoveIt进行路径规划
   - 碰撞避免

## 总结

✅ **已实现**：
- 完整的双臂协同旋转任务
- 基于颜色的尺段识别
- VLM观测消除关节二义性
- 几何计算和路径规划
- 完整的安全检查
- Dry run测试模式
- 详细的日志和错误处理

✅ **不影响现有功能**：
- 所有现有技能保持不变
- 使用现有底层原语
- 独立的API端点

✅ **测试完备**：
- 几何单元测试
- Dry run演示脚本
- 详细文档

---

**实现日期**：2026-05-12  
**版本**：v1.0  
**状态**：已实现，待实机测试

