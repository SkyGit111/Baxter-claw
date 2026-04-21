# VLM+D455 定位校准偏移量应用

## 测试数据（8次测试）

### 偏移量统计
- **X轴**: +13.29 cm ± 0.69 cm ✅ **稳定**
- **Y轴**: -26.44 cm ± 0.66 cm ✅ **稳定**
- **Z轴**: -6.01 cm ± 6.19 cm ⚠️ **不稳定**

### 平均偏移距离
- 30.81 cm ± 1.33 cm

### 偏移范围
- 最大: 32.81 cm
- 最小: 29.18 cm

## 校准策略

### X、Y轴
- **使用测试平均值**：X = +0.1329 m, Y = -0.2644 m
- **原因**：标准差 < 1cm，偏移非常稳定

### Z轴
- **使用保守值**：Z = -0.05 m
- **原因**：
  1. 标准差 6.19 cm，不稳定
  2. 对抓取影响小（物体高度 < 夹爪长度）
  3. 夹爪下探到接近桌面（约 -0.15m）即可抓取
  4. 保守偏移避免过度补偿

## 实现位置

**文件**: `bridge/multi_view_vlm.py`

### 1. 初始化校准偏移量

```python
def __init__(self, driver, vlm_client, safety_validator, debug=False):
    # ...
    
    # Calibration offset (from empirical testing)
    # Based on 8 test samples:
    # X: +13.29 cm ± 0.69 cm (stable)
    # Y: -26.44 cm ± 0.66 cm (stable)
    # Z: -6.01 cm ± 6.19 cm (unstable, use conservative -5 cm)
    self.calibration_offset = np.array([0.1329, -0.2644, -0.05])
    print(f"[MultiView] Calibration offset: {self.calibration_offset}")
```

### 2. 应用校准偏移量

在 `_capture_and_analyze_d455()` 方法中，坐标转换后立即应用：

```python
# 坐标转换：相机坐标系 → 基座坐标系
position_base = self.transforms.transform_d455_to_base(position_camera)

if position_base is not None:
    # 应用校准偏移量
    position_calibrated = position_base + self.calibration_offset
    
    result['position'] = position_calibrated.tolist()  # 校准后的位置
    result['position_raw'] = position_base.tolist()    # 原始位置（调试用）
    result['position_camera_frame'] = position_camera.tolist()
    result['coordinate_transformed'] = True
    result['calibration_applied'] = True
    
    print(f"  Position (base frame, raw): {position_base}")
    print(f"  Calibration offset: {self.calibration_offset}")
    print(f"  Position (base frame, calibrated): {position_calibrated}")
```

## 输出示例

```
[D455] Coordinate transformation:
  Position (camera frame): [0.6234, 0.1523, 0.8456]
  Position (base frame, raw): [0.7123, 0.2345, 0.1234]
  Calibration offset: [ 0.1329 -0.2644 -0.05  ]
  Position (base frame, calibrated): [0.8452, -0.0299, 0.0734]
  Transformation applied successfully
```

## 数据流

```
1. D455 捕获 RGB + Depth
   ↓
2. VLM 识别边界框
   ↓
3. 深度相机计算 3D 坐标（相机坐标系）
   position_camera = [0.6234, 0.1523, 0.8456]
   ↓
4. 坐标转换（相机 → 基座）
   position_base = [0.7123, 0.2345, 0.1234]
   ↓
5. 应用校准偏移 ✨ NEW
   position_calibrated = position_base + [0.1329, -0.2644, -0.05]
                       = [0.8452, -0.0299, 0.0734]
   ↓
6. 返回校准后的位置
   result['position'] = [0.8452, -0.0299, 0.0734]
```

## 预期效果

### 校准前
- 平均偏移：30.81 cm
- X轴偏移：+13.29 cm
- Y轴偏移：-26.44 cm
- Z轴偏移：-6.01 cm

### 校准后（预期）
- 平均偏移：< 5 cm
- X轴偏移：< 1 cm（标准差范围内）
- Y轴偏移：< 1 cm（标准差范围内）
- Z轴偏移：< 7 cm（Z轴本身不稳定 + 保守补偿）

## 验证方法

### 1. 运行测试脚本
```bash
python test_vlm_localization_accuracy.py
```

### 2. 观察输出
查看校准后的偏移量是否显著减小：
```
📊 偏移量分析
======================================================================
  X 轴偏移: +0.0050 m (+0.50 cm)  ← 应该接近 0
  Y 轴偏移: -0.0080 m (-0.80 cm)  ← 应该接近 0
  Z 轴偏移: -0.0120 m (-1.20 cm)  ← 可能仍有偏差
  总偏移距离: 0.0150 m (1.50 cm)  ← 应该 < 5 cm
```

### 3. 实际抓取测试
- 测试不同位置的物体抓取
- 观察成功率是否提高

## 调试信息

### 查看原始位置 vs 校准位置
```python
result['position_raw']        # 原始位置（未校准）
result['position']            # 校准后位置
result['calibration_applied'] # True 表示已应用校准
```

### 调试图像
校准后的位置会显示在调试图像上：
- `debug_d455_phase1_annotated.jpg`

## 注意事项

### 1. 校准偏移量的有效性
- 基于特定环境和设置
- 如果改变了：
  - D455 安装位置
  - 手眼标定参数
  - 工作区域
- 需要重新测试和校准

### 2. Z轴偏移的保守性
- Z轴使用 -5cm 而不是测试平均值 -6.01cm
- 原因：Z轴标准差大（6.19cm），不稳定
- 对抓取影响小，保守补偿更安全

### 3. 持续监控
- 定期运行测试脚本验证偏移量
- 如果偏移量变化，更新校准值

## 如何更新校准值

如果需要更新校准偏移量：

1. 运行测试脚本收集新数据
2. 计算新的平均偏移量
3. 修改 `bridge/multi_view_vlm.py`:
   ```python
   self.calibration_offset = np.array([new_x, new_y, new_z])
   ```
4. 重启 Bridge Server
5. 验证新的校准效果

## 测试数据记录

**测试日期**: 2026-04-20
**测试物体**: 蓝色小方块
**测试次数**: 8
**测试位置**: 桌面不同位置

**原始数据**: `vlm_localization_test_YYYYMMDD_HHMMSS.csv`

## 总结

✅ **已实现**：
1. 基于 8 次测试的校准偏移量
2. 自动应用到所有 D455 定位结果
3. 保留原始位置用于调试
4. 详细的日志输出

✅ **预期改进**：
- 定位精度从 30.81 cm 提升到 < 5 cm
- X、Y轴精度提升到 < 1 cm
- 抓取成功率显著提高

⚠️ **注意**：
- Z轴仍可能有偏差（不稳定）
- 但对抓取影响小（夹爪下探策略）
