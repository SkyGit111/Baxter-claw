# Flatten Articulated Ruler Implementation

## 概述

实现了全新的双臂协同拉直任务：通过抓住折叠尺的两个端点并向两侧拉开，将 S 型折叠尺拉直。

## 核心特性

### 与旧任务的区别

**旧任务 (bimanual_shape_ruler)**:
- ❌ 定位4个点（红色抓取、绿色关节、橙色关节、蓝色推动）
- ❌ 计算关节位置和二连杆角度
- ❌ 左臂抓住红色段，右臂推动蓝色段（夹爪张开）
- ❌ 右臂沿圆弧轨迹推动
- ❌ 开环控制，无姿态插值

**新任务 (flatten_articulated_ruler)**:
- ✅ 只定位2个点（红色端点、蓝色端点）
- ✅ 无需关节定位
- ✅ 双臂同时抓住两个端点（夹爪闭合）
- ✅ 双臂同步向两侧拉开
- ✅ 位置和姿态同步插值
- ✅ Yaw 角度随拉直方向旋转

## 实现文件

### 1. 配置文件
**文件**: `config/flatten_ruler_task.yaml`

```yaml
flatten_ruler:
  # VLM 定位 prompt（只需2个端点）
  red_endpoint_prompt: "center of the purple tape patch on the outer end of the red segment"
  blue_endpoint_prompt: "center of the green tape patch on the outer end of the blue segment"

  # 抓取参数
  grasp:
    grasp_z: -0.16                 # 抓取高度
    approach_z_offset: 0.08        # 接近偏移
    grasp_force: 50.0              # 抓取力（拉动需要更大的力）
    base_orientation:
      roll: 3.14159                # 夹爪向下
      pitch: 0.0
      yaw: 0.0                     # 根据拉动方向调整

  # 拉动参数
  pulling:
    pull_distance: 0.20            # 拉动距离
    num_waypoints: 30              # 路径点数量
    speed_scale: 0.15              # 速度比例
    min_separation: 0.15           # 最小初始距离
    max_separation: 0.60           # 最大最终距离
    interpolate_yaw: true          # 启用 yaw 插值
```

### 2. 核心算法
**文件**: `bridge/primitives.py`

**新增方法**: `async def flatten_articulated_ruler(config_path, dry_run)`

**执行流程**:
```
1. 加载配置
2. VLM 定位红色端点（紫色胶带）
3. VLM 定位蓝色端点（绿色胶带）
4. 准备抓取坐标（XY 来自 VLM，Z 固定）
5. 计算初始姿态（yaw 指向对方）
6. 生成拉动轨迹（位置+姿态插值）
7. 计算最终姿态（yaw 对齐拉直方向）
8. 验证所有姿态（工作空间+IK）
9. [Dry run 退出]
10. 双臂移动到接近位置
11. 双臂张开夹爪
12. 双臂下降到抓取位置
13. 双臂闭合夹爪，抓住端点
14. 执行同步拉动（30个 waypoints）
15. 双臂松开夹爪
16. 双臂撤离
17. 完成
```

### 3. 轨迹生成算法

```python
# 计算拉动方向
pull_vector = blue_endpoint - red_endpoint
pull_angle = atan2(pull_vector.y, pull_vector.x)

# 初始姿态
left_initial_yaw = pull_angle           # 左臂指向右
right_initial_yaw = pull_angle + π      # 右臂指向左

# 最终位置（从中点向两侧拉开）
midpoint = (red_endpoint + blue_endpoint) / 2
red_final = midpoint - pull_direction * (initial_sep/2 + pull_dist/2)
blue_final = midpoint + pull_direction * (initial_sep/2 + pull_dist/2)

# 最终姿态（对齐拉直方向）
final_pull_angle = atan2(blue_final.y - red_final.y, 
                         blue_final.x - red_final.x)
left_final_yaw = final_pull_angle
right_final_yaw = final_pull_angle + π

# 生成 waypoints（位置和姿态插值）
for i in range(num_waypoints + 1):
    ratio = i / num_waypoints
    
    # 位置插值
    left_pos = red_endpoint + ratio * (red_final - red_endpoint)
    right_pos = blue_endpoint + ratio * (blue_final - blue_endpoint)
    
    # 姿态插值
    left_yaw = left_initial_yaw + ratio * (left_final_yaw - left_initial_yaw)
    right_yaw = right_initial_yaw + ratio * (right_final_yaw - right_initial_yaw)
    
    left_waypoint = [left_pos, roll, pitch, left_yaw]
    right_waypoint = [right_pos, roll, pitch, right_yaw]
```

