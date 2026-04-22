# Baxter 真机连接完整方案

## 📋 当前环境状态

### ✅ 已确认
- Baxter IP: 192.168.1.100 (011A08P0014.local)
- 网络连接正常（ping 成功）
- D455 深度相机已连接
- ROS Noetic 已安装
- baxter.sh 脚本存在于 ~/catkin_ws/

### ⚠️ 需要配置
- Baxter 机器人需要开机并启动
- RealSense SDK (pyrealsense2) 需要安装
- Bridge Server 需要切换到 Baxter 驱动
- 深度相机集成需要实现

---

## 🎯 完整工作清单

### 阶段 1: Baxter 机器人准备（需要你手动完成）

#### ✋ 任务 1.1: 启动 Baxter 机器人
**需要你做：**
- [ ] 确认 Baxter 机器人已开机
- [ ] 确认紧急停止按钮未按下
- [ ] 等待 Baxter 完全启动（约 2-3 分钟）
- [ ] 确认 Baxter 屏幕显示正常

#### ✋ 任务 1.2: 测试 ROS 连接
**需要你做：**
```bash
cd ~/catkin_ws
./baxter.sh
rostopic list
```

**预期结果：**
应该看到 Baxter 的话题列表，例如：
```
/robot/state
/robot/limb/right/endpoint_state
/robot/limb/left/endpoint_state
...
```

**如果看不到话题：**
- 检查 Baxter 是否完全启动
- 检查网络连接
- 重新运行 `./baxter.sh`

---

### 阶段 2: 安装 RealSense SDK（我来完成）

#### 🤖 任务 2.1: 安装 pyrealsense2
```bash
source /home/cothink/miniconda3/etc/profile.d/conda.sh
conda activate baxter-claw
pip install pyrealsense2
```

#### 🤖 任务 2.2: 测试 D455 连接
```python
import pyrealsense2 as rs
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)
frames = pipeline.wait_for_frames()
print(f"✓ D455 连接成功")
print(f"  Depth: {frames.get_depth_frame().get_width()}x{frames.get_depth_frame().get_height()}")
print(f"  Color: {frames.get_color_frame().get_width()}x{frames.get_color_frame().get_height()}")
pipeline.stop()
```

---

### 阶段 3: 创建深度相机驱动（我来完成）

#### 🤖 任务 3.1: 创建 RealSense 驱动类
**文件：** `bridge/drivers/realsense_driver.py`

**功能：**
```python
class RealSenseDriver:
    def __init__(self):
        # 初始化 D455
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        # 配置流
        
    def capture_rgbd(self):
        # 捕获 RGB + 深度图像
        return rgb_image, depth_image
    
    def deproject_pixel_to_point(self, x, y, depth):
        # 将 2D 像素 + 深度转换为 3D 坐标
        return [x_3d, y_3d, z_3d]
```

#### 🤖 任务 3.2: 修改 VLM 客户端支持深度
**文件：** `bridge/vlm_client.py`

**新增方法：**
```python
async def locate_object_with_depth(
    self,
    rgb_image: bytes,
    depth_image: np.ndarray,
    object_name: str,
    camera_intrinsics
) -> Dict:
    # 1. VLM 识别物体（2D 边界框）
    bbox = await self.locate_object(rgb_image, object_name)
    
    # 2. 从深度图获取真实深度
    center_x = (bbox['bounding_box'][0] + bbox['bounding_box'][2]) // 2
    center_y = (bbox['bounding_box'][1] + bbox['bounding_box'][3]) // 2
    depth = depth_image[center_y, center_x]
    
    # 3. 转换为 3D 坐标
    real_3d = deproject_pixel_to_point(center_x, center_y, depth, camera_intrinsics)
    
    return {
        'found': True,
        'position': real_3d,  # 真实 3D 坐标！
        'confidence': 95,  # 深度数据可靠
        'bounding_box': bbox['bounding_box']
    }
```

