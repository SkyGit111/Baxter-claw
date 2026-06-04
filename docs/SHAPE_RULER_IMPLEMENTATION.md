# Bimanual Shape Ruler Implementation Summary

## 实现完成

成功实现了新的技能 **Skill 14: bimanual_shape_ruler**，用于将铰接折叠尺从S型调整为L型。

## 核心特性

### 1. 推动模式（Push Mode）
- ✅ 左臂抓住红色尺段并保持固定
- ✅ 右臂**不闭合夹爪**，通过推动方式移动蓝色尺段
- ✅ 避免了刚性抓取带来的力控问题

### 2. 固定运动Z坐标
- ✅ 所有运动高度固定为 `motion_z = -0.16m`
- ✅ Approach高度为 `motion_z + 0.08 = -0.08m`
- ✅ VLM定位结果的XY用于计算，Z统一覆盖

### 3. VLM直接定位关节
- ✅ 不再使用"中点反推关节"的旧逻辑
- ✅ 绿色关节和橙色关节直接通过VLM+D455定位
- ✅ 定位4个点：R（红色抓取）、G（绿色关节）、O（橙色关节）、B（蓝色推动）

### 4. 二连杆角度插值
- ✅ 不使用单圆弧路径
- ✅ 使用theta1和theta2同时插值生成waypoints
- ✅ 支持角度插值方向控制（auto/clockwise/counterclockwise）

### 5. 物理关节角度验证
- ✅ 分别检查绿色关节（G→R与G→O夹角）
- ✅ 分别检查橙色关节（O→G与O→B夹角）
- ✅ 关节角度违规直接失败（可配置）

### 6. 完整的姿态验证
- ✅ 验证所有执行位姿（position + orientation）
- ✅ 包括approach、contact、所有waypoints、retreat
- ✅ Safety检查 + IK可达性检查

### 7. 配置文件驱动
- ✅ 所有颜色、prompt、参数从YAML配置读取
- ✅ 不硬编码任何颜色或尺寸
- ✅ 支持灵活调整目标角度

## 修改文件清单

### 新增文件
1. **config/ruler_task.yaml** - 任务配置文件
2. **tests/test_shape_ruler_geometry.py** - 几何单元测试
3. **examples/shape_ruler_demo.py** - 演示脚本

### 修改文件
1. **bridge/models.py**
   - 新增 `BimanualShapeRulerRequest`
   - 新增 `ShapeRulerResponse`

2. **bridge/primitives.py**
   - 新增 `distance_xy()`
   - 新增 `normalize_xy()`
   - 新增 `rotate_vector_2d()`
   - 新增 `interpolate_angle()`
   - 新增 `convert_to_motion_coordinates()`
   - 新增 `calculate_two_link_target_L_shape()`
   - 新增 `plan_two_link_waypoints()`
   - 新增 `validate_all_execution_poses()`
   - 新增 `bimanual_shape_ruler()` - 主方法（约200行）

3. **bridge/server.py**
   - 更新imports
   - 新增 `POST /dualarm/shape_ruler` API端点

4. **openclaw_plugin/skills.md**
   - 新增 Skill 14: bimanual_shape_ruler 定义

5. **openclaw_plugin/baxter_claw_plugin.py**
   - 更新skill分发逻辑
   - 新增 `_execute_bimanual_shape_ruler()`

## 使用方法

### 1. 运行几何单元测试

```bash
cd /home/cothink/Baxter-claw
python tests/test_shape_ruler_geometry.py
```

预期输出：
```
✓✓✓ ALL TESTS PASSED ✓✓✓
```

### 2. Dry Run测试（推荐先测试）

```bash
python examples/shape_ruler_demo.py
```

或指定参数：
```bash
python examples/shape_ruler_demo.py \
  --fixed-arm left \
  --moving-arm right \
  --target-shape L \
  --blue-turn clockwise
```

### 3. 实机执行

```bash
python examples/shape_ruler_demo.py --execute
```

### 4. 通过OpenClaw自然语言

```
用户输入：
"把尺子从S型调整成L型"
"调整尺子构型"

LLM识别为：
{
  "skill": "bimanual_shape_ruler",
  "fixed_arm": "left",
  "moving_arm": "right",
  "target_shape": "L",
  "l_shape_blue_turn_direction": "clockwise"
}
```

### 5. 直接API调用

```python
import httpx

response = httpx.post(
    "http://localhost:8420/dualarm/shape_ruler",
    json={
        "fixed_arm": "left",
        "moving_arm": "right",
        "target_shape": "L",
        "l_shape_blue_turn_direction": "clockwise",
        "config_path": "config/ruler_task.yaml",
        "dry_run": True  # 先测试
    },
    timeout=300.0
)
result = response.json()
```