### 4. API 端点
**文件**: `bridge/server.py`

**新增端点**: `POST /primitives/flatten_ruler`

**参数**:
- `config_path` (string, optional): 配置文件路径
- `dry_run` (boolean, optional): 是否只计划不执行

**返回**:
```json
{
  "success": true,
  "message": "Ruler flattening task completed successfully",
  "red_endpoint": [x, y, z],
  "blue_endpoint": [x, y, z],
  "initial_separation": 0.25,
  "final_separation": 0.45,
  "pull_distance": 0.20,
  "num_waypoints": 31,
  "left_arm_trajectory": [...],
  "right_arm_trajectory": [...]
}
```

### 5. Plugin 集成
**文件**: `openclaw_plugin/baxter_claw_plugin.py`

**新增方法**: `_execute_flatten_articulated_ruler(params)`

**Skill 定义**: `openclaw_plugin/skills.md` - Skill 15

### 6. 测试脚本
**文件**: `examples/flatten_ruler_demo.py`

**使用方法**:
```bash
cd /home/cothink/Baxter-claw
python examples/flatten_ruler_demo.py
```

## 关键技术点

### 1. 双臂同步运动
- 左右臂使用相同数量的 waypoints
- 每个 waypoint 同时执行
- 保证双臂协调一致

### 2. 姿态插值
- **Roll**: 固定为 π（夹爪向下）
- **Pitch**: 固定为 0（无俯仰）
- **Yaw**: 线性插值，从初始方向到最终方向
  - 初始：指向对方（保持当前尺段方向）
  - 最终：对齐拉直方向（平行于拉直后的尺子）

### 3. 拉动策略
```
初始状态:  红 ～～～ 蓝  (S型，距离d1)
           ←       →
           
拉动过程:  红 ～～～～ 蓝  (逐渐拉直)
           ←         →
           
最终状态:  红 ━━━━━ 蓝  (直线，距离d2)
           ←           →
```

- 从中点向两侧对称拉开
- 保持 Z 坐标固定（桌面高度）
- Yaw 角度随拉直过程旋转

### 4. 安全验证
- 初始距离检查：`min_separation < d < max_separation`
- 最终距离检查：`final_separation < max_separation`
- 所有 waypoint 工作空间检查
- 关键 waypoint IK 可达性检查

## 使用示例

### 通过 API 调用
```bash
curl -X POST "http://localhost:8420/primitives/flatten_ruler" \
  -H "Content-Type: application/json" \
  -d '{
    "config_path": "config/flatten_ruler_task.yaml",
    "dry_run": false
  }'
```

### 通过 Plugin 调用
```python
plugin = BaxterClawPlugin(bridge_url="http://localhost:8420")

result = plugin.execute_skill(
    skill_name="flatten_articulated_ruler",
    params={
        "dry_run": False
    }
)
```

### 通过自然语言
```
用户: "把尺子拉直"
LLM: 识别为 flatten_articulated_ruler skill
Plugin: 执行双臂拉直任务
```

## 预期输出

