# 摄像头和语言配置优化

## 问题

1. **摄像头问题**：所有视觉任务使用 `right_hand` 摄像头，但它无法看到完整桌面
   - D455 深度摄像头（head camera）视角最佳，能完整拍摄桌面
   - 手腕摄像头视角有限，无法定位桌面上的物体

2. **语言问题**：`describe_scene` 返回英文描述
   - 用户希望返回中文
   - 需要通过 VLM prompt 控制输出语言

## 解决方案

### 1. 默认使用 D455 摄像头

**修改文件**：`openclaw_plugin/baxter_claw_plugin.py`

**改动**：
```python
class BaxterClawPlugin:
    def __init__(
        self,
        bridge_url: str = "http://localhost:8420",
        llm_provider: str = "qwen",
        llm_api_key: Optional[str] = None,
        default_camera: str = "head"  # 新增：默认使用 head camera (D455)
    ):
        self.default_camera = default_camera
```

**影响的操作**：
- `locate_object` - 使用 `self.default_camera` (head)
- `describe_scene` - 使用 `self.default_camera` (head)
- `identify_objects` - 使用 `self.default_camera` (head)
- `pick_by_name` - 使用 `self.default_camera` (head)

**摄像头选项**：
- `"head"` - D455 深度摄像头（推荐，视角最佳）
- `"right_hand"` - 右手腕摄像头
- `"left_hand"` - 左手腕摄像头

### 2. 支持中文场景描述

**修改文件**：
1. `bridge/vlm_client.py` - VLM 客户端
2. `bridge/primitives.py` - 原语层
3. `bridge/models.py` - API 模型
4. `bridge/server.py` - API 端点

**VLM Prompt 改动**：
```python
# 中文 prompt
if language == "zh":
    prompt = """请用中文描述这个场景（从机器人的视角）。包括：
1. 可见的物体有哪些
2. 它们的大致位置
3. 任何值得注意的特征或障碍物
4. 对机器人操作任务的建议

请简洁明了，重点关注对机器人控制有用的信息。"""

# 英文 prompt (原有)
else:
    prompt = """Describe this scene from a robot's perspective..."""
```

**API 调用**：
```python
# 默认中文
POST /vision/describe_scene
{
  "camera": "head",
  "language": "zh"  # 新增参数
}

# 英文
POST /vision/describe_scene
{
  "camera": "head",
  "language": "en"
}
```

## 使用示例

### Python 代码
```python
from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin

# 创建插件，默认使用 D455 摄像头
plugin = BaxterClawPlugin(
    llm_api_key="your_key",
    default_camera="head"  # D455 摄像头
)

# 定位物体（使用 D455）
result = plugin.handle_message("识别魔方的坐标")
# 现在能看到完整桌面了！

# 描述场景（中文）
result = plugin.handle_message("看看桌上有什么")
# 返回中文描述
```

### 直接 API 调用
```bash
# 使用 D455 定位物体
curl -X POST http://localhost:8420/vision/locate_object \
  -H "Content-Type: application/json" \
  -d '{
    "object_name": "魔方",
    "camera": "head"
  }'

# 中文场景描述
curl -X POST http://localhost:8420/vision/describe_scene \
  -H "Content-Type: application/json" \
  -d '{
    "camera": "head",
    "language": "zh"
  }'
```

## 配置选项

### 摄像头选择策略

**推荐配置**：
```python
# 全局视觉任务：使用 D455 (head)
default_camera = "head"

# 特殊情况：
# - 需要近距离观察：使用手腕摄像头
# - 需要特定角度：手动指定摄像头
```

**摄像头对比**：

| 摄像头 | 视角 | 深度信息 | 适用场景 |
|--------|------|----------|----------|
| head (D455) | 宽广，俯视桌面 | ✅ 有 | 物体定位、场景理解 |
| right_hand | 窄，手腕视角 | ❌ 无 | 近距离检查、精细操作 |
| left_hand | 窄，手腕视角 | ❌ 无 | 近距离检查、精细操作 |

### 语言选择

**默认**：中文 (`"zh"`)

**可选**：
- `"zh"` - 中文
- `"en"` - 英文

## 技术细节

### D455 摄像头集成

系统已经支持 D455 深度摄像头：

```python
# bridge/drivers/baxter_driver.py
def __init__(self, use_depth_camera: bool = False):
    if use_depth_camera:
        from .realsense_driver import RealSenseDriver
        self._depth_camera = RealSenseDriver()
```

**配置文件**：`config/baxter.yaml`
```yaml
driver:
  type: "baxter"
  use_depth_camera: true  # 启用 D455
```

### 摄像头访问

**Baxter 内置摄像头**：
- 通过 ROS topics 访问
- `/cameras/head_camera/image`
- `/cameras/left_hand_camera/image`
- `/cameras/right_hand_camera/image`

**D455 深度摄像头**：
- 通过 RealSense SDK 访问
- 提供 RGB + Depth 数据
- 更高的分辨率和精度

## 向后兼容性

**默认行为变化**：
- 旧代码：使用 `right_hand` 摄像头
- 新代码：使用 `head` 摄像头（D455）

**兼容性保证**：
- 可以通过 `default_camera` 参数恢复旧行为
- API 仍然支持指定任意摄像头
- 语言参数可选，默认中文

**迁移建议**：
```python
# 如果需要旧行为
plugin = BaxterClawPlugin(
    default_camera="right_hand"  # 使用旧的默认摄像头
)
```

## 测试

### 测试摄像头切换
```python
# 测试 D455
plugin = BaxterClawPlugin(default_camera="head")
result = plugin.handle_message("识别魔方的坐标")
print(result)  # 应该能找到桌面上的物体

# 测试手腕摄像头
plugin = BaxterClawPlugin(default_camera="right_hand")
result = plugin.handle_message("识别魔方的坐标")
print(result)  # 可能找不到（视角受限）
```

### 测试语言切换
```python
# 中文描述
result = plugin.handle_message("看看桌上有什么")
print(result)  # 应该返回中文

# 直接 API 测试英文
import httpx
response = httpx.post(
    "http://localhost:8420/vision/describe_scene",
    json={"camera": "head", "language": "en"}
)
print(response.json())  # 应该返回英文
```

## 总结

### 改进点
1. ✅ 默认使用 D455 摄像头，视角更好
2. ✅ 支持中文场景描述
3. ✅ 保持向后兼容性
4. ✅ 灵活的配置选项

### 影响
- **定位准确性提升** - D455 能看到完整桌面
- **用户体验改善** - 中文描述更友好
- **配置灵活性** - 可根据需求选择摄像头

### 建议配置
```python
# 推荐配置
plugin = BaxterClawPlugin(
    llm_api_key="your_key",
    default_camera="head",  # 使用 D455
    llm_provider="qwen"
)
```

### 配置文件
```yaml
# config/baxter.yaml
driver:
  type: "baxter"
  use_depth_camera: true  # 必须启用

vlm:
  enabled: true
  provider: "claude"  # 或 "qwen"
  api_key: "your_key"
```
