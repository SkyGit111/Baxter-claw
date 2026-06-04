# Skill 12: Sequential Handover - 实现文档

## 概述

新增了第12个技能：`sequential_handover`（顺序接力），实现左右臂依次协作完成物体传递任务。

## 功能描述

**场景**：
- 物体A放在桌子左侧
- 物体B放在桌子右侧
- 机器人需要将物体A从左侧传递到物体B上

**执行流程**：
1. 左臂抓取物体A（从左侧）
2. 左臂将物体A放置到中间位置（Y=0）
3. 左臂回到home姿态
4. 右臂抓取物体A（从中间位置）
5. 右臂将物体A放置到物体B上

## 技能定义

**文件**：`openclaw_plugin/skills.md`

**参数**：
- `object_a` (string, required): 要传递的物体（例如："蓝色小方块"）
- `object_b` (string, required): 最终目标物体（例如："红色小方块"）
- `relative_position` (string, optional): 放置位置，默认"on_top"
  - "on_top": 放在物体B上方
  - "next_to": 放在物体B旁边
  - "behind": 放在物体B后面
  - "in_front": 放在物体B前面

**触发关键词**：
- "依次"、"先...再..."、"传递"、"接力"
- "sequentially"、"then"、"handover"、"relay"

**示例指令**：
- "先用左手抓取蓝色小方块放到中间，再用右手抓取它放到红色小方块上"
- "left arm picks blue cube to center, then right arm picks it and places on red cube"

## 实现细节

**文件**：`openclaw_plugin/baxter_claw_plugin.py`

**方法**：`_execute_sequential_handover(params: Dict) -> Dict`

**实现位置**：第645-845行

**关键代码**：

```python
def _execute_sequential_handover(self, params: Dict) -> Dict:
    # Phase 1: 左臂抓取物体A
    pick1_result = POST /vision/pick_by_name
        arm='left', object_name=object_a
    
    # Phase 2: 左臂放置到中间（Y=0）
    center_position = [pick_position[0], 0.0, pick_position[2]]
    place1_result = POST /primitives/place
        arm='left', position=center_position
    
    # Phase 3: 左臂回home
    home_result = POST /primitives/home
        arm='left'
    
    # Phase 4: 右臂抓取物体A
    pick2_result = POST /vision/pick_by_name
        arm='right', object_name=object_a
    
    # Phase 5: 右臂放置到物体B上
    place2_result = POST /vision/place_by_name
        arm='right', target_object_name=object_b,
        relative_position=relative_position
```

## 与现有技能的区别

| 特性 | sequential_handover | parallel_pick_and_place |
|-----|---------------------|------------------------|
| 执行方式 | 顺序执行 | 完全并行 |
| 中间位置 | 固定中间（Y=0） | 无中间位置 |
| 适用场景 | 单个物体传递 | 两个独立任务 |
| 执行时间 | 较长（~30秒） | 较短（~15秒） |
| 手臂协作 | 接力传递 | 独立并行 |

## 测试方法

**测试脚本**：`test_sequential_handover.py`

**测试步骤**：
1. 将蓝色小方块放在桌子左侧
2. 将红色小方块放在桌子右侧
3. 在OpenClaw中输入：
   ```
   "先用左手抓取蓝色小方块放到中间，再用右手抓取它放到红色小方块上"
   ```
4. 观察执行过程：
   - 左臂抓取蓝色小方块
   - 左臂放置到中间
   - 左臂回home
   - 右臂抓取蓝色小方块
   - 右臂放置到红色小方块上

## 安全性保证

1. **不影响现有功能**：
   - 新技能独立实现，不修改现有技能代码
   - 使用现有的底层原语（pick_by_name, place, place_by_name）
   - 所有现有技能保持不变

2. **错误处理**：
   - 每个阶段都有独立的错误检查
   - 失败时返回详细的phase信息
   - 不会因为一个阶段失败而影响系统稳定性

3. **参数验证**：
   - 检查必需参数（object_a, object_b）
   - 提供默认值（relative_position='on_top'）

## 修改文件清单

1. ✅ `openclaw_plugin/skills.md`
   - 添加Skill 12定义（第249-283行）

2. ✅ `openclaw_plugin/baxter_claw_plugin.py`
   - 在execute_skill中添加调用（第258-259行）
   - 实现_execute_sequential_handover方法（第645-845行）

3. ✅ `test_sequential_handover.py`
   - 创建测试脚本

## 验证清单

- [x] 技能定义已添加到skills.md
- [x] 执行方法已实现
- [x] execute_skill中已添加调用
- [x] 不影响现有11个技能
- [x] 使用现有底层原语
- [x] 错误处理完善
- [x] 测试脚本已创建

## 使用示例

**中文指令**：
```
"先用左手抓取蓝色小方块放到中间，再用右手抓取它放到红色小方块上"
```

**英文指令**：
```
"left arm picks blue cube to center, then right arm picks it and places on red cube"
```

**LLM识别结果**：
```json
{
  "skill": "sequential_handover",
  "params": {
    "object_a": "蓝色小方块",
    "object_b": "红色小方块",
    "relative_position": "on_top"
  }
}
```

## 注意事项

1. **中间位置计算**：
   - 使用pick时的X和Z坐标
   - Y坐标固定为0（桌子中间）
   - 确保中间位置在工作空间内

2. **执行顺序**：
   - 必须严格按照5个阶段顺序执行
   - 不能跳过任何阶段
   - 左臂必须先回home再让右臂抓取

3. **物体识别**：
   - 两次抓取都使用VLM定位
   - 第二次抓取时物体已在中间位置
   - 确保VLM能识别中间位置的物体

---

**创建日期**：2026-05-12  
**版本**：v1.0  
**状态**：已实现，待测试