#### 🤖 任务 3.3: 修改 Baxter 驱动集成深度相机
**文件：** `bridge/drivers/baxter_driver.py`

**修改：**
```python
from .realsense_driver import RealSenseDriver

class BaxterDriver(ArmDriver):
    def __init__(self, use_depth_camera=False):
        # 原有初始化
        self.limb_right = baxter_interface.Limb('right')
        self.gripper_right = baxter_interface.Gripper('right')
        
        # 新增：深度相机
        if use_depth_camera:
            self.depth_camera = RealSenseDriver()
        else:
            self.depth_camera = None
    
    def capture_image(self, camera: str) -> bytes:
        if self.depth_camera and camera == "depth":
            # 返回 RGB + 深度
            return self.depth_camera.capture_rgbd()
        else:
            # 原有的 Baxter 相机逻辑
            return self._capture_baxter_camera(camera)
```

---

### 阶段 4: 修改配置文件（我来完成）

#### 🤖 任务 4.1: 更新 baxter.yaml
```yaml
driver:
  type: "baxter"  # 从 mock 改为 baxter
  use_depth_camera: true  # 启用深度相机

vlm:
  enabled: true
  provider: "qwen"
  api_key: "sk-bd990626c84a4142b9581f13c5317522"
  use_depth: true  # 使用深度数据增强

depth_camera:
  enabled: true
  type: "realsense"
  model: "D455"
  resolution:
    width: 640
    height: 480
  fps: 30
  
# Baxter 相机配置
baxter_cameras:
  right_hand: "/cameras/right_hand_camera/image"
  left_hand: "/cameras/left_hand_camera/image"
  head: "/cameras/head_camera/image"
```

#### 🤖 任务 4.2: 创建启动脚本
**文件：** `start_with_baxter.sh`

```bash
#!/bin/bash
# Baxter 真机启动脚本

echo "=========================================="
echo "Baxter-Claw 真机启动"
echo "=========================================="

# 1. Source Baxter 环境
echo "1. 配置 Baxter 环境..."
cd ~/catkin_ws
source ./baxter.sh

# 2. 激活 conda 环境
echo "2. 激活 conda 环境..."
source /home/cothink/miniconda3/etc/profile.d/conda.sh
conda activate baxter-claw

# 3. 返回项目目录
cd /home/cothink/Baxter-claw

# 4. 测试 ROS 连接
echo "3. 测试 ROS 连接..."
if rostopic list > /dev/null 2>&1; then
    echo "   ✓ ROS 连接正常"
else
    echo "   ✗ ROS 连接失败"
    echo "   请确认 Baxter 已启动"
    exit 1
fi

# 5. 启动 Bridge Server
echo "4. 启动 Bridge Server..."
python -m bridge.server --config config/baxter.yaml &

sleep 3

# 6. 测试 Bridge Server
echo "5. 测试 Bridge Server..."
if curl -s http://localhost:8420/health > /dev/null; then
    echo "   ✓ Bridge Server 启动成功"
else
    echo "   ✗ Bridge Server 启动失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "启动完成！"
echo "=========================================="
echo ""
echo "Bridge Server: http://localhost:8420"
echo "Baxter IP: 192.168.1.100"
echo ""
```

---

### 阶段 5: 测试连接（逐步验证）

#### 🤖 任务 5.1: 创建连接测试脚本
**文件：** `test_baxter_connection.py`