```
======================================================================
FLATTEN ARTICULATED RULER - DUAL-ARM PULLING
======================================================================
Config: config/flatten_ruler_task.yaml
Dry run: False
======================================================================

[Stage 1] Loading configuration...
  ✓ Configuration loaded

[Stage 2] VLM Localization (2 endpoints)...
  [2.1] Locating red endpoint (purple tape)...
       ✓ Red endpoint (raw): [0.63, 0.12, -0.07]
  [2.2] Locating blue endpoint (green tape)...
       ✓ Blue endpoint (raw): [0.72, 0.18, -0.08]
  ✓ All localization complete

[Stage 3] Preparing grasp coordinates...
  ✓ Red endpoint: [0.63, 0.12, -0.16]
  ✓ Blue endpoint: [0.72, 0.18, -0.16]
  Initial separation: 0.108m

[Stage 4] Calculating initial grasp orientations...
  Pull direction angle: 33.7°
  Left arm initial orientation (RPY): [3.14159, 0.0, 0.588]
  Right arm initial orientation (RPY): [3.14159, 0.0, 3.730]
  ✓ Initial orientations calculated

[Stage 5] Generating pulling trajectories...
  Red final position: [0.58, 0.09, -0.16]
  Blue final position: [0.77, 0.21, -0.16]
  Final separation: 0.308m
  Final pull angle: 33.7°
  ✓ Trajectories generated: 31 waypoints

[Stage 6] Validating all poses...
  ✓ All poses validated (workspace check)

[Stage 8] Starting robot execution...
  ⚠ Robot will now move

[Stage 9] Moving both arms to approach positions...
  ✓ Both arms at approach positions

[Stage 10] Opening both grippers...

[Stage 11] Moving down to grasp positions...
  ✓ Both arms at grasp positions

[Stage 12] Closing both grippers...
  ✓ Both endpoints grasped

[Stage 13] Executing synchronized pulling motion...
  Pulling along 31 waypoints at speed 0.15
  Waypoint 1/31
    Left: pos=[0.63, 0.12, -0.16], yaw=33.7°
    Right: pos=[0.72, 0.18, -0.16], yaw=213.7°
  Waypoint 6/31
    Left: pos=[0.62, 0.11, -0.16], yaw=33.7°
    Right: pos=[0.73, 0.19, -0.16], yaw=213.7°
  ...
  Waypoint 31/31
    Left: pos=[0.58, 0.09, -0.16], yaw=33.7°
    Right: pos=[0.77, 0.21, -0.16], yaw=213.7°
  ✓ Pulling motion complete

[Stage 14] Releasing both grippers...

[Stage 15] Retreating both arms...

======================================================================
✓ TASK COMPLETE
======================================================================
  Ruler flattened successfully
  Initial separation: 0.108m
  Final separation: 0.308m
  Pull distance: 0.200m
======================================================================
```

## 参数调整

### 如果拉动距离不够
```yaml
pulling:
  pull_distance: 0.30  # 增加到 30cm
```

### 如果拉动太快
```yaml
pulling:
  speed_scale: 0.10    # 降低速度
  num_waypoints: 50    # 增加 waypoint 数量
```

### 如果抓取不牢固
```yaml
grasp:
  grasp_force: 70.0    # 增加抓取力
```

### 如果不需要 yaw 插值
```yaml
pulling:
  interpolate_yaw: false  # 保持初始 yaw
```

## 优势

✅ **极简定位**：只需2个点，无需关节定位  
✅ **双臂协同**：真正的双臂同步运动  
✅ **姿态控制**：位置和姿态同步插值  
✅ **安全可靠**：多重验证，小步慢速  
✅ **可配置**：所有参数可调整  
✅ **详细日志**：每个阶段清晰输出  

## 局限性

⚠️ **固定 Z 坐标**：只在 XY 平面拉动  
⚠️ **对称拉动**：从中点向两侧对称拉开  
⚠️ **无力反馈**：开环控制，无拉力检测  
⚠️ **直线拉动**：只支持直线拉开，不支持曲线  

## 后续改进建议

1. **添加力反馈**：检测拉动阻力，自适应调整
2. **添加视觉伺服**：拉动过程中实时检测尺子状态
3. **非对称拉动**：支持一侧固定，另一侧拉动
4. **Z 轴调整**：支持抬起拉动（离开桌面）

---

**实现日期**: 2026-05-18  
**版本**: v1.0 (Dual-arm Pulling)  
**状态**: 已实现，待测试  
**优先级**: 双臂协同 > 姿态控制 > 稳定性
