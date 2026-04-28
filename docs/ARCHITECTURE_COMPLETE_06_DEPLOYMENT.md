# Baxter-Claw 完整架构文档 - 第6节：部署和测试

## 6. 部署和测试

### 6.1 系统部署

#### 6.1.1 环境要求

**硬件要求**：
- Baxter Research Robot
- Intel RealSense D455 深度相机
- 工作站（Ubuntu 20.04）
- 网络连接（机器人和工作站在同一局域网）

**软件要求**：
- ROS Noetic
- Python 3.8+
- Conda 环境管理
- 必要的 Python 包（见 requirements.txt）

#### 6.1.2 安装步骤

**1. 克隆仓库**
```bash
git clone https://github.com/SkyGit111/Baxter-claw.git
cd Baxter-claw
```

**2. 创建 Conda 环境**
```bash
conda create -n baxter-claw python=3.8
conda activate baxter-claw
```

**3. 安装依赖**
```bash
pip install -r requirements.txt
```

**4. 配置 ROS 环境**
```bash
cd ~/catkin_ws
source devel/setup.bash
./baxter.sh  # 连接到 Baxter
```

**5. 配置 API 密钥**
```bash
export QWEN_API_KEY="your_qwen_api_key"
# 或在 config/baxter.yaml 中配置
```

**6. 校准深度相机（首次使用）**
```bash
# 使用 easy_handeye 进行 hand-eye 标定
roslaunch easy_handeye calibrate.launch
```

#### 6.1.3 启动系统

**方式 1：标准启动**
```bash
# Terminal 1: 启动 Bridge Server
python start_server.py

# Terminal 2: 启动 Web 界面
python openclaw_plugin/web_interface.py

# 浏览器访问: http://localhost:5000
```

**方式 2：启用实验性功能**
```bash
# 启用抓取验证
python start_server.py --enable-grasp-verification --grasp-verify-retries 3

# 启用碰撞检测（需修改配置文件）
# 编辑 config/baxter.yaml:
#   experimental:
#     collision_detection:
#       enabled: true
```

**方式 3：使用配置文件**
```bash
python start_server.py --config config/baxter.yaml
```

### 6.2 测试框架

#### 6.2.1 测试层次

```
单元测试 (Unit Tests)
    ├─ test_primitives.py      # 动作原语测试
    ├─ test_safety.py           # 安全验证测试
    ├─ test_mock_driver.py      # 驱动层测试
    └─ test_bridge_api.py       # API 测试

集成测试 (Integration Tests)
    ├─ test_dualarm.py          # 双臂协同测试
    └─ run_system_test.py       # 系统集成测试

端到端测试 (E2E Tests)
    ├─ examples/test_primitives.py
    ├─ examples/vision_demo.py
    └─ examples/dualarm_demo.py
```

#### 6.2.2 单元测试示例

**test_primitives.py**
```python
import pytest
from bridge.primitives import BaxterPrimitives
from bridge.drivers.mock_driver import MockDriver
from bridge.safety import SafetyValidator

@pytest.fixture
def primitives():
    driver = MockDriver()
    safety = SafetyValidator()
    return BaxterPrimitives(driver, safety)

def test_pick_basic(primitives):
    """测试基础抓取"""
    result = primitives.pick(
        arm='right',
        position=[0.6, 0.0, 0.0],
        approach_height=0.1,
        speed=0.3
    )
    assert result['success'] == True

def test_pick_out_of_workspace(primitives):
    """测试工作空间外抓取"""
    result = primitives.pick(
        arm='right',
        position=[2.0, 0.0, 0.0],  # 超出范围
        approach_height=0.1,
        speed=0.3
    )
    assert result['success'] == False
    assert 'unsafe' in result['message'].lower()

def test_home_position(primitives):
    """测试回原位"""
    result = primitives.home(arm='right')
    assert result['success'] == True
```

#### 6.2.3 系统测试

**run_system_test.py**
```python
#!/usr/bin/env python
"""系统集成测试"""

import asyncio
from bridge.arm_manager import ArmManager

async def test_full_workflow():
    """测试完整工作流"""
    print("="*60)
    print("Baxter-Claw 系统测试")
    print("="*60)
    
    # 1. 初始化
    manager = ArmManager(config_path='config/baxter.yaml')
    assert manager.connect(), "连接失败"
    assert manager.enable(), "使能失败"
    
    # 2. 测试基础动作
    print("\n[Test 1] 回到原位")
    result = manager.primitives.home(arm='both')
    assert result['success'], f"Home 失败: {result['message']}"
    
    # 3. 测试视觉定位
    print("\n[Test 2] 定位物体")
    result = await manager.primitives.locate_object(
        object_name='blue cube',
        use_d455=True
    )
    assert result['success'], f"定位失败: {result['message']}"
    print(f"  位置: {result['position']}")
    
    # 4. 测试抓取
    print("\n[Test 3] 抓取物体")
    result = await manager.primitives.pick_by_name(
        arm='auto',
        object_name='blue cube',
        use_d455=True
    )
    assert result['success'], f"抓取失败: {result['message']}"
    
    # 5. 测试放置
    print("\n[Test 4] 放置物体")
    result = manager.primitives.place(
        arm='right',
        position=[0.6, -0.3, 0.0]
    )
    assert result['success'], f"放置失败: {result['message']}"
    
    # 6. 清理
    manager.primitives.home(arm='both')
    manager.disable()
    
    print("\n" + "="*60)
    print("✓ 所有测试通过")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_full_workflow())
```

### 6.3 性能指标

#### 6.3.1 响应时间

| 操作 | 平均时间 | 说明 |
|------|---------|------|
| 连接机器人 | ~2s | 初始化 ROS 节点和接口 |
| 使能机器人 | ~1s | 激活电机 |
| 回到原位 | ~3-5s | 取决于当前位置 |
| 视觉定位 | ~2-3s | D455 + VLM |
| 抓取动作 | ~8-12s | 包含定位、移动、抓取 |
| 放置动作 | ~5-8s | 移动和释放 |
| 完整 pick-and-place | ~15-25s | 端到端 |

#### 6.3.2 成功率

| 任务 | 成功率 | 条件 |
|------|--------|------|
| 基础运动 | >99% | 工作空间内 |
| 视觉定位 | ~90% | 常见物体，良好光照 |
| 抓取 | ~85% | 规则物体，无遮挡 |
| 放置 | >95% | 已知位置 |
| 端到端任务 | ~75% | 完整流程 |

#### 6.3.3 资源占用

- **CPU**: 20-40% (单核)
- **内存**: ~2GB
- **网络**: <1MB/s (VLM API 调用)
- **GPU**: 不需要（VLM 在云端）

### 6.4 故障排查

#### 6.4.1 常见问题

**问题 1: 无法连接机器人**
```
错误: Failed to connect to Baxter
```
解决：
1. 检查网络连接：`ping baxter.local`
2. 确认 ROS 环境：`echo $ROS_MASTER_URI`
3. 运行 baxter.sh：`cd ~/catkin_ws && ./baxter.sh`

**问题 2: 夹爪无法控制**
```
错误: Unable to command gripper until calibrated
```
解决：
1. 重启 Bridge Server（会自动校准）
2. 或手动校准：
```python
from baxter_interface import Gripper
gripper = Gripper('right')
gripper.calibrate()
```

**问题 3: 相机图像获取失败**
```
错误: Failed to capture from d455
```
解决：
1. 检查相机连接：`rs-enumerate-devices`
2. 重启相机：拔插 USB
3. 检查权限：`sudo chmod 666 /dev/video*`

**问题 4: VLM 定位不准确**
```
结果: 物体位置偏移 10cm+
```
解决：
1. 检查校准文件是否存在
2. 重新进行 hand-eye 标定
3. 调整校准偏移量（primitives.py）

**问题 5: 抓取失败**
```
错误: Failed to reach target
```
解决：
1. 检查物体是否在工作空间内
2. 检查 Z 坐标（可能太低）
3. 尝试手动指定手臂：`arm='right'`

#### 6.4.2 调试工具

**1. 日志级别**
```python
# 在 start_server.py 中
import logging
logging.basicConfig(level=logging.DEBUG)
```