```python
#!/usr/bin/env python3
"""测试 Baxter 真机连接"""

import sys
import rospy
import baxter_interface
import pyrealsense2 as rs

def test_ros_connection():
    """测试 ROS 连接"""
    print("测试 1: ROS 连接...")
    try:
        rospy.init_node('test_connection', anonymous=True)
        print("  ✓ ROS 节点初始化成功")
        return True
    except Exception as e:
        print(f"  ✗ ROS 连接失败: {e}")
        return False

def test_baxter_interface():
    """测试 Baxter 接口"""
    print("\n测试 2: Baxter 接口...")
    try:
        # 测试右臂
        limb = baxter_interface.Limb('right')
        angles = limb.joint_angles()
        print(f"  ✓ 右臂连接成功")
        print(f"    关节角度: {list(angles.keys())[:3]}...")
        
        # 测试夹爪
        gripper = baxter_interface.Gripper('right')
        print(f"  ✓ 右夹爪连接成功")
        print(f"    夹爪位置: {gripper.position():.2f}mm")
        
        return True
    except Exception as e:
        print(f"  ✗ Baxter 接口失败: {e}")
        return False

def test_realsense():
    """测试 RealSense D455"""
    print("\n测试 3: RealSense D455...")
    try:
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        
        pipeline.start(config)
        frames = pipeline.wait_for_frames()
        
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        
        print(f"  ✓ D455 连接成功")
        print(f"    深度图: {depth_frame.get_width()}x{depth_frame.get_height()}")
        print(f"    彩色图: {color_frame.get_width()}x{color_frame.get_height()}")
        
        pipeline.stop()
        return True
    except Exception as e:
        print(f"  ✗ D455 连接失败: {e}")
        return False

def main():
    print("=" * 60)
    print("  Baxter 真机连接测试")
    print("=" * 60)
    
    results = []
    results.append(("ROS 连接", test_ros_connection()))
    results.append(("Baxter 接口", test_baxter_interface()))
    results.append(("RealSense D455", test_realsense()))
    
    print("\n" + "=" * 60)
    print("  测试结果")
    print("=" * 60)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n✓ 所有测试通过！可以开始控制 Baxter。")
        return 0
    else:
        print(f"\n✗ {total - passed} 个测试失败，请检查配置。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

### 阶段 6: 执行简单抓取任务

#### 🤖 任务 6.1: 创建真机测试脚本
**文件：** `test_real_baxter_grasp.py`

```python
#!/usr/bin/env python3
"""Baxter 真机抓取测试"""

import requests
import time

BASE_URL = "http://localhost:8420"

def test_enable():
    """启用机器人"""
    print("\n测试 1: 启用机器人...")
    print("⚠️  机器人即将启用，确保工作空间安全")
    input("按 Enter 继续...")
    
    response = requests.post(f"{BASE_URL}/enable")
    data = response.json()
    print(f"  结果: {data.get('message')}")
    return data.get('success')

def test_home():
    """回到初始位置"""
    print("\n测试 2: 回到初始位置...")
    response = requests.post(
        f"{BASE_URL}/primitives/home",
        json={"arm": "right"}
    )
    data = response.json()
    print(f"  结果: {data.get('message')}")
    return data.get('success')

def test_small_move():
    """小幅度移动"""
    print("\n测试 3: 小幅度移动...")
    print("  目标位置: [0.6, -0.3, 0.2]")
    
    response = requests.post(
        f"{BASE_URL}/primitives/move_to",
        json={
            "arm": "right",
            "position": [0.6, -0.3, 0.2],
            "orientation": [0, 0, 0]
        }
    )
    data = response.json()
    print(f"  结果: {data.get('message')}")
    return data.get('success')

def test_gripper():
    """测试夹爪"""
    print("\n测试 4: 测试夹爪...")
    
    # 打开
    print("  打开夹爪...")
    requests.post(f"{BASE_URL}/gripper/open", json={"arm": "right"})
    time.sleep(1)
    
    # 关闭
    print("  关闭夹爪...")
    requests.post(f"{BASE_URL}/gripper/close", json={"arm": "right", "force": 30.0})
    time.sleep(1)
    
    print("  ✓ 夹爪测试完成")
    return True

