# Home 位姿更新为避让位姿

## 背景

在 VLM 定位流程中，左右臂会先调整到避让位姿以避免遮挡 D455 摄像头。这个避让位姿比原有的 home 位姿更合适，因为：

1. **不遮挡摄像头** - 手臂向后收起，不会进入 D455 视野
2. **安全可靠** - 经过实际测试验证
3. **适合作为默认位姿** - 既是 home 位置，也是视觉任务的准备位置

## 修改内容

### 文件
`bridge/primitives.py` - 第 43-62 行

### 修改前（旧 home 位姿）

```python
self.home_positions = {
    'right': {
        'right_s0': 0.076316,
        'right_s1': -0.981748,
        'right_e0': 1.140515,
        'right_e1': 1.890631,
        'right_w0': -0.641204,
        'right_w1': 1.038888,
        'right_w2': 0.479752,
    },
    'left': {
        'left_s0': -0.079384,
        'left_s1': -0.998621,
        'left_e0': -1.188068,
        'left_e1': 1.937801,
        'left_w0': 0.671884,
        'left_w1': 1.028918,
        'left_w2': -0.501612,
    }
}
```

### 修改后（避让位姿）

```python
self.home_positions = {
    'right': {
        'right_s0': -0.5,
        'right_s1': -0.5,
        'right_e0': 0.0,
        'right_e1': 1.5,
        'right_w0': 0.0,
        'right_w1': 1.0,
        'right_w2': 0.0,
    },
    'left': {
        'left_s0': 0.5,
        'left_s1': -0.5,
        'left_e0': 0.0,
        'left_e1': 1.5,
        'left_w0': 0.0,
        'left_w1': 1.0,
        'left_w2': 0.0,
    }
}
```

## 位姿对比

### 右臂

| 关节 | 旧 home | 新 home (避让) | 变化 |
|------|---------|----------------|------|
| s0 | 0.076 | -0.5 | 向左收起 |
| s1 | -0.982 | -0.5 | 向上抬起 |
| e0 | 1.141 | 0.0 | 伸直 |
| e1 | 1.891 | 1.5 | 略微弯曲 |
| w0 | -0.641 | 0.0 | 中立 |
| w1 | 1.039 | 1.0 | 略微调整 |
| w2 | 0.480 | 0.0 | 中立 |

### 左臂

| 关节 | 旧 home | 新 home (避让) | 变化 |
|------|---------|----------------|------|
| s0 | -0.079 | 0.5 | 向右收起 |
| s1 | -0.999 | -0.5 | 向上抬起 |
| e0 | -1.188 | 0.0 | 伸直 |
| e1 | 1.938 | 1.5 | 略微弯曲 |
| w0 | 0.672 | 0.0 | 中立 |
| w1 | 1.029 | 1.0 | 略微调整 |
| w2 | -0.502 | 0.0 | 中立 |

## 位姿特点

### 新 home 位姿（避让位姿）

**右臂**：
- s0 = -0.5：肩部向左旋转，手臂向后收起
- s1 = -0.5：肩部向上抬起
- e0 = 0.0：肘部伸直
- e1 = 1.5：肘部略微弯曲
- w0, w1, w2：手腕保持中立或标准位置

**左臂**：
- s0 = 0.5：肩部向右旋转，手臂向后收起（镜像）
- s1 = -0.5：肩部向上抬起
- e0 = 0.0：肘部伸直
- e1 = 1.5：肘部略微弯曲
- w0, w1, w2：手腕保持中立或标准位置

**关键特征**：
- 手臂向后收起，远离 D455 摄像头视野
- 左右臂对称（s0 符号相反）
- 简洁的关节角度（多为 0.0, 0.5, 1.0, 1.5）

## 影响范围

### ✅ 所有使用 home 动作的地方

1. **手动调用 home**
   ```python
   primitives.home('right')
   primitives.home('left')
   primitives.home('both')
   ```

