# Baxter-Claw OpenClaw Plugin

OpenClaw 插件，用于通过自然语言控制 Baxter 机器人。

## 功能

- **视觉抓取**: "帮我拿一下红色的杯子"
- **坐标控制**: "把它放到左边"
- **夹爪控制**: "打开夹爪" / "关闭夹爪"
- **场景理解**: "看看桌上有什么"
- **状态查询**: "查看机器人状态"
- **回原位**: "回到原位"

## 安装

### 1. 确保 Bridge Server 正在运行

```bash
cd ~/catkin_ws && ./baxter.sh
conda activate baxter-claw
cd ~/Baxter-claw
python -m bridge.server --config config/baxter.yaml
```

### 2. 安装依赖

```bash
pip install httpx
```

### 3. 测试插件

```bash
cd ~/Baxter-claw
python openclaw_plugin/baxter_claw_plugin.py
```

## 使用方法

### 方式 1: 直接使用插件

```python
from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin

plugin = BaxterClawPlugin(bridge_url="http://localhost:8420")

# 处理用户消息
response = plugin.handle_message("帮我拿一下红色的杯子")
print(response)
```

### 方式 2: 集成到 OpenClaw

将此插件注册到 OpenClaw 框架中，然后通过 OpenClaw 的对话接口使用。

### 方式 3: 集成到通讯软件

#### 微信 Bot 示例

```python
from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin
import itchat

plugin = BaxterClawPlugin()

@itchat.msg_register(itchat.content.TEXT)
def text_reply(msg):
    user_message = msg['Text']
    response = plugin.handle_message(user_message)
    return response

itchat.auto_login()
itchat.run()
```

#### 钉钉 Bot 示例

```python
from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin
from dingtalkchatbot.chatbot import DingtalkChatbot

plugin = BaxterClawPlugin()
webhook = "YOUR_DINGTALK_WEBHOOK_URL"
bot = DingtalkChatbot(webhook)

# 接收消息并处理
def handle_dingtalk_message(message):
    response = plugin.handle_message(message)
    bot.send_text(response)
```

#### 简单 Web 界面示例

```python
from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin
from flask import Flask, request, jsonify

app = Flask(__name__)
plugin = BaxterClawPlugin()

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    response = plugin.handle_message(user_message)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## 支持的命令

### 抓取命令
- "帮我拿一下红色的杯子"
- "抓住蓝色的盒子"
- "取一下那个瓶子"
- "pick the red cup"

### 放置命令
- "把它放到左边"
- "放在右边"
- "放到前面"
- "place it on the left"

### 夹爪控制
- "打开夹爪"
- "关闭夹爪"
- "松开"
- "夹紧"

### 场景理解
- "看看桌上有什么"
- "识别一下物体"
- "describe the scene"

### 其他命令
- "回到原位" - 回到 home 位置
- "查看状态" - 查看机器人状态

## API 参考

### BaxterClawPlugin

#### `__init__(bridge_url: str = "http://localhost:8420")`

初始化插件。

**参数:**
- `bridge_url`: Bridge Server 的 URL

#### `handle_message(user_message: str) -> str`

处理用户消息的主入口。

**参数:**
- `user_message`: 用户的自然语言消息

**返回:**
- 回复消息字符串

#### `parse_intent(user_message: str) -> Dict[str, Any]`

解析用户消息，提取意图和参数。

**返回:**
```python
{
    'action': 'pick_by_name',  # 动作类型
    'params': {'object_name': '红色杯子'},  # 参数
    'confidence': 0.8  # 置信度
}
```

#### `execute_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]`

执行具体动作。

**返回:**
```python
{
    'success': True,  # 是否成功
    'message': '成功抓取 红色杯子',  # 消息
    'data': {...}  # 详细数据
}
```

## 扩展

### 添加新的意图识别

在 `parse_intent` 方法中添加新的正则表达式模式：

```python
patterns = {
    'your_new_action': [
        r'你的.*?正则表达式',
        r'another.*?pattern',
    ],
    # ...
}
```

### 添加新的动作执行

在 `execute_action` 方法中添加新的动作处理：

```python
elif action == 'your_new_action':
    # 调用 Bridge Server API
    response = self.client.post(
        f"{self.bridge_url}/your/endpoint",
        json={'param': value}
    )
    # 处理响应
    return {'success': True, 'message': '完成'}
```

## 故障排除

### 问题 1: 连接失败

**错误**: `API 调用失败: Connection refused`

**解决**: 确保 Bridge Server 正在运行：
```bash
python -m bridge.server --config config/baxter.yaml
```

### 问题 2: 无法识别意图

**错误**: `抱歉，我不太理解你的意思`

**解决**: 
- 检查命令格式是否正确
- 参考"支持的命令"部分
- 在 `parse_intent` 中添加新的模式

### 问题 3: 视觉抓取失败

**错误**: `无法定位 xxx`

**解决**:
- 确保物体在相机视野内
- 物体描述要清晰（颜色 + 物体名称）
- 运行深度相机标定：`python calibrate_depth_camera.py`

## 许可证

MIT License

## 联系方式

如有问题，请提交 Issue。