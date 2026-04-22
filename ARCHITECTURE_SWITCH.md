# OpenClaw 架构切换指南

本文档说明如何在两种 OpenClaw 架构之间切换。

---

## 两种架构对比

### 架构 1：Intent-based（旧架构，已弃用）

**特点**：
- LLM 识别意图 → 动态工作流 → 多步执行
- LLM 负责规划每一步
- 适合复杂多步任务

**问题**：
- LLM 判断不可靠，容易误判任务是否完成
- 单步任务（如"抓住黄色方块"）会错误地继续执行 place
- 参数传递容易出错

**代码位置**：
- `baxter_claw_plugin.py` 中标记为 `# OLD: Intent-based architecture`
- 方法：`parse_intent()`, `handle_message()`, `execute_workflow()`

---

### 架构 2：Skills-based（新架构，推荐）✅

**特点**：
- 基于 `skills.md` 定义的技能
- LLM 只负责：选择技能 + 提取参数
- 技能执行逻辑固定，不依赖 LLM 判断

**优势**：
- ✅ 参数准确：强制 LLM 同时提取 source 和 target 对象名
- ✅ 单步完成：技能定义明确，不会多余执行
- ✅ 可控性强：技能逻辑固定，行为可预测
- ✅ 易于扩展：添加新技能只需修改 `skills.md`

**代码位置**：
- `baxter_claw_plugin.py` 中标记为 `# NEW: Skills-based architecture`
- 方法：`select_skill()`, `execute_skill()`, `handle_message_with_skills()`
- 技能定义：`openclaw_plugin/skills.md`

---

## 如何切换架构

### 方法 1：修改 Web 界面（推荐）

编辑 `openclaw_plugin/web_interface.py`：

```python
# 使用新架构（当前默认）
response = plugin.handle_message_with_skills(user_message)

# 切换回旧架构
# response = plugin.handle_message(user_message)
```

### 方法 2：修改插件初始化

在 `baxter_claw_plugin.py` 中添加配置参数：

```python
class BaxterClawPlugin:
    def __init__(
        self,
        bridge_url: str = "http://localhost:8420",
        llm_provider: str = "qwen",
        llm_api_key: Optional[str] = None,
        use_d455: bool = True,
        use_skills_architecture: bool = True  # 新增参数
    ):
        self.use_skills_architecture = use_skills_architecture
        # ...

    def handle_message_auto(self, user_message: str) -> str:
        """自动选择架构"""
        if self.use_skills_architecture:
            return self.handle_message_with_skills(user_message)
        else:
            return self.handle_message(user_message)
```

然后在 `web_interface.py` 中：

```python
plugin = BaxterClawPlugin(
    bridge_url="http://localhost:8420",
    llm_provider="qwen",
    llm_api_key=qwen_api_key,
    use_skills_architecture=True  # True=新架构, False=旧架构
)

# 使用自动选择
response = plugin.handle_message_auto(user_message)
```

---

## 技能定义（Skills.md）

### 当前可用技能

1. **pick_object** - 抓取物体
2. **place_object_direction** - 放置到方向
3. **place_object_relative** - 放置到物体旁边
4. **pick_and_place_direction** - 抓取并放置到方向（组合）
5. **pick_and_place_relative** - 抓取并放置到物体旁边（组合）
6. **locate_object** - 定位物体
7. **describe_scene** - 描述场景
8. **go_home** - 回到原位
9. **open_gripper** - 打开夹爪
10. **close_gripper** - 关闭夹爪

### 添加新技能

编辑 `openclaw_plugin/skills.md`，按照以下格式添加：

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

然后在 `baxter_claw_plugin.py` 中添加对应的执行方法：

```python
def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    # ...
    elif skill_name == 'your_new_skill':
        return self._execute_your_new_skill(params)
    # ...

def _execute_your_new_skill(self, params: Dict) -> Dict:
    """Execute your_new_skill."""
    # 实现技能逻辑
    pass
```

---

## 测试

### 测试新架构

```bash
# 启动 Bridge Server
python start_server.py

# 启动 Web 界面
python openclaw_plugin/web_interface.py

# 在浏览器打开 http://localhost:5000
```

测试指令：
- "抓住蓝色小方块" → 应该只执行 pick，不会继续 place
- "把蓝色方块放到黄色方块上" → 应该正确识别 source=蓝色, target=黄色

### 测试旧架构

修改 `web_interface.py` 使用 `handle_message()`，然后重启。

---

## 推荐配置

**生产环境**：使用新架构（Skills-based）
- 更可靠
- 更可控
- 更易维护

**调试/实验**：可以切换回旧架构对比
- 保留旧代码用于参考
- 方便对比两种架构的行为差异

---

## 常见问题

### Q: 新架构是否支持所有旧功能？

A: 是的。新架构通过组合技能实现了旧架构的所有功能：
- 单步任务 → 单步技能（pick_object, place_object_*）
- 多步任务 → 组合技能（pick_and_place_*）

### Q: 如何确认当前使用的是哪种架构？

A: 查看日志输出：
- 新架构：`[Skill Selected] skill_name`
- 旧架构：`[Workflow] Step 1/N`

### Q: 可以同时使用两种架构吗？

A: 可以，但不推荐。建议统一使用新架构。

### Q: 旧架构会被删除吗？

A: 短期内不会。旧代码会保留作为参考，但不再维护。

---

## 版本历史

- **v0.4.0 (2026-04-22)**: 引入 Skills-based 架构，保留旧架构代码
- **v0.3.0 (2026-04-20)**: Intent-based 架构（旧架构）
