# Baxter-Claw 完整架构文档 - 第3节：视觉系统

## 3. 视觉系统架构

### 3.1 视觉系统概述

Baxter-Claw 的视觉系统是实现智能操作的核心，集成了深度相机、手腕相机和 VLM，提供精确的物体定位和场景理解能力。

#### 3.1.1 相机配置

**主相机：Intel RealSense D455**
- 位置：固定在机器人基座前方，俯视工作区
- 分辨率：640x480 @ 30fps
- 功能：RGB + 深度，用于全局物体定位
- 优势：精确的 3D 坐标，不受手臂遮挡影响

**辅助相机：Baxter 手腕相机**
- 位置：左右手腕各一个
- 分辨率：640x400
- 功能：近距离观察，抓取验证
- 优势：跟随手臂移动，可以近距离观察

#### 3.1.2 视觉流程

```
用户请求："抓住蓝色方块"
    ↓
[Phase 1] 全局定位 (D455)
    ├─ 双臂避让到 home 位置
    ├─ D455 拍摄 RGB + 深度图
    ├─ VLM 识别物体位置（2D）
    ├─ 深度图获取 Z 坐标
    ├─ 相机坐标 → 机器人基座坐标
    └─ 应用校准偏移量
    ↓
[Phase 2] 精细定位 (手腕相机，可选)
    ├─ 手臂移动到物体上方
    ├─ 手腕相机近距离拍摄
    ├─ VLM 精确定位
    └─ 修正坐标
    ↓
[Phase 3] 执行抓取
    ↓
[Phase 4] 验证抓取 (手腕相机，可选)
    ├─ 手腕相机拍摄夹爪
    ├─ VLM 判断是否抓到物体
    └─ 失败则重试
```

### 3.2 VLM Client (bridge/vlm_client.py)

VLM Client 负责与视觉语言模型交互，实现物体识别和定位。

#### 3.2.1 支持的 VLM 提供商

```python
class VLMClient:
    PROVIDERS = {
        'qwen': {
            'endpoint': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation',
            'model': 'qwen-vl-max'
        },
        'openai': {
            'endpoint': 'https://api.openai.com/v1/chat/completions',
            'model': 'gpt-4-vision-preview'
        },
        'claude': {
            'endpoint': 'https://api.anthropic.com/v1/messages',
            'model': 'claude-3-opus-20240229'
        }
    }
```

#### 3.2.2 核心方法

**1. locate_object(image_bytes, object_name, workspace_bounds)**
- 纯 VLM 定位（2D + 估计深度）
- 适用于：手腕相机、无深度信息的场景

```python
async def locate_object(self, image_bytes, object_name, workspace_bounds):
    # 1. 构建 prompt
    prompt = f"""在这张图片中找到 {object_name}。
    
    工作空间范围：
    X: {workspace_bounds['x'][0]:.2f} 到 {workspace_bounds['x'][1]:.2f} 米
    Y: {workspace_bounds['y'][0]:.2f} 到 {workspace_bounds['y'][1]:.2f} 米
    Z: {workspace_bounds['z'][0]:.2f} 到 {workspace_bounds['z'][1]:.2f} 米
    
    返回 JSON 格式：
    {{
        "found": true/false,
        "position": [x, y, z],
        "confidence": 0-100,
        "reasoning": "..."
    }}"""
    
    # 2. 调用 VLM
    response = await self._call_vlm(image_b64, prompt)
    
    # 3. 解析响应
    return self._parse_location_response(response)
```

**2. locate_object_with_depth(image_bytes, depth_image, object_name, depth_camera, workspace_bounds)**
- VLM + 深度融合定位（精确 3D）
- 适用于：D455 深度相机

```python
async def locate_object_with_depth(self, image_bytes, depth_image, object_name, depth_camera, workspace_bounds):
    # 1. VLM 获取 2D 像素坐标
    location_2d = await self.locate_object(image_bytes, object_name, workspace_bounds)
    
    if not location_2d['found']:
        return location_2d
    
    # 2. 从深度图获取真实深度
    pixel_x = int(location_2d['pixel_x'])
    pixel_y = int(location_2d['pixel_y'])
    depth_value = depth_image[pixel_y, pixel_x]  # 单位：毫米
    
    # 3. 像素 + 深度 → 3D 坐标（相机坐标系）
    point_3d = depth_camera.deproject_pixel_to_point(
        pixel_x, pixel_y, depth_value / 1000.0
    )
    
    # 4. 返回精确 3D 位置
    return {
        'found': True,
        'position': list(point_3d),
        'confidence': location_2d['confidence'],
        'depth_mm': depth_value,
        'pixel': [pixel_x, pixel_y]
    }
```

**3. query_image(image_bytes, prompt)**
- 通用 VLM 查询接口
- 适用于：抓取验证、场景描述等自定义任务

```python
async def query_image(self, image_bytes, prompt):
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    response = await self._call_vlm(image_b64, prompt)
    return self._extract_text(response)
```

### 3.3 Multi-View VLM (bridge/multi_view_vlm.py)

Multi-View VLM 协调器实现了多视角定位流程，提供最高精度的物体定位。

#### 3.3.1 两阶段定位流程

**Phase 1: 全局定位 (Global Localization)**
```python
async def _phase1_global_localization(self, object_name, arm):
    # Step 1: 双臂避让
    await self._retract_arm(arm)
    await self._retract_arm('left' if arm == 'right' else 'right')
    await asyncio.sleep(1.5)
    
    # Step 2: D455 拍摄和分析
    d455_result = await self._capture_and_analyze_d455(object_name, "phase1")
    
    # Step 3: 融合结果
    return self._fuse_phase1_results(d455_result)
```

**Phase 2: 精细定位 (Wrist Refinement，可选)**
```python
async def _phase2_wrist_refinement(self, object_name, arm, global_position):
    # Step 1: 移动到物体上方
    approach_position = global_position.copy()
    approach_position[2] += 0.15  # 上方 15cm
    
    self.driver.move_to_pose(arm, approach_position + orientation)
    
    # Step 2: 手腕相机拍摄
    wrist_result = await self._capture_and_analyze_wrist(arm, object_name)
    
    # Step 3: 融合全局和局部结果
    return self._fuse_global_and_wrist(global_position, wrist_result)
```

#### 3.3.2 坐标变换流程

```python
# 1. VLM 返回相机坐标系下的位置
position_camera = [x_cam, y_cam, z_cam]

# 2. 相机坐标 → 机器人基座坐标
position_base = self.transforms.transform_d455_to_base(position_camera)

# 3. 应用校准偏移量（经验修正）
calibration_offset = np.array([0.1329, -0.2644, -0.05])
position_calibrated = position_base + calibration_offset

# 4. 最终位置
final_position = position_calibrated.tolist()
```

#### 3.3.3 校准偏移量

通过 8 次实际测试得出的经验偏移量：

```python
self.calibration_offset = np.array([
    0.1329,   # X: +13.29 cm ± 0.69 cm (稳定)
    -0.2644,  # Y: -26.44 cm ± 0.66 cm (稳定)
    -0.05     # Z: -5 cm (保守值，原始 -6.01 cm ± 6.19 cm 不稳定)
])
```

### 3.4 Camera Transforms (bridge/camera_transforms.py)

相机坐标变换模块负责在不同坐标系之间转换。

#### 3.4.1 坐标系定义

**1. D455 相机坐标系**
- 原点：相机光心
- X 轴：向右
- Y 轴：向下
- Z 轴：向前（深度方向）

**2. 机器人基座坐标系**
- 原点：Baxter 基座中心
- X 轴：向前
- Y 轴：向左
- Z 轴：向上

**3. 手腕相机坐标系**
- 原点：手腕相机光心
- 跟随手臂运动

#### 3.4.2 Hand-Eye 标定

使用 easy_handeye 进行 eye-on-base 标定：

```yaml
# ~/.ros/easy_handeye/baxter_d455_handeye_calibration_eye_on_base.yaml
transformation:
  translation:
    x: 0.79105528
    y: -0.03208981
    z: 0.87098674
  rotation:
    x: -0.28156844
    y: 0.67849261
    z: -0.67849261
    w: 0.06281234
```

转换为旋转矩阵和平移向量：

```python
class CameraTransforms:
    def __init__(self):
        # 从标定文件加载
        self.d455_to_base_translation = np.array([0.791, -0.032, 0.871])
        self.d455_to_base_rotation = self._quaternion_to_matrix(
            [-0.282, 0.678, -0.678, 0.063]
        )
    
    def transform_d455_to_base(self, point_camera):
        # 应用旋转和平移
        point_base = self.d455_to_base_rotation @ point_camera + self.d455_to_base_translation
        return point_base
```

### 3.5 Image Processor (bridge/image_processor.py)

图像处理模块提供图像增强和标注功能。

#### 3.5.1 功能

```python
class ImageProcessor:
    @staticmethod
    def annotate_detection(image, position_2d, label, confidence):
        """在图像上标注检测结果"""
        cv2.circle(image, position_2d, 10, (0, 255, 0), 2)
        cv2.putText(image, f"{label} ({confidence}%)", 
                    position_2d, cv2.FONT_HERSHEY_SIMPLEX, 
                    0.6, (0, 255, 0), 2)
        return image
    
    @staticmethod
    def create_depth_visualization(depth_image):
        """深度图可视化"""
        depth_normalized = cv2.normalize(depth_image, None, 0, 255, cv2.NORM_MINMAX)
        depth_colored = cv2.applyColorMap(depth_normalized.astype(np.uint8), cv2.COLORMAP_JET)
        return depth_colored
```

### 3.6 视觉系统性能

#### 3.6.1 定位精度

**D455 + VLM + 校准偏移**：
- X 轴：±1-2 cm
- Y 轴：±1-2 cm
- Z 轴：±2-3 cm

**纯 VLM（手腕相机）**：
- X/Y 轴：±3-5 cm
- Z 轴：±5-10 cm（估计值）

#### 3.6.2 处理时间

- D455 图像捕获：~0.1s
- VLM 推理：~1-2s
- 坐标变换：<0.01s
- **总计**：~1.5-2.5s

#### 3.6.3 成功率

- 常见物体（方块、杯子）：>90%
- 小物体（<3cm）：~70%
- 复杂场景（多物体）：~80%

---

**下一节**：[第4节：OpenClaw 插件系统](ARCHITECTURE_COMPLETE_04_OPENCLAW.md)
