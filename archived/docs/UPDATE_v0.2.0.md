# Baxter-Claw OpenClaw 插件更新说明

## 版本 0.2.0 - LLM 意图识别

### 主要改进

#### 1. 使用 LLM 替代正则表达式进行意图识别

**之前的问题:**
- 使用正则表达式匹配，只能识别固定模式
- 英文支持有限（如 `pick.*?(\w+)` 只能捕获单个单词）
- 无法理解复杂的自然语言表达
- 需要为每种语言手动编写规则

**现在的解决方案:**
- 使用 Qwen LLM 进行智能意图识别
- 支持中文和英文的各种表达方式
- 可以理解复杂的短语（如 "细长的白色盒子", "the white box"）
- 自动提取参数（物体名称、方向等）

#### 2. 改进的错误报告

**Bridge Server 改进:**
- 所有 API 端点现在返回详细的错误信息
- 使用 try-catch 包装，捕获异常并返回具体错误描述

**Plugin 改进:**
- 捕获 HTTPStatusError 并提取响应中的详细错误信息
- 不再只显示 "400 Bad Request"，而是显示具体原因
- 例如: "Pre-grasp pose unsafe: X position -0.244 outside limits [0.3, 0.9]"

### 使用方法

#### 方式 1: 测试 LLM 意图识别（不连接机器人）

```bash
conda activate baxter-claw
cd ~/Baxter-claw
export QWEN_API_KEY="sk-bd990626c84a4142b9581f13c5317522"
python openclaw_plugin/test_llm_intent.py
```

这将测试各种中英文命令的意图识别，不需要启动 Bridge Server。

#### 方式 2: 命令行测试（需要 Bridge Server）

**终端 1 - 启动 Bridge Server:**
```bash
cd ~/catkin_ws && ./baxter.sh
conda activate baxter-claw
cd ~/Baxter-claw
python -m bridge.server --config config/baxter.yaml
```

**终端 2 - 测试插件:**
```bash
conda activate baxter-claw
cd ~/Baxter-claw
export QWEN_API_KEY="sk-bd990626c84a4142b9581f13c5317522"
python openclaw_plugin/test_plugin.py
```

#### 方式 3: Web 界面（推荐）

**终端 1 - 启动 Bridge Server:**
```bash
cd ~/catkin_ws && ./baxter.sh
conda activate baxter-claw
cd ~/Baxter-claw
python -m bridge.server --config config/baxter.yaml
```

**终端 2 - 启动 Web 界面:**
```bash
conda activate baxter-claw
cd ~/Baxter-claw
export QWEN_API_KEY="sk-bd990626c84a4142b9581f13c5317522"
python openclaw_plugin/web_interface.py
```

**浏览器:**
打开 http://localhost:5000

现在可以使用中文或英文命令，例如：
- "帮我拿一下红色的杯子"
- "pick the white box"
- "grab the blue bottle"
- "把它放到左边"
- "place it on the right"

### 支持的命令示例

#### 抓取物体
- 中文: "帮我拿一下红色的杯子", "抓住蓝色的瓶子", "取一下细长的白色盒子"
- 英文: "pick the white box", "grab the red cup", "get me the blue bottle"

#### 放置物体
- 中文: "把它放到左边", "放在右边", "放到前面"
- 英文: "place it on the left", "put it on the right", "place it in the center"

#### 夹爪控制
- 中文: "打开夹爪", "关闭夹爪"
- 英文: "open gripper", "close gripper"

#### 场景理解
- 中文: "看看桌上有什么", "识别一下物体"
- 英文: "what do you see", "describe the scene"

#### 其他
- 中文: "回到原位", "查看状态"
- 英文: "home", "status"

### 技术细节

#### LLM 配置

插件现在支持三种 LLM 提供商：
- **Qwen** (默认): 使用阿里云通义千问
- **OpenAI**: 使用 GPT-4
- **Claude**: 使用 Anthropic Claude

配置方式：
```python
plugin = BaxterClawPlugin(
    bridge_url="http://localhost:8420",
    llm_provider="qwen",  # 或 "openai", "claude"
    llm_api_key="your-api-key"
)
```

#### 意图识别流程

1. 用户输入自然语言命令
2. 插件构建 prompt，包含所有可用动作和参数说明
3. 调用 LLM API 进行意图识别
4. LLM 返回 JSON 格式的意图和参数
5. 插件解析 JSON 并执行相应动作

#### 错误处理改进

**之前:**
```
API 调用失败: 400 Bad Request
```

**现在:**
```
API 调用失败: Pre-grasp pose unsafe: X position -0.244 outside limits [0.3, 0.9]
```

这样用户可以清楚地知道问题所在（坐标超出工作空间），而不是只看到一个通用的错误代码。

### 下一步

1. **测试 LLM 意图识别**: 运行 `test_llm_intent.py` 验证各种命令
2. **测试完整流程**: 启动 Bridge Server 和 Web 界面，尝试实际控制机器人
3. **深度相机标定**: 运行 `calibrate_depth_camera.py` 提高定位精度
4. **根据需要调整**: 如果某些命令识别不准确，可以在 prompt 中添加更多示例

### 文件变更

- `openclaw_plugin/baxter_claw_plugin.py` - 重写意图识别逻辑，使用 LLM
- `openclaw_plugin/web_interface.py` - 添加 LLM 配置，更新示例命令
- `openclaw_plugin/config.yaml` - 添加 LLM 配置选项
- `openclaw_plugin/test_llm_intent.py` - 新增 LLM 测试脚本
- `openclaw_plugin/LANGUAGE_SUPPORT.md` - 语言支持说明文档
- `bridge/server.py` - 改进错误处理，返回详细错误信息

### 注意事项

- LLM API 调用需要网络连接
- 每次意图识别会调用一次 LLM API（有少量延迟和费用）
- 如果 LLM 调用失败，会返回 'unknown' 动作
- 确保 API key 有效且有足够的配额