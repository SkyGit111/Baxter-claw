# 架构改进总结

## 问题诊断

你观察到的问题非常准确：

1. **"识别魔方的坐标"任务失败** - OpenClaw 反复调用 `describe_scene` 直到超时
2. **数据传递失败** - `locate_object` 返回了坐标，但下一步 LLM 错误地调用 `pick_by_name` 而不是使用已有坐标
3. **缺少明确的技能定义** - LLM 不知道如何正确组合技能

## 根本原因

### 1. 任务类型混淆
- **问题**：查询任务（如"识别坐标"）被当作操作任务处理，进入了多次迭代的工作流
- **后果**：LLM 不知道查询完成后应该停止，反复调用查询技能

### 2. 数据传递断裂
- **问题**：工作流 prompt 只包含简短的历史摘要，没有包含结构化的输出数据
- **示例**：
  ```
  旧的 prompt:
  "1. locate_object: ✓ 成功
     信息: 找到魔方..."
  
  LLM 看不到具体的 position=[0.6, 0.15, 0.1]
  ```
- **后果**：LLM 无法使用前一步的输出作为下一步的输入

### 3. 技能定义不清晰
- **问题**：没有明确的技能定义文档，LLM 不知道：
  - 每个技能的输入/输出
  - 如何组合技能
  - 何时使用哪个技能
- **后果**：LLM 做出错误的技能选择

## 解决方案

### 1. 区分任务类型 ✅

**实现**：在意图识别时添加 `task_type` 字段

```python
# 查询任务
{
  "action": "locate_object",
  "task_type": "query",  # 新增
  "params": {"object_name": "魔方"}
}

# 操作任务
{
  "action": "pick_by_name",
  "task_type": "manipulation",  # 新增
  "params": {"object_name": "红杯子"}
}
```

**路由逻辑**：
```python
if task_type == 'query':
    # 直接执行，返回结果
    result = execute_action(action, params)
    return result['message']
else:
    # 进入工作流循环
    return execute_workflow(context)
```

**效果**：
- "识别魔方的坐标" → 执行一次 `locate_object` → 返回结果 ✅
- 不再进入工作流循环 ✅

### 2. 改进数据传递 ✅

**实现**：在工作流 prompt 中包含结构化输出数据

```python
# 旧的历史摘要
"1. locate_object: ✓ 成功
   信息: 找到魔方..."

# 新的历史摘要
"1. locate_object: ✓ 成功
   信息: 找到魔方，位置: [0.6, 0.15, 0.1], 置信度: 85%
   输出数据: {'position': [0.6, 0.15, 0.1], 'confidence': 85}
   → 可用于: pick(arm='auto', position=[0.6, 0.15, 0.1])"
```

**关键代码**：
```python
# 提取输出数据
output_data = {}
if 'position' in result:
    output_data['position'] = result['position']
if 'arm_used' in result:
    output_data['arm_used'] = result['arm_used']

# 添加到 prompt
history_text += f"   输出数据: {output_data}\n"

# 建议如何使用
if skill == 'locate_object' and 'position' in output_data:
    history_text += f"   → 可用于: pick(position={output_data['position']})\n"
```

**效果**：
- LLM 能看到前一步的具体输出数据 ✅
- LLM 知道如何使用这些数据 ✅

### 3. 添加 `pick` 技能 ✅

**问题**：只有 `pick_by_name`（定位+抓取），没有单独的 `pick`（使用已知坐标）

**解决**：添加 `pick` 技能

```python
def execute_action(action, params):
    if action == 'pick':
        # 使用已知坐标抓取
        position = params['position']  # 从 locate_object 获得
        arm = params.get('arm', 'auto')
        
        if arm == 'auto':
            arm = choose_arm_by_position(position)
        
        # 调用 Bridge API
        result = call_bridge_pick(arm, position)
        return result
```

**效果**：
- LLM 可以使用 `locate_object` 的输出调用 `pick` ✅
- 避免重复定位 ✅

### 4. 创建技能定义文档 ✅

**文件**：`SKILLS.md`

**内容**：
- 每个技能的详细定义
- 输入参数和输出数据
- 状态变化
- 下一步建议
- 使用示例
- 技能组合模式

**示例**：
```markdown
### locate_object
**Input**: {"object_name": "魔方"}
**Output**: {"position": [x, y, z], "confidence": 85}
**Next Skills**: pick(position=...) 或 describe_scene()

### pick
**Input**: {"arm": "auto", "position": [x, y, z]}
**Output**: {"success": true, "arm_used": "left"}
**State Change**: robot_state[arm].holding_object = true
**Next Skills**: place() 或 handover()
```

