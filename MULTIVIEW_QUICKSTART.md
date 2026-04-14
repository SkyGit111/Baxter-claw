# 多视角VLM物体定位系统 - 快速开始

## 🎯 系统概述

完整的多视角VLM物体定位系统，结合：
- **D455深度相机** - 精确3D定位
- **Baxter头部相机** - 交叉验证
- **Baxter手腕相机** - 近距离精确定位
- **手眼标定** - 准确的坐标转换
- **图像预处理** - 优化VLM分析
- **优化提示词** - 针对不同阶段的详细指导

## 🚀 快速开始

### 1. 测试模块（无需机器人）

```bash
python test_modules.py
```

这会测试：
- ✅ 坐标转换功能
- ✅ 图像处理功能
- ✅ VLM提示词生成
- ✅ 模块集成

### 2. 完整流程测试（需要机器人）

```bash
python test_multiview_vlm.py
```

按照提示输入：
- 物体名称（如 "red cup"）
- 使用哪个手臂（left/right）
- 是否启用手腕精确定位（y/n）

## 📋 系统要求

### 硬件
- Baxter机器人
- Intel RealSense D455深度相机
- 已完成手眼标定

### 软件
- Python 3.8+
- ROS Noetic
- 依赖包：
  - numpy
  - opencv-python
  - scipy
  - pyrealsense2
  - httpx
  - pyyaml

### 配置
确保 `config/baxter.yaml` 中：
```yaml
driver:
  use_depth_camera: true  # 必须启用
```

## 🔧 使用方法

### 基本用法

```python
import asyncio
from bridge.drivers.baxter_driver import BaxterDriver
from bridge.vlm_client import VLMClient
from bridge.safety import SafetyValidator
from bridge.multi_view_vlm import MultiViewVLMCoordinator

async def locate_object():
    # 初始化
    driver = BaxterDriver(use_depth_camera=True)
    driver.connect()
    driver.enable()
    
    vlm_client = VLMClient(provider='qwen')
    safety = SafetyValidator(config_path='config/baxter.yaml')
    coordinator = MultiViewVLMCoordinator(driver, vlm_client, safety)
    
    # 定位物体
    result = await coordinator.locate_object_multiview(
        object_name="red cup",
        arm="right",
        use_wrist_refinement=True
    )
    
    # 使用结果
    if result and result['found']:
        print(f"Found at: {result['position']}")
        print(f"Confidence: {result['confidence']}%")
        
        # 移动到物体
        approach_pose = result['position'].copy()
        approach_pose[2] += 0.1  # 10cm above
        driver.move_to_pose("right", approach_pose)
    
    driver.disconnect(keep_enabled=True)

# 运行
asyncio.run(locate_object())
```

### 仅Phase 1（快速）

```python
result = await coordinator.locate_object_multiview(
    object_name="red cup",
    arm="right",
    use_wrist_refinement=False  # 跳过手腕精确定位
)
```

### 完整流程（精确）

```python
result = await coordinator.locate_object_multiview(
    object_name="red cup",
    arm="right",
    use_wrist_refinement=True  # 启用手腕精确定位
)
```

## 📊 结果解读

### 返回结果

```python
{
    'found': True,
    'position': [0.6, 0.0, 0.05],  # 基座坐标系 [x, y, z]
    'confidence': 92,               # 置信度 0-100
    'description': "...",           # 物体描述
    'bounding_box': [x1, y1, x2, y2],  # 像素坐标
    
    # 处理详情
    'coordinate_transformed': True,     # 是否应用坐标转换
    'multi_view_validated': True,       # 是否多视角验证
    'validation_quality': 'excellent',  # 验证质量
    'wrist_validated': True,            # 是否手腕验证
    'depth_enhanced': True,             # 是否深度增强
    'refinement_applied': True,         # 是否应用精确定位
    
    # 抓取建议（如果有）
    'grasp_recommendations': {
        'best_grasp_points': "...",
        'approach_angle': "...",
        'obstacles': "..."
    }
}
```

### 置信度解读

- **90-100%**：非常可靠，可以直接抓取
- **80-89%**：可靠，建议验证后抓取
- **70-79%**：中等可靠，需要额外验证
- **<70%**：不可靠，建议重新定位

## 🐛 调试

### 查看调试图像

运行后会自动保存调试图像到当前目录：
- `debug_d455_phase1_*.jpg` - Phase 1 D455图像
- `debug_head_phase1_*.jpg` - Phase 1 头部相机图像
- `debug_wrist_phase2_*.jpg` - Phase 2 手腕相机图像
- `debug_d455_phase2_*.jpg` - Phase 2 D455图像

### 启用/禁用调试

```python
coordinator = MultiViewVLMCoordinator(driver, vlm_client, safety)
coordinator.debug = True   # 启用调试图像保存
coordinator.debug = False  # 禁用调试图像保存
```

## 📖 详细文档

- **完整实现总结**：[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **多视角方案指南**：[MULTIVIEW_VLM_GUIDE.md](MULTIVIEW_VLM_GUIDE.md)
- **手眼标定指南**：[HANDEYE_CALIBRATION_GUIDE.md](HANDEYE_CALIBRATION_GUIDE.md)

## 🔍 故障排除

### 问题：找不到物体

**可能原因**：
1. 物体不在相机视野内
2. 光照条件不佳
3. 物体被遮挡
4. VLM提供商API问题

**解决方法**：
1. 检查调试图像，确认物体可见
2. 改善光照条件
3. 移动机械臂避免遮挡
4. 检查VLM API密钥和网络连接

### 问题：位置不准确

**可能原因**：
1. 手眼标定不准确
2. 相机镜头有污渍
3. 深度相机距离过远/过近

**解决方法**：
1. 重新进行手眼标定
2. 清洁相机镜头
3. 调整相机到物体的距离（最佳：0.5-1.5m）

### 问题：置信度很低

**可能原因**：
1. 多视角结果不一致
2. 物体特征不明显
3. 图像质量差

**解决方法**：
1. 检查调试图像质量
2. 改善光照和对比度
3. 使用更明显的物体进行测试
4. 启用手腕精确定位

## 🎓 最佳实践

### 1. 选择合适的模式

- **快速定位**：仅Phase 1，适合大物体（>10cm）
- **精确定位**：Phase 1 + Phase 2，适合小物体（<5cm）

### 2. 优化环境

- 良好的光照（避免强烈阴影）
- 简洁的背景（减少干扰）
- 物体与背景有明显对比

### 3. 物体描述

- 使用具体描述："red plastic cup"
- 包含颜色、材质、形状
- 避免模糊描述："那个东西"

### 4. 验证结果

- 检查置信度
- 查看调试图像
- 验证位置是否合理

## 📞 支持

如有问题，请查看：
1. [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - 完整实现细节
2. [MULTIVIEW_VLM_GUIDE.md](MULTIVIEW_VLM_GUIDE.md) - 方案设计文档
3. 调试图像 - 查看实际捕获的图像

## 🎉 开始使用

```bash
# 1. 测试模块
python test_modules.py

# 2. 测试完整流程
python test_multiview_vlm.py

# 3. 集成到你的应用
# 参考上面的"基本用法"示例
```

祝你使用愉快！🚀