def test_pick_with_coordinates():
    """使用精确坐标抓取"""
    print("\n测试 5: 使用精确坐标抓取...")
    print("⚠️  请在以下位置放置物体：")
    print("   X: 0.65m (前方 65cm)")
    print("   Y: -0.25m (右侧 25cm)")
    print("   Z: 0.02m (桌面上方 2cm)")
    print()
    print("   建议物体：轻质、易抓取、5-10cm 大小")
    
    input("物体已放置？按 Enter 继续...")
    
    response = requests.post(
        f"{BASE_URL}/primitives/pick",
        json={
            "arm": "right",
            "position": [0.65, -0.25, 0.02],
            "approach_height": 0.1
        }
    )
    data = response.json()
    print(f"  结果: {data.get('message')}")
    
    if data.get('success'):
        print("\n  ✓ 抓取成功！")
        print("  现在测试放置...")
        time.sleep(2)
        
        # 放置
        response = requests.post(
            f"{BASE_URL}/primitives/place",
            json={
                "arm": "right",
                "position": [0.55, -0.35, 0.02],
                "approach_height": 0.1
            }
        )
        data = response.json()
        print(f"  放置结果: {data.get('message')}")
    
    return data.get('success')

def main():
    print("=" * 60)
    print("  Baxter 真机抓取测试")
    print("=" * 60)
    print()
    print("⚠️  安全提醒：")
    print("   1. 确保工作空间内无人")
    print("   2. 保持紧急停止按钮可用")
    print("   3. 随时准备按下紧急停止")
    print()
    
    input("准备好开始测试？按 Enter 继续...")
    
    tests = [
        test_enable,
        test_home,
        test_small_move,
        test_gripper,
        test_pick_with_coordinates,
    ]
    
    for test_func in tests:
        try:
            success = test_func()
            if not success:
                print(f"\n⚠️  测试失败")
                if input("继续下一个测试？(y/n): ").lower() != 'y':
                    break
            time.sleep(1)
        except Exception as e:
            print(f"\n✗ 测试出错: {e}")
            break
    
    # 返回初始位置
    print("\n返回初始位置...")
    requests.post(f"{BASE_URL}/primitives/home", json={"arm": "right"})
    
    print("\n测试完成！")

if __name__ == "__main__":
    main()
```

---

## 📊 工作分配总结

### 🙋 你需要手动完成（约 10 分钟）

| 任务 | 命令 | 预计时间 |
|------|------|---------|
| 1. 确认 Baxter 开机 | 物理检查 | 2 分钟 |
| 2. 测试 ROS 连接 | `cd ~/catkin_ws && ./baxter.sh && rostopic list` | 3 分钟 |
| 3. 告诉我结果 | 复制输出 | 1 分钟 |
| 4. 放置测试物体 | 物理操作 | 5 分钟 |

### 🤖 我会自动完成（约 30 分钟）

| 任务 | 说明 | 预计时间 |
|------|------|---------|
| 1. 安装 pyrealsense2 | pip install | 2 分钟 |
| 2. 创建 RealSense 驱动 | 编写代码 | 10 分钟 |
| 3. 修改 VLM 客户端 | 集成深度 | 10 分钟 |
| 4. 修改 Baxter 驱动 | 集成深度相机 | 5 分钟 |
| 5. 更新配置文件 | 修改 yaml | 2 分钟 |
| 6. 创建测试脚本 | 编写测试代码 | 5 分钟 |
| 7. 重启 Bridge Server | 应用配置 | 2 分钟 |

---

## 🎯 下一步行动

### 现在请你完成：

**步骤 1: 确认 Baxter 已启动**
```bash
# 物理检查 Baxter 是否开机
# 等待完全启动（约 2-3 分钟）
```

**步骤 2: 测试 ROS 连接**
```bash
cd ~/catkin_ws
./baxter.sh
rostopic list
```

**步骤 3: 告诉我结果**
- 能看到 `/robot/...` 话题吗？
- 有任何错误信息吗？
- 复制 `rostopic list` 的输出

**完成这些后，我会立即：**
1. 安装 pyrealsense2
2. 创建深度相机驱动
3. 修改代码集成深度数据
4. 创建测试脚本
5. 启动真机测试

---

**准备好了吗？请先确认 Baxter 已启动，然后运行上面的命令！**