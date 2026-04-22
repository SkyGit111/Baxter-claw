# D455 摄像头配置修复

## 问题

1. **摄像头混淆**：
   - 之前错误地将 Baxter 的 `head` 摄像头当作 D455
   - 实际上 D455 是外接的 RealSense 深度摄像头
   - `head` 摄像头视角很差，已决定弃用

2. **访问方式不同**：
   - Baxter 内置摄像头：通过 `capture_image(camera)` 访问
   - D455 深度摄像头：通过 `capture_rgbd()` 访问

## 解决方案

### 1. 移除 camera 参数，使用 use_d455 标志

**修改的文件**：
- `openclaw_plugin/baxter_claw_plugin.py`
- `bridge/models.py`
- `bridge/primitives.py`
- `bridge/server.py`

**新的 API 设计**：
```python
# 旧的设计（已废弃）
{
  "camera": "head"  # 容易混淆
}

# 新的设计
{
  "use_d455": true  # 明确使用 D455
}
```

### 2. 智能摄像头选择逻辑

**primitives.py 中的实现**：
```python
if use_d455 and self.driver.has_depth_camera():
    # 使用 D455 深度摄像头
    rgb, depth = self.driver.capture_rgbd()
    image_bytes = encode_to_jpeg(rgb)
else:
    # 回退到手腕摄像头
    image_bytes = self.driver.capture_image("right_hand")
```

**优先级**：
1. `use_d455=True` + D455 可用 → 使用 D455 ✅
2. `use_d455=True` + D455 不可用 → 回退到 right_hand
3. `use_d455=False` → 使用 right_hand

### 3. 移除 head 摄像头选项

**已删除**：
- 所有 `camera="head"` 的调用
- API 中的 `camera` 参数（对于视觉任务）

**保留**：
- `capture_image()` 方法仍支持 `"head"` 用于调试
- 但不在高级 API 中暴露

## 修改详情

### OpenClaw 插件

**baxter_claw_plugin.py**：
```python
class BaxterClawPlugin:
    def __init__(
        self,
        bridge_url: str = "http://localhost:8420",
        llm_provider: str = "qwen",
        llm_api_key: Optional[str] = None,
        use_d455: bool = True  # 默认使用 D455
    ):
        self.use_d455 = use_d455

# 所有视觉操作
locate_object(object_name, use_d455=self.use_d455)
describe_scene(use_d455=self.use_d455)
identify_objects(use_d455=self.use_d455)
pick_by_name(arm, object_name, use_d455=self.use_d455)
```

### API 模型

**models.py**：
```python
class LocateObjectRequest(BaseModel):
    object_name: str
    use_d455: bool = Field(default=True)  # 默认使用 D455

class DescribeSceneRequest(BaseModel):
    use_d455: bool = Field(default=True)
    language: str = Field(default="zh")

class IdentifyObjectsRequest(BaseModel):
    use_d455: bool = Field(default=True)

class PickByNameRequest(BaseModel):
    arm: Literal["left", "right"]
    object_name: str
    use_d455: bool = Field(default=True)
    approach_height: Optional[float] = 0.1
```

### 原语层

**primitives.py**：
```python
async def locate_object(self, object_name: str, use_d455: bool = True):
    if use_d455 and self.driver.has_depth_camera():
        # 使用 D455
        rgb, depth = self.driver.capture_rgbd()
        image_bytes = encode_to_jpeg(rgb)
    else:
        # 回退到手腕摄像头
        image_bytes = self.driver.capture_image("right_hand")
    
    # 调用 VLM
    location = await self.vlm_client.locate_object(image_bytes, ...)
```

### API 端点

**server.py**：
```python
@app.post("/vision/locate_object")
async def locate_object(req: LocateObjectRequest):
    result = await manager.primitives.locate_object(
        req.object_name,
        req.use_d455  # 传递 use_d455 标志
    )
    return VisionResponse(**result)
```

## 使用示例

### Python 代码

```python
from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin

# 默认使用 D455
plugin = BaxterClawPlugin(
    llm_api_key="your_key",
    use_d455=True  # 默认值
)

# 定位物体（使用 D455）
result = plugin.handle_message("识别魔方的坐标")

# 如果需要使用手腕摄像头（不推荐）
plugin = BaxterClawPlugin(
    llm_api_key="your_key",
    use_d455=False  # 使用手腕摄像头
)
```

### API 调用