2. **OpenClaw 插件**
   - 用户说"回到初始位置"
   - 用户说"home"

3. **测试脚本**
   - 任何调用 home 的测试

### ✅ VLM 定位流程
- `multi_view_vlm.py` 中的 `_retract_arm()` 仍使用相同的避让位姿
- 现在 home 位姿和避让位姿一致

## 优势

### 1. 统一性
- home 位姿 = 避让位姿
- 减少位姿定义的重复
- 更容易维护

### 2. 摄像头友好
- 手臂不会遮挡 D455 视野
- 适合作为视觉任务的起始位置

### 3. 安全可靠
- 已在 VLM 定位流程中验证
- 关节角度合理，不会超限

### 4. 简洁
- 关节角度简单（0.0, ±0.5, 1.0, 1.5）
- 容易记忆和调试

## 使用示例

### Python API

```python
from bridge.primitives import BaxterPrimitives

# 初始化
primitives = BaxterPrimitives(driver, safety, vlm)

# 右臂回到 home（避让位姿）
primitives.home('right')

# 左臂回到 home（避让位姿）
primitives.home('left')

# 双臂回到 home（避让位姿）
primitives.home('both')
```

### OpenClaw 自然语言

```
用户: "回到初始位置"
机器人: [执行 home('both')]
        → 双臂移动到避让位姿

用户: "右手回家"
机器人: [执行 home('right')]
        → 右臂移动到避让位姿
```

### 测试脚本

```bash
# 测试 home 动作
python -c "
from bridge.drivers.baxter_driver import BaxterDriver
from bridge.primitives import BaxterPrimitives
from bridge.safety import SafetyValidator

driver = BaxterDriver()
driver.connect()
safety = SafetyValidator(config_path='config/baxter.yaml')
primitives = BaxterPrimitives(driver, safety, None)

# 回到 home（避让位姿）
primitives.home('both')
"
```

## 验证方法

### 1. 视觉检查
执行 home 动作后，观察：
- 手臂是否向后收起
- 是否远离 D455 摄像头视野
- 左右臂是否对称

### 2. 定位测试
```bash
# home 后立即进行定位
python -c "
primitives.home('both')
# 然后运行定位
python debug_localization.py 蓝色小方块
"
```
检查 D455 视野中是否有手臂遮挡。

### 3. 关节角度检查
```python
# 读取当前关节角度
driver.get_joint_angles('right')
driver.get_joint_angles('left')
```
确认与定义的 home 位姿一致。

## 注意事项

### 1. 向后兼容性
- 旧的 home 位姿已被替换
- 如果有脚本依赖旧的 home 位姿，需要更新

### 2. 工作空间
- 新 home 位姿在工作空间内
- 已通过安全检查

### 3. 碰撞检查
- 手臂向后收起，不会与桌面或其他物体碰撞
- 左右臂不会相互碰撞

## 回滚方法

如果需要恢复旧的 home 位姿，修改 `bridge/primitives.py`：

```python
self.home_positions = {
    'right': {
        'right_s0': 0.076316,
        'right_s1': -0.981748,
        'right_e0': 1.140515,
        'right_e1': 1.890631,
        'right_w0': -0.641204,
        'right_w1': 1.038888,
        'right_w2': 0.479752,
    },
    'left': {
        'left_s0': -0.079384,
        'left_s1': -0.998621,
        'left_e0': -1.188068,
        'left_e1': 1.937801,
        'left_w0': 0.671884,
        'left_w1': 1.028918,
        'left_w2': -0.501612,
    }
}
```

## 总结

### 修改内容
- ✅ home 位姿更新为避让位姿
- ✅ 左右臂对称设计
- ✅ 摄像头友好

### 优势
- 统一 home 和避让位姿
- 不遮挡 D455 视野
- 简洁可靠

### 影响
- 所有 home 动作使用新位姿
- 与 VLM 定位流程一致
- 更适合作为默认位置

现在 home 位姿已经是摄像头友好的避让位姿了！
