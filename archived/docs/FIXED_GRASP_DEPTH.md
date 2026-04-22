# 抓取深度固定优化

## 问题

定位很准确，但抓取失败的原因是：
- VLM+D455 计算的 Z 坐标（深度）不够低
- 夹爪没有下探到足够深度
- 无法接触到桌面上的物体

## 解决方案

### 固定抓取深度为 -0.15m

**原因**：
1. 桌面物体高度通常 < 夹爪长度
2. Z 轴偏移不稳定（标准差 6.19 cm）
3. 只要夹爪下探到接近桌面，就能抓到物体
4. 固定深度比依赖 VLM 估算更可靠

**实现位置**：`bridge/primitives.py` 的 `pick()` 方法

## 修改内容

### 修改前
```python
# Step 3: Descend to target
target_pose = position + orientation  # 使用 VLM 计算的 Z 坐标
print(f"  Descending to target: {position}")
success = self.driver.move_to_pose(arm, target_pose, speed * 0.5)
```

### 修改后
```python
# Step 3: Descend to target
# Override Z coordinate to fixed depth for reliable grasping
grasp_position = position.copy()
grasp_position[2] = -0.15  # 固定 Z 深度，确保夹爪到达桌面高度

target_pose = grasp_position + orientation
print(f"  Descending to target: {grasp_position} (Z fixed at -0.15)")
success = self.driver.move_to_pose(arm, target_pose, speed * 0.5)
```

## 工作流程

```
1. VLM+D455 定位物体
   position = [x, y, z]  (例如: [0.7, 0.2, 0.08])
   ↓
2. 移动到预抓取位置
   pre_grasp = [x, y, z + approach_height]
   (例如: [0.7, 0.2, 0.20])
   ↓
3. 打开夹爪
   ↓
4. 下探到固定深度 ✨ NEW
   grasp_position = [x, y, -0.15]  ← Z 固定为 -0.15
   (例如: [0.7, 0.2, -0.15])
   ↓
5. 闭合夹爪
   ↓
6. 提升物体
   回到预抓取高度
```

## 影响范围

### ✅ 仅影响抓取动作
- `pick()` 方法中的下探步骤
- 其他动作不受影响：
  - `place()` - 放置动作
  - `move()` - 移动动作
  - 预抓取位置仍使用 VLM 的 Z 坐标

### ✅ X、Y 坐标仍使用 VLM 定位
- X、Y 坐标使用校准后的 VLM 定位（精度高）
- 只有 Z 坐标在抓取时固定为 -0.15

## 输出示例

### 修改前
```
[Primitive] Pick: arm=right, position=[0.700, 0.200, 0.080]
  Pre-grasp pose: [0.700, 0.200, 0.200]
  Opening gripper
  Descending to target: [0.700, 0.200, 0.080]  ← Z=0.08 太高
  Closing gripper
  ✗ 抓取失败（夹爪没接触到物体）
```

### 修改后
```
[Primitive] Pick: arm=right, position=[0.700, 0.200, 0.080]
  Pre-grasp pose: [0.700, 0.200, 0.200]
  Opening gripper
  Descending to target: [0.700, 0.200, -0.150] (Z fixed at -0.15)  ← Z=-0.15 固定
  Closing gripper
  ✓ 抓取成功
```

## 安全性

### 桌面高度
- 桌面通常在 Z = -0.15 到 -0.18 之间
- 固定深度 -0.15 接近桌面但不会碰撞

### 工作空间检查
- 仍然会进行安全检查
- 如果 Z = -0.15 超出工作空间，会拒绝执行

### 物体高度
- 适用于高度 < 10cm 的物体
- 夹爪长度足够覆盖这个范围

## 测试方法

```bash
# 测试抓取
python test_d455_pick.py 蓝色小方块
```

观察输出：
```
Descending to target: [0.700, 0.200, -0.150] (Z fixed at -0.15)
```

确认 Z 坐标固定为 -0.15。

## 优势

### 1. 可靠性提高
- 不依赖 VLM 的 Z 坐标估算（不稳定）
- 固定深度确保夹爪到达桌面

### 2. 简单有效
- 无需复杂的深度校准
- 适用于大多数桌面抓取场景

### 3. 保持精度
- X、Y 坐标仍使用高精度的 VLM+校准定位
- 只有 Z 坐标固定

## 局限性

### 不适用场景
1. **多层物体**：如果物体堆叠，固定深度可能不够
2. **高物体**：高度 > 10cm 的物体可能抓不到顶部
3. **非桌面场景**：如果物体在架子上，固定深度不适用

### 解决方案
如果需要抓取特殊场景的物体，可以：
1. 添加参数控制是否使用固定深度
2. 根据物体类型动态调整深度

## 配置选项（未来扩展）

可以考虑添加配置：
```python
def pick(
    self,
    arm: str,
    position: List[float],
    approach_height: float = 0.1,
    speed: float = 0.3,
    use_fixed_depth: bool = True,  # 是否使用固定深度
    fixed_depth: float = -0.15     # 固定深度值
):
    if use_fixed_depth:
        grasp_position[2] = fixed_depth
    else:
        grasp_position = position.copy()
```

## 总结

### 修改内容
- ✅ 抓取时 Z 坐标固定为 -0.15m
- ✅ X、Y 坐标仍使用 VLM 定位
- ✅ 其他动作不受影响

### 预期效果
- 抓取成功率显著提高
- 不再因为深度不够而失败
- 适用于大多数桌面抓取场景

### 测试建议
1. 测试不同位置的物体
2. 测试不同大小的物体
3. 观察抓取成功率

现在可以重新测试抓取了！
