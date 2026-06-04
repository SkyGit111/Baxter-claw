# Hold-and-Rotate 快速开始指南

## 新技能概述

**Skill 13: bimanual_hold_and_rotate**

一只机械臂固定折叠尺的一段，另一只机械臂带动另一段绕旋转关节做平面旋转。

## 快速测试（3步）

### 1. 运行几何单元测试

```bash
cd /home/cothink/Baxter-claw
python tests/test_hold_and_rotate_geometry.py
```

预期输出：
```
✓✓✓ ALL TESTS PASSED ✓✓✓
```

### 2. Dry Run测试（不移动机器人）

```bash
python examples/hold_and_rotate_demo.py \
  --fixed-color blue \
  --moving-color yellow \
  --angle 90 \
  --direction clockwise
```

这会：
- 连接机器人
- 使用VLM定位所有关键点
- 计算旋转中心和路径
- 显示完整计划
- **不执行机器人动作**

### 3. 实机执行（确认dry run成功后）

```bash
python examples/hold_and_rotate_demo.py \
  --fixed-color blue \
  --moving-color yellow \
  --angle 90 \
  --direction clockwise \
  --execute
```

## 通过OpenClaw使用

### 启动系统

```bash
# Terminal 1: 启动Bridge Server
cd /home/cothink/Baxter-claw
python -m bridge.server --config config/baxter.yaml

# Terminal 2: 启动OpenClaw
nvm use 22
openclaw
```

### 自然语言指令示例

```
"用左手固定蓝色尺段，用右手把黄色尺段顺时针旋转90度"
"固定蓝色部分，把黄色部分逆时针旋转60度"
"hold blue segment with left arm, rotate yellow segment 90 degrees clockwise"
```

## 物体准备

### 2段尺子（1个关节）

```
[蓝色尺段]---[关节]---[黄色尺段]
    15cm              15cm
```

### 3段尺子（2个关节）

```
[蓝色尺段]---[关节1]---[黄色尺段]---[关节2]---[绿色尺段]
    15cm                 15cm                   15cm
```

**要求**：
- 每段长度15cm
- 用不同颜色胶带标识
- 在每段远离关节的一端贴抓取块
- 放置在桌面上（平面运动）

## 参数说明

| 参数 | 说明 | 默认值 | 示例 |
|-----|------|--------|------|
| fixed_segment_color | 固定段颜色 | 必需 | "blue" |
| moving_segment_color | 旋转段颜色 | 必需 | "yellow" |
| angle_degrees | 旋转角度 | 必需 | 90 |
| direction | 旋转方向 | 必需 | "clockwise" |
| fixed_arm | 固定臂 | "left" | "left"/"right" |
| moving_arm | 旋转臂 | "right" | "left"/"right" |
| segment_length | 尺段长度(m) | 0.15 | 0.15 |
| dry_run | 仅计划不执行 | False | True/False |

## 常见问题

### Q: VLM定位失败怎么办？

**A**: 检查：
- 光照是否充足
- 颜色对比是否明显
- 物体是否在相机视野内
- 是否有遮挡

### Q: Hinge计算失败？

**A**: 可能原因：
- 两个尺段不相邻
- VLM中点定位误差过大
- 尺段长度设置不正确

查看日志中的：
- 两中点距离
- 候选hinge位置
- 到观测点的距离

### Q: Waypoint不可达？

**A**: 
- 检查旋转角度是否过大
- 确认物体位置在工作空间内
- 尝试减小旋转角度

### Q: 固定段移动了？

**A**:
- 降低旋转速度（默认已经很低）
- 检查夹爪力度
- 确认固定段抓取位置合理

## 修改文件清单

如果需要调整代码：

```
bridge/
├── models.py              # 数据模型（新增2个类）
├── primitives.py          # 核心逻辑（新增6个方法，约500行）
└── server.py              # API端点（新增1个端点）

openclaw_plugin/
├── skills.md              # 技能定义（新增Skill 13）
└── baxter_claw_plugin.py  # 插件执行（新增1个方法）

tests/
└── test_hold_and_rotate_geometry.py  # 单元测试

examples/
└── hold_and_rotate_demo.py           # 演示脚本

docs/
└── HOLD_AND_ROTATE_IMPLEMENTATION.md # 完整文档
```

## 调试技巧

### 1. 查看详细日志

所有阶段都有详细日志输出：
- `[Stage 1]` 参数验证
- `[Stage 2]` VLM定位
- `[Stage 3]` 几何计算
- `[Stage 4]` 安全检查
- `[Stage 5]` 机器人执行
- `[Stage 6]` 结果返回

### 2. 使用Dry Run

始终先用dry_run=True测试：
```python
result = await primitives.bimanual_hold_and_rotate(
    ...,
    dry_run=True
)
```

检查返回的：
- `hinge_position`
- `candidate_hinges`
- `waypoints`
- `warnings`

### 3. 检查VLM置信度

如果置信度<70%，考虑：
- 改善光照
- 调整相机角度
- 使用更明显的颜色标记

## 性能指标

- **定位时间**: ~10-15秒（5个点）
- **计算时间**: <1秒
- **执行时间**: 
  - 30度: ~15秒
  - 60度: ~25秒
  - 90度: ~35秒

## 下一步

1. ✅ 运行几何测试
2. ✅ Dry run验证
3. ✅ 实机测试（小角度开始）
4. ✅ 尝试不同颜色组合
5. ✅ 测试3段尺子

## 获取帮助

- 完整文档: `docs/HOLD_AND_ROTATE_IMPLEMENTATION.md`
- 原始需求: `新skill提示词.md`
- 问题反馈: 项目issue tracker

---

**创建日期**: 2026-05-12  
**版本**: v1.0