## 配置说明

### 道具结构（config/ruler_task.yaml）

```
红色尺段 --[绿色关节G]-- 黄色尺段 --[橙色关节O]-- 蓝色尺段
   ↑                                              ↑
  固定(R)                                      推动(B)
```

### 关键配置项

```yaml
motion:
  motion_z: -0.16              # 固定运动高度
  approach_offset_z: 0.08      # Approach偏移

push:
  moving_gripper_close: false  # 右臂不闭合夹爪
  skip_first_waypoint: true    # 跳过第0个waypoint

planning:
  waypoint_count: 10
  fail_on_joint_limit_violation: true
  green_joint_min_angle_deg: 10
  green_joint_max_angle_deg: 170

target:
  red_yellow_target_angle_deg: 165  # 绿色关节目标角度
  blue_yellow_target_angle_deg: 90  # 橙色关节目标角度
```

## 技术亮点

### 1. 几何模型
- 二连杆链条：G-O-B
- G固定（近似），O和B随动
- 使用实际测量的L1和L2，不强制0.15m

### 2. 目标计算
```python
# 红色段延伸方向
u_red_extension = normalize(G - R)

# 黄色段目标方向（考虑弯曲角度）
bend_angle = 180° - red_yellow_target_angle_deg
u_yellow_target = rotate(u_red_extension, ±bend_angle)

# 蓝色段目标方向（垂直于黄色段）
u_blue_target = rotate(u_yellow_target, ±90°)

# 目标位置
O_target = G + L1 * u_yellow_target
B_target = O_target + L2 * u_blue_target
```

### 3. 路径规划
```python
# 角度插值
for k in range(N):
    theta1_k = interpolate_angle(theta1_current, theta1_target, ratio_k)
    theta2_k = interpolate_angle(theta2_current, theta2_target, ratio_k)
    
    # 正向运动学
    O_k = G + L1 * [cos(theta1_k), sin(theta1_k)]
    B_k = O_k + L2 * [cos(theta2_k), sin(theta2_k)]
```

### 4. 执行流程
```
1. 加载配置
2. VLM定位 R, G, O, B
3. 转换为motion坐标（固定Z）
4. 计算L型目标
5. 规划waypoints
6. 验证所有姿态
7. 左臂抓R并保持
8. 右臂推B沿waypoints
9. 释放
```

## 与旧版本的区别

| 特性 | 旧版 (hold_and_rotate) | 新版 (shape_ruler) |
|-----|----------------------|-------------------|
| 关节定位 | 中点反推 | VLM直接定位 |
| 运动模型 | 单关节圆弧 | 二连杆角度插值 |
| 右臂动作 | 闭合夹爪抓取 | **打开夹爪推动** |
| Z坐标 | VLM定位结果 | 固定motion_z=-0.16 |
| 坐标类型 | 单一坐标 | raw + motion双坐标 |
| 关节检查 | 无 | 绿色+橙色分别检查 |
| 目标定义 | 旋转角度 | L型构型 |
| 配置方式 | 硬编码颜色 | YAML配置文件 |

## 安全注意事项

1. **首次使用必须dry_run**
   - 验证VLM定位结果
   - 检查关节角度计算
   - 确认waypoints合理

2. **物体准备**
   - 红色、黄色、蓝色尺段用彩色胶带标识
   - 绿色、橙色关节用彩色胶带标识
   - 每段长度约15cm

3. **运动安全**
   - 默认速度10%
   - 所有waypoints预先验证
   - 关节角度限制检查

4. **推动模式**
   - 右臂不闭合夹爪
   - 通过接触推动，不是拖拽
   - 左臂固定作用更关键

## 已知限制

1. **平面运动**
   - 仅支持XY平面调整
   - Z坐标固定不变

2. **目标形状**
   - 当前仅支持L型
   - 可扩展支持其他形状

3. **VLM依赖**
   - 需要良好光照条件
   - 颜色对比要明显

4. **固定段约束**
   - G固定是近似假设
   - 依赖左臂夹爪摩擦力

## 代码统计

- **新增代码**: 约1200行
- **新增文件**: 3个
- **修改文件**: 5个
- **新增API**: 1个端点
- **新增技能**: 1个（Skill 14）

## 测试状态

✅ 几何单元测试已创建  
✅ Dry run演示脚本已创建  
⏳ 实机测试待进行  

---

**实现日期**: 2026-05-17  
**版本**: v1.0  
**状态**: 已实现，待实机测试
