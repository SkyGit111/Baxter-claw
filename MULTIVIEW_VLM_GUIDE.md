# 多视角VLM定位方案

## 概述

本方案通过融合多个相机视角来提高VLM（视觉语言模型）的物体定位精度。

### 相机配置

1. **D455深度相机**：固定安装，提供RGB-D数据，始终启用
2. **Baxter头部相机**：固定视角，提供顶视图
3. **Baxter手腕相机**：可移动，提供近距离细节视图

### 限制

- Baxter同时只能启用2个相机（头部、左手、右手三选二）
- D455不占用Baxter相机资源，可以始终启用

## 两阶段定位策略

### 阶段1：全局定位（Global Localization）

**目标**：快速识别物体并获得初步位置估计

**步骤**：
1. 机械臂收起到"反打包"姿态，避免遮挡桌面
2. 启用D455 + 头部相机（2个相机）
3. 同时采集两个视角的图像
4. VLM分析D455图像（带深度增强）获得3D位置
5. VLM分析头部相机图像进行交叉验证
6. 如果两个视角结果一致（误差<15cm），提高置信度

**优势**：
- 两个顶视角度可以互相验证
- D455深度数据提供准确的3D坐标
- 机械臂收起避免遮挡

**输出**：
- 物体初步位置 [x, y, z]
- 置信度（如果多视角一致，置信度提升）
- 物体描述和边界框

### 阶段2：手腕精确定位（Wrist Refinement）

**目标**：通过近距离视角精确定位物体

**步骤**：
1. 关闭头部相机，启用手腕相机（切换相机）
2. 移动手腕到物体上方约30cm处
3. 手腕相机朝下拍摄，获得近距离清晰图像
4. 结合之前拍摄的D455、头部相机图像，和刚刚拍摄的手腕相机图像，进行精确定位

**优势**：
- 手腕视角更近，图像更清晰
- 可以看到物体细节（纹理、边缘等）
- 机械臂移动避免了固定视角的遮挡问题

**输出**：
- 精确位置 [x, y, z]
- 高置信度（通常>90%）
- 详细描述（融合多视角信息）

## 使用方法

### 基本用法

```python
from bridge.drivers.baxter_driver import BaxterDriver
from bridge.vlm_client import VLMClient
from bridge.safety import SafetyValidator
from bridge.multi_view_vlm import MultiViewVLMCoordinator

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
    use_wrist_refinement=True  # 启用手腕精确定位
)

if result and result['found']:
    print(f"Position: {result['position']}")
    print(f"Confidence: {result['confidence']}%")
```

### 测试脚本

```bash
# 运行交互式测试
python test_multiview_vlm.py
```

测试脚本会引导你：
1. 输入要定位的物体名称
2. 选择使用哪个手臂的手腕相机
3. 选择是否启用手腕精确定位
4. 显示定位结果
5. 可选：移动机械臂到检测位置

## 关键参数

### `locate_object_multiview()`

- `object_name`: 物体名称（如"red cup", "blue box"）
- `arm`: 使用哪个手臂的手腕相机（"left" 或 "right"）
- `use_wrist_refinement`: 是否启用阶段2精确定位（默认True）

### 返回结果

```python
{
    'found': True,                    # 是否找到物体
    'position': [x, y, z],            # 3D位置（米）
    'confidence': 95,                 # 置信度（0-100）
    'description': "...",             # 物体描述
    'bounding_box': [x1, y1, x2, y2], # 像素坐标边界框
    'multi_view_validated': True,     # 是否通过多视角验证
    'wrist_validated': True,          # 是否通过手腕相机验证
    'depth_enhanced': True,           # 是否使用深度增强
    'refinement_applied': True,       # 是否应用了精确定位
    'vlm_estimate': [x, y, z]         # VLM原始估计（对比用）
}
```

## 性能优化建议

### 1. 何时使用手腕精确定位

**推荐使用**：
- 物体较小（<5cm）
- 需要高精度抓取（误差<1cm）
- 物体有复杂纹理或形状
- 初步定位置信度较低（<80%）

**可以跳过**：
- 物体较大且明显（>10cm）
- 初步定位置信度很高（>90%）
- 时间敏感的任务
- 物体位置不需要很精确

### 2. 头部相机的使用

**优势**：
- 固定视角，稳定可靠
- 覆盖范围大
- 可以看到整个工作区

**劣势**：
- 角度倾斜（不是正俯视）
- 画面中桌面只占一部分
- 分辨率可能不如D455