```bash
# 使用 D455 定位物体（推荐）
curl -X POST http://localhost:8420/vision/locate_object \
  -H "Content-Type: application/json" \
  -d '{
    "object_name": "魔方",
    "use_d455": true
  }'

# 使用手腕摄像头（不推荐）
curl -X POST http://localhost:8420/vision/locate_object \
  -H "Content-Type: application/json" \
  -d '{
    "object_name": "魔方",
    "use_d455": false
  }'

# 中文场景描述（使用 D455）
curl -X POST http://localhost:8420/vision/describe_scene \
  -H "Content-Type: application/json" \
  -d '{
    "use_d455": true,
    "language": "zh"
  }'
```

## 摄像头对比

| 摄像头 | 访问方式 | 视角 | 深度信息 | 推荐用途 |
|--------|----------|------|----------|----------|
| **D455** | `capture_rgbd()` | 宽广，俯视桌面 | ✅ 有 | **物体定位、场景理解（推荐）** |
| right_hand | `capture_image("right_hand")` | 窄，手腕视角 | ❌ 无 | 近距离检查、精细操作 |
| left_hand | `capture_image("left_hand")` | 窄，手腕视角 | ❌ 无 | 近距离检查、精细操作 |
| ~~head~~ | ~~`capture_image("head")`~~ | ~~差~~ | ❌ 无 | ~~已弃用~~ |

## 配置要求

### 启用 D455

**config/baxter.yaml**：
```yaml
driver:
  type: "baxter"
  use_depth_camera: true  # 必须启用 D455

vlm:
  enabled: true
  provider: "claude"  # 或 "qwen"
  api_key: "your_key"
```

### 检查 D455 状态

```python
# 检查 D455 是否可用
if manager.driver.has_depth_camera():
    print("D455 可用")
else:
    print("D455 不可用，将使用手腕摄像头")
```

## 向后兼容性

### 破坏性变更

**API 参数变化**：
- 旧：`camera: str = "right_hand"`
- 新：`use_d455: bool = True`

**迁移指南**：
```python
# 旧代码
locate_object(object_name="魔方", camera="head")

# 新代码
locate_object(object_name="魔方", use_d455=True)
```

### 默认行为

**旧行为**：
- 默认使用 `right_hand` 摄像头
- 视角受限，无法看到完整桌面

**新行为**：
- 默认使用 D455 深度摄像头
- 视角宽广，能看到完整桌面
- 提供深度信息，定位更准确

## 优势

### 1. 更好的视角
- D455 俯视桌面，能看到完整工作区
- 手腕摄像头视角受限

### 2. 深度信息
- D455 提供 RGB + Depth
- 更准确的 3D 定位

### 3. 更高分辨率
- D455: 640x480 或更高
- 手腕摄像头：较低分辨率

### 4. 明确的配置
- `use_d455` 标志清晰明了
- 避免 `camera="head"` 的混淆

## 测试

### 测试 D455

```python
from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin

# 使用 D455
plugin = BaxterClawPlugin(use_d455=True)
result = plugin.handle_message("识别魔方的坐标")
print(result)  # 应该能找到桌面上的物体

# 使用手腕摄像头
plugin = BaxterClawPlugin(use_d455=False)
result = plugin.handle_message("识别魔方的坐标")
print(result)  # 可能找不到（视角受限）
```

### 测试中文描述

```python
plugin = BaxterClawPlugin(use_d455=True)
result = plugin.handle_message("看看桌上有什么")
print(result)  # 应该返回中文描述
```

## 总结

### 改进点
1. ✅ 移除了 `camera` 参数的混淆
2. ✅ 明确区分 D455 和 Baxter 内置摄像头
3. ✅ 默认使用 D455（视角最佳）
4. ✅ 支持回退到手腕摄像头
5. ✅ 移除了 head 摄像头选项（已弃用）
6. ✅ 支持中文场景描述

### 推荐配置

```python
# 推荐配置
plugin = BaxterClawPlugin(
    llm_api_key="your_key",
    use_d455=True,  # 使用 D455（推荐）
    llm_provider="qwen"
)
```

### 配置文件

```yaml
# config/baxter.yaml
driver:
  type: "baxter"
  use_depth_camera: true  # 启用 D455

vlm:
  enabled: true
  provider: "claude"
  api_key: "your_key"
```

现在系统会正确使用 D455 深度摄像头进行物体定位和场景理解，视角更好，定位更准确！