**效果**：
- 为 LLM 提供清晰的技能使用指南 ✅
- 明确技能组合模式 ✅

### 5. 改进完成条件检测 ✅

**实现**：在工作流 prompt 中明确完成条件

```python
prompt = """
Decision rules:
1. Check if user's goal is COMPLETED:
   - For "识别坐标" task: if locate_object succeeded, goal is DONE
   - For pick task: if object is picked and lifted, set action="done"
   - For place task: if object is placed, set action="done"
   ...

IMPORTANT: If the last action succeeded and completed the user's goal, 
set action="done"!
"""
```

**效果**：
- LLM 知道何时任务完成 ✅
- 避免无限循环 ✅

## 改进后的工作流

### 场景 1：纯查询任务
```
用户: "识别魔方的坐标"

1. 意图识别:
   action="locate_object"
   task_type="query"  ← 关键

2. 路由决策:
   task_type == "query" → 直接执行

3. 执行:
   locate_object(object_name="魔方")
   → 返回: position=[0.6, 0.15, 0.1]

4. 返回结果给用户:
   "找到魔方，位置: [0.6, 0.15, 0.1], 置信度: 85%"

✅ 不进入工作流循环
✅ 一次执行完成
```

### 场景 2：定位并抓取
```
用户: "识别魔方的坐标并抓取"

1. 意图识别:
   action="pick_by_name"
   task_type="manipulation"  ← 关键

2. 路由决策:
   task_type == "manipulation" → 进入工作流

3. 工作流执行:
   
   迭代 1:
   - LLM 决策: locate_object(object_name="魔方")
   - 执行结果: position=[0.6, 0.15, 0.1]
   - 历史记录: "输出数据: {'position': [0.6, 0.15, 0.1]}"
   
   迭代 2:
   - LLM 看到输出数据
   - LLM 决策: pick(arm="auto", position=[0.6, 0.15, 0.1])  ← 使用前一步数据
   - 执行结果: success=true, arm_used="left"
   
   迭代 3:
   - LLM 判断: 物体已抓取，目标完成
   - LLM 决策: action="done"

4. 返回结果:
   "成功用左臂抓取魔方"

✅ 正确使用前一步的数据
✅ 避免重复定位
✅ 正确判断完成
```

## 关键改进点总结

| 问题 | 原因 | 解决方案 | 状态 |
|------|------|----------|------|
| 查询任务进入工作流循环 | 没有区分任务类型 | 添加 task_type 字段，查询任务直接执行 | ✅ |
| LLM 看不到前一步的输出数据 | prompt 只有简短摘要 | 在 prompt 中包含结构化输出数据 | ✅ |
| LLM 不知道如何使用数据 | 缺少使用指导 | 添加 "可用于" 提示 | ✅ |
| 缺少使用已知坐标的 pick | 只有 pick_by_name | 添加 pick 技能 | ✅ |
| LLM 不知道何时完成 | 完成条件不明确 | 在 prompt 中明确完成条件 | ✅ |
| 技能定义不清晰 | 缺少文档 | 创建 SKILLS.md | ✅ |

## 测试建议

运行测试脚本：
```bash
python test_architecture_improvements.py <your_api_key>
```

手动测试关键场景：
1. "识别魔方的坐标" - 应该直接返回，不循环
2. "识别魔方的坐标并抓取" - 应该正确使用坐标
3. "拿红杯子放到左边" - 应该正确完成整个流程

观察终端输出：
- `[Task Type]` - 确认任务类型识别正确
- `[Mode]` - 确认路由决策正确
- `输出数据:` - 确认数据被正确提取
- `→ 可用于:` - 确认使用建议正确
- 迭代次数 - 确认不会无限循环

## 未来改进方向

1. **更智能的技能组合**
   - 让 LLM 学习常见的技能组合模式
   - 减少迭代次数

2. **更好的状态管理**
   - 使用状态机管理工作流
   - 更精确的完成条件判断

3. **技能库扩展**
   - 添加更多高级技能
   - 支持更复杂的任务

4. **错误恢复**
   - 更智能的错误处理
   - 自动尝试替代方案

## 总结

这次架构改进从根本上解决了你观察到的问题：

1. ✅ **任务路由** - 查询任务不再进入工作流循环
2. ✅ **数据传递** - LLM 能看到并使用前一步的输出
3. ✅ **技能定义** - 清晰的技能文档指导 LLM
4. ✅ **完成检测** - 明确的完成条件避免无限循环

核心思想：**让 LLM 看到完整的上下文和数据，并明确告诉它如何使用**。
