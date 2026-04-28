# Baxter-Claw 完整架构文档 - 第4节：OpenClaw 插件系统

## 4. OpenClaw 自然语言控制

### 4.1 OpenClaw 架构概述

OpenClaw 插件实现了从自然语言到机器人动作的完整转换流程，是用户与机器人交互的主要接口。

#### 4.1.1 架构演进

**旧架构：Intent-based (v0.3.0，已弃用)**
```
用户输入 → LLM 识别意图 → 动态工作流规划 → 逐步执行
```
问题：
- LLM 判断不可靠，容易误判任务完成
- 单步任务会错误地继续执行
- 参数传递容易出错

**新架构：Skills-based (v0.4.0，当前)**
```
用户输入 → LLM 选择技能 → LLM 提取参数 → 执行固定流程
```
优势：
- ✅ 技能逻辑固定，行为可预测
- ✅ 参数提取准确（强制区分 source/target）
- ✅ 单步任务不会多余执行
- ✅ 易于扩展新技能

### 4.2 Skills.md 技能系统

#### 4.2.1 技能定义格式

```markdown
## Skill N: skill_name
**Description**: 技能描述

**When to use**:
- 使用场景 1
- 使用场景 2

**Parameters**:
- `param1` (type, required/optional): 参数说明
- `param2` (type, required/optional): 参数说明

**Execution**:
1. 执行步骤 1
2. 执行步骤 2

**Success condition**: 成功条件
```

#### 4.2.2 当前可用技能

**单步技能**：
1. **pick_object** - 抓取物体
2. **place_object_direction** - 放置到方向
3. **place_object_relative** - 放置到物体旁边
4. **locate_object** - 定位物体
5. **describe_scene** - 描述场景
6. **go_home** - 回到原位
7. **open_gripper** - 打开夹爪
8. **close_gripper** - 关闭夹爪

**组合技能**：
9. **pick_and_place_direction** - 抓取并放置到方向
10. **pick_and_place_relative** - 抓取并放置到物体旁边

#### 4.2.3 技能示例

```markdown
## Skill 5: pick_and_place_relative
**Description**: Pick an object and place it relative to another object (combined skill)

**When to use**:
- User asks to move an object relative to another object
- Examples: "把蓝色方块放到黄色方块上", "place the red cup next to the white box"

**Parameters**:
- `source_object_name` (string, required): Name of the object to pick
- `target_object_name` (string, required): Name of the reference object
- `relative_position` (string, required): Where to place ("on_top", "next_to", "behind", "in_front")
- `arm` (string, optional): Which arm to use ("auto" recommended)

**Execution**:
1. Call `pick_by_name(source_object_name, arm)`
2. If pick fails, skill FAILS
3. Call `place_by_name(target_object_name, relative_position, arm)` (use same arm)
4. If successful, skill is DONE

**Success condition**: Source object is picked and placed relative to target object

**CRITICAL**: 
- source_object_name = 要抓取的物体
- target_object_name = 参考物体（放置位置）
- 不要混淆！
```

### 4.3 BaxterClawPlugin (openclaw_plugin/baxter_claw_plugin.py)

#### 4.3.1 核心流程

```python
class BaxterClawPlugin:
    def handle_message_with_skills(self, user_message: str) -> str:
        # Step 1: LLM 选择技能
        skill_selection = self.select_skill(user_message)
        # 返回：{'skill': 'pick_and_place_relative', 'params': {...}, 'confidence': 0.95}
        
        # Step 2: 执行技能
        result = self.execute_skill(skill_selection['skill'], skill_selection['params'])
        
        # Step 3: 返回结果
        return result['message']
```

#### 4.3.2 技能选择 (select_skill)

```python
def select_skill(self, user_message: str) -> Dict[str, Any]:
    # 1. 构建 prompt
    prompt = f"""你是机器人控制助手。用户给出命令，你需要从 skills.md 中选择合适的技能。

用户命令："{user_message}"

可用技能：
{self.skills}  # skills.md 的完整内容

你的任务：
1. 选择最合适的技能
2. 提取所有必需参数
3. 特别注意区分 source_object_name 和 target_object_name

返回 JSON：
{{
    "skill": "skill_name",
    "params": {{"param1": "value1", "param2": "value2"}},
    "confidence": 0.95,
    "reasoning": "选择理由"
}}"""
    
    # 2. 调用 LLM
    response = self._call_llm(prompt)
    
    # 3. 解析响应
    return self._parse_skill_selection(response)
```

#### 4.3.3 技能执行 (execute_skill)

```python
def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if skill_name == 'pick_object':
        return self._execute_pick_object(params)
    elif skill_name == 'pick_and_place_relative':
        return self._execute_pick_and_place_relative(params)
    # ... 其他技能

def _execute_pick_and_place_relative(self, params: Dict) -> Dict:
    source = params.get('source_object_name')
    target = params.get('target_object_name')
    position = params.get('relative_position', 'next_to')
    arm = params.get('arm', 'auto')
    
    # Step 1: Pick source
    pick_result = self._execute_pick_object({
        'object_name': source,
        'arm': arm
    })
    if not pick_result['success']:
        return pick_result
    
    # Step 2: Place relative to target
    arm_used = pick_result.get('arm_used', arm)
    place_result = self._execute_place_object_relative({
        'target_object_name': target,
        'relative_position': position,
        'arm': arm_used  # 使用同一只手臂
    })
    
    return place_result
```

#### 4.3.4 参数提取规则

LLM 必须遵守的参数提取规则：

```python
# 1. object_name / source_object_name
"抓住蓝色小方块" → object_name = "蓝色小方块"
"grab the red cup" → object_name = "red cup"

# 2. target_object_name
"放到黄色方块上" → target_object_name = "黄色方块"
"place it next to the white box" → target_object_name = "white box"

# 3. relative_position 映射
"上面", "上", "on top", "on" → "on_top"
"旁边", "next to", "beside" → "next_to"
"后面", "behind" → "behind"
"前面", "in front", "front" → "in_front"

# 4. direction 映射
"左边", "左", "left" → "left"
"右边", "右", "right" → "right"
"前面", "前", "front" → "front"
"后面", "后", "back" → "back"

# 5. arm 默认值
未指定 → "auto"
"用左手", "left arm" → "left"
"用右手", "right arm" → "right"
```

### 4.4 Web 界面 (openclaw_plugin/web_interface.py)

#### 4.4.1 界面功能

```python
@app.route('/')
def index():
    # 主界面：聊天框 + 相机视图
    return render_template_string(HTML_TEMPLATE)

@app.route('/send', methods=['POST'])
def send():
    user_message = request.json.get('message')
    
    # 调用插件处理
    response = plugin.handle_message_with_skills(user_message)
    
    return jsonify({'response': response})

@app.route('/camera_feed')
def camera_feed():
    # 实时相机流
    return Response(
        generate_camera_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
```

#### 4.4.2 界面布局

```
┌─────────────────────────────────────────────────────────┐
│  Baxter-Claw 控制界面                                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  D455 相机       │  │  右手腕相机       │            │
│  │  [实时视频]      │  │  [实时视频]       │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  聊天记录                                       │    │
│  │  用户: 抓住蓝色方块                             │    │
│  │  机器人: 成功抓取 蓝色方块                      │    │
│  │  用户: 放到黄色方块上                           │    │
│  │  机器人: 成功将 蓝色方块 放置到 黄色方块 on_top │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  输入: [                                    ] 发送│    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  快捷命令：                                              │
│  [回到原位] [打开夹爪] [关闭夹爪] [查看状态]            │
└─────────────────────────────────────────────────────────┘
```

### 4.5 使用示例

#### 4.5.1 单步任务

```
用户: "抓住蓝色小方块"

[LLM 选择]
skill: pick_object
params: {
    "object_name": "蓝色小方块",
    "arm": "auto"
}

[执行流程]
1. 定位 "蓝色小方块"
2. 自动选择手臂（基于 Y 坐标）
3. 执行 pick
4. （可选）验证抓取

[结果]
✓ 成功抓取 蓝色小方块
```

#### 4.5.2 组合任务

```
用户: "把蓝色方块放到魔方上"

[LLM 选择]
skill: pick_and_place_relative
params: {
    "source_object_name": "蓝色方块",
    "target_object_name": "魔方",
    "relative_position": "on_top",
    "arm": "auto"
}

[执行流程]
1. 定位并抓取 "蓝色方块"
2. 定位 "魔方"
3. 计算放置位置（魔方上方 3cm）
4. 执行 place
5. 打开夹爪

[结果]
✓ 成功将 蓝色方块 放置到 魔方 on_top
```

#### 4.5.3 错误处理

```
用户: "把红色杯子放到绿色盒子里"

[LLM 选择]
skill: pick_and_place_relative
params: {
    "source_object_name": "红色杯子",
    "target_object_name": "绿色盒子",
    "relative_position": "on_top",
    "arm": "auto"
}

[执行流程]
1. 尝试定位 "红色杯子"
2. ✗ 未找到红色杯子

[结果]
✗ 抓取失败: 未找到 红色杯子
```

### 4.6 多语言支持

OpenClaw 支持中英文混合输入：

```python
# 中文
"抓住蓝色小方块" → pick_object(object_name="蓝色小方块")

# 英文
"grab the blue cube" → pick_object(object_name="blue cube")

# 混合
"pick 蓝色方块" → pick_object(object_name="蓝色方块")
```

VLM 也支持多语言物体名称识别。

---

**下一节**：[第5节：安全系统](ARCHITECTURE_COMPLETE_05_SAFETY.md)