**建议**：
- 主要用于交叉验证，不作为主要定位源
- 如果D455和头部相机结果差异大（>15cm），降低置信度
- 可以考虑对头部相机图像进行透视变换（未实现）

### 3. 相机切换策略

由于Baxter只能同时启用2个相机，需要管理相机切换：

**阶段1**：D455 + 头部相机
- D455不占用Baxter资源，始终开启
- 头部相机提供第二视角

**阶段2**：D455 + 手腕相机
- 关闭头部相机
- 启用手腕相机
- D455继续工作

**注意**：相机切换可能需要短暂延迟（~0.5秒）

## 坐标系转换

### 当前实现

目前所有相机的3D坐标都假设在机器人基座坐标系中。

### 需要标定的转换

1. **D455 → 机器人基座**：
   - 已完成手眼标定
   - 标定文件：`/home/cothink/.ros/easy_handeye/baxter_d455_handeye_calibration_eye_on_base.yaml`
   - 需要在代码中加载并应用此转换

2. **头部相机 → 机器人基座**：
   - 头部相机位置固定
   - 可以通过测量或标定获得转换矩阵
   - 或者直接使用TF树查询

3. **手腕相机 → 机器人基座**：
   - 手腕相机位置随机械臂移动
   - 可以通过正向运动学计算
   - 或者使用TF树实时查询

### TODO：集成标定数据

```python
# 需要添加到 MultiViewVLMCoordinator
def _load_camera_calibration(self):
    """加载相机标定数据"""
    # 加载D455手眼标定
    calib_file = "/home/cothink/.ros/easy_handeye/baxter_d455_handeye_calibration_eye_on_base.yaml"
    # 解析转换矩阵
    # 应用到深度相机的3D点

def _transform_camera_to_base(self, point_3d, camera_type):
    """将相机坐标系的点转换到机器人基座坐标系"""
    # 应用相应的转换矩阵
    pass
```

## 已知问题和改进方向

### 1. 头部相机倾斜角度

**问题**：头部相机不是正俯视，而是有一定倾斜角度

**影响**：
- 图像中桌面只占一部分
- 透视畸变较大
- 距离估计可能不准确

**改进方案**：
- 对头部相机图像进行透视变换，校正为正俯视
- 或者在VLM提示词中说明相机角度
- 或者降低头部相机的权重，主要用于验证

### 2. 相机同步

**问题**：不同相机采集时间略有差异

**影响**：
- 如果场景中有移动物体，可能导致不一致
- 机械臂移动时可能产生运动模糊

**改进方案**：
- 确保机械臂静止后再采集
- 添加时间戳同步
- 考虑使用硬件触发同步（如果支持）

### 3. VLM提示词优化

**当前**：使用通用提示词

**改进方向**：
- 针对不同阶段使用不同提示词
- 阶段1：强调"快速识别"和"大致位置"
- 阶段2：强调"精确定位"和"细节特征"
- 多视角融合时，明确告诉VLM这是同一物体的不同视角

### 4. 置信度融合策略

**当前**：简单平均或规则判断

**改进方向**：
- 基于贝叶斯融合
- 考虑每个视角的可靠性权重
- 根据物体类型动态调整权重

## 实验建议

### 测试场景

1. **简单场景**：单个明显物体（如红色杯子）
2. **复杂场景**：多个相似物体
3. **遮挡场景**：部分遮挡的物体
4. **小物体**：<5cm的物体（测试精度）

### 评估指标

1. **定位精度**：与真实位置的误差（使用标定板或已知位置物体）
2. **置信度准确性**：高置信度是否对应高精度
3. **成功率**：找到物体的比例
4. **耗时**：完整流程的时间
5. **多视角一致性**：不同视角结果的差异

### 对比实验

- 单视角（仅D455）vs 多视角
- 有/无手腕精确定位
- 有/无深度增强
- 不同VLM提供商（Claude vs Qwen vs GPT-4V）

## 参考资料

- [Baxter相机限制](https://nu-msr.github.io/ros_notes/ros1/lecture13_rethink.html)
- 手眼标定结果：`/home/cothink/.ros/easy_handeye/baxter_d455_handeye_calibration_eye_on_base.yaml`
- VLM客户端：[bridge/vlm_client.py](bridge/vlm_client.py)
- 深度相机驱动：[bridge/drivers/realsense_driver.py](bridge/drivers/realsense_driver.py)