**2. 保存调试图像**
```python
# 启用 debug 模式
manager = ArmManager(
    config_path='config/baxter.yaml',
    enable_grasp_verification=True  # 会自动保存图像
)
```

**3. 查看相机图像**
```bash
# 实时查看 D455
python -c "from bridge.drivers.realsense_driver import RealSenseDriver; import cv2; d=RealSenseDriver(); rgb,_=d.capture_rgbd(); cv2.imshow('D455', rgb); cv2.waitKey(0)"

# 通过 API 查看
curl http://localhost:8420/camera?camera=d455 > test.jpg
```

### 6.5 最佳实践

#### 6.5.1 开发建议

1. **先用 MockDriver 测试**
   - 避免频繁操作真机
   - 快速验证逻辑

2. **分层测试**
   - 单元测试 → 集成测试 → 真机测试
   - 逐步验证功能

3. **使用配置文件**
   - 不要硬编码参数
   - 便于不同环境切换

4. **记录实验数据**
   - 保存成功/失败的案例
   - 持续优化参数

#### 6.5.2 生产部署

1. **安全第一**
   - 始终在监督下运行
   - 设置紧急停止按钮
   - 定期检查工作空间

2. **性能优化**
   - 使用本地 VLM（如果可能）
   - 缓存常见物体位置
   - 批量处理任务

3. **监控和日志**
   - 记录所有操作
   - 监控成功率
   - 定期备份配置

4. **维护计划**
   - 定期校准相机
   - 检查夹爪磨损
   - 更新软件依赖

### 6.6 扩展开发

#### 6.6.1 添加新技能

1. 在 `skills.md` 中定义技能
2. 在 `baxter_claw_plugin.py` 中实现执行方法
3. 测试并文档化

示例：
```python
# 1. skills.md
## Skill 11: pour_liquid
**Description**: Pour liquid from one container to another
**Parameters**:
- source_container (string): Container to pour from
- target_container (string): Container to pour into

# 2. baxter_claw_plugin.py
def _execute_pour_liquid(self, params: Dict) -> Dict:
    source = params['source_container']
    target = params['target_container']
    
    # 实现倾倒逻辑
    # ...
```

#### 6.6.2 集成新传感器

1. 创建新的 Driver 类
2. 实现必要的接口
3. 在 ArmManager 中集成

#### 6.6.3 支持新 LLM

1. 在 `vlm_client.py` 中添加提供商
2. 实现 API 调用逻辑
3. 测试兼容性

---

## 7. 总结

### 7.1 系统特点

**优势**：
- ✅ 完整的分层架构，易于维护
- ✅ 自然语言控制，降低使用门槛
- ✅ 视觉引导操作，精确定位
- ✅ 多层安全保障
- ✅ 可扩展的技能系统

**局限**：
- ⚠️ 依赖云端 VLM（网络延迟）
- ⚠️ 小物体识别困难
- ⚠️ 复杂场景成功率下降
- ⚠️ 需要良好光照条件

### 7.2 未来方向

1. **本地 VLM 部署**
   - 减少网络延迟
   - 提高隐私性

2. **更精确的抓取**
   - 力反馈控制
   - 触觉传感器

3. **复杂任务规划**
   - 多步骤任务分解
   - 动态重规划

4. **学习和适应**
   - 从失败中学习
   - 个性化调整

### 7.3 参考资源

**文档**：
- [README.md](../README.md) - 项目主文档
- [QUICKSTART.md](../QUICKSTART.md) - 快速开始
- [ARCHITECTURE_SWITCH.md](../ARCHITECTURE_SWITCH.md) - 架构切换
- [GRASP_VERIFICATION.md](../GRASP_VERIFICATION.md) - 抓取验证

**代码**：
- [bridge/](../bridge/) - 核心代码
- [openclaw_plugin/](../openclaw_plugin/) - 插件代码
- [examples/](../examples/) - 示例代码

**社区**：
- GitHub: https://github.com/SkyGit111/Baxter-claw
- Issues: 报告问题和建议

---

**完整架构文档结束**

本文档涵盖了 Baxter-Claw 项目的完整架构、技术细节和使用指南。
如有疑问，请参考各节详细内容或提交 Issue。
