# Baxter-Claw 真机测试完整指南

## 项目架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    用户交互层                                 │
│  - Web界面 (web_interface.py)                               │
│  - OpenClaw Plugin (baxter_claw_plugin.py)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/REST API
┌─────────────────────▼───────────────────────────────────────┐
│              Bridge Server (FastAPI)                         │
│  - server.py: REST API端点                                   │
│  - arm_manager.py: 机器人生命周期管理                        │
│  - primitives.py: 高级动作原语                               │
│  - safety.py: 安全验证                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌───▼────────┐ ┌─▼──────────┐
│ BaxterDriver │ │ VLMClient  │ │ RealSense  │
│ (ROS/SDK)    │ │ (Qwen)     │ │ D455       │
└──────────────┘ └────────────┘ └────────────┘
        │
┌───────▼──────────────────────────────────────┐
│         Baxter Robot (真机)                   │
│  - 双臂控制                                   │
│  - 夹爪控制                                   │
│  - 关节/末端位姿反馈                          │
└───────────────────────────────────────────────┘
```

## 系统组件说明

### 1. Bridge Server (核心服务)
- **位置**: `bridge/server.py`
- **功能**: 提供REST API，协调各组件
- **端口**: 8420
- **依赖**: 
  - ROS Noetic
  - Baxter SDK
  - FastAPI/Uvicorn

### 2. Baxter Driver
- **位置**: `bridge/drivers/baxter_driver.py`
- **功能**: 与Baxter机器人通信
- **依赖**: 
  - baxter_interface
  - rospy
  - ROS环境

### 3. RealSense D455 Driver
- **位置**: `bridge/drivers/realsense_driver.py`
- **功能**: 深度相机图像采集
- **依赖**: pyrealsense2

### 4. VLM Client
- **位置**: `bridge/vlm_client.py`
- **功能**: 视觉语言模型物体识别
- **支持**: Qwen-VL, Claude, GPT-4V

### 5. OpenClaw Plugin
- **位置**: `openclaw_plugin/baxter_claw_plugin.py`
- **功能**: LLM意图识别，自然语言控制
- **依赖**: Qwen API

### 6. Web界面
- **位置**: `openclaw_plugin/web_interface.py`
- **功能**: 浏览器控制界面
- **端口**: 5000
- **特性**: 语音输入、语音反馈、摄像头显示

## 前置条件检查清单

### 硬件要求
- [ ] Baxter机器人已开机并完全启动（约5分钟）
- [ ] Baxter显示屏显示正常
- [ ] RealSense D455摄像头已连接到工作站USB 3.0接口
- [ ] 工作站与Baxter在同一网络
- [ ] 急停按钮可触及

### 软件环境
- [ ] Ubuntu 18.04/20.04
- [ ] ROS Noetic已安装
- [ ] Baxter SDK已安装在 `~/catkin_ws`
- [ ] Conda环境 `baxter-claw` 已创建
- [ ] Python 3.8+

### 环境变量
```bash
# 检查ROS环境
echo $ROS_MASTER_URI  # 应指向Baxter的IP
echo $ROS_IP          # 应为工作站IP

# 检查Baxter连接
rostopic list | grep /robot/  # 应显示Baxter话题
```

### Python依赖
```bash
# 激活conda环境
conda activate baxter-claw

# 检查关键依赖
python -c "import fastapi; print('FastAPI OK')"
python -c "import uvicorn; print('Uvicorn OK')"
python -c "import httpx; print('HTTPX OK')"
python -c "import numpy; print('NumPy OK')"
python -c "import yaml; print('PyYAML OK')"
python -c "import pyrealsense2; print('RealSense OK')"
```

### API密钥
```bash
# 设置Qwen API密钥
export QWEN_API_KEY="your-api-key-here"

# 或在配置文件中设置
# config/baxter.yaml -> vlm.api_key
```

## 测试流程

### 阶段0: 环境准备

#### 步骤0.1: 配置ROS环境
```bash
cd ~/catkin_ws
source ./baxter.sh

# 验证连接
rostopic list | grep /robot/
rostopic echo /robot/state -n 1
```

#### 步骤0.2: 激活Python环境
```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate baxter-claw
cd ~/Baxter-claw
```

#### 步骤0.3: 检查硬件
```bash
# 检查RealSense
./check_baxter.sh

# 或手动检查
lsusb | grep 8086:0b5c  # D455摄像头
rs-enumerate-devices    # RealSense设备列表
```

#### 步骤0.4: 验证配置文件
```bash
cat config/baxter.yaml

# 确认以下配置:
# - driver.type: "baxter"
# - driver.use_depth_camera: true
# - vlm.enabled: true
# - vlm.provider: "qwen"
# - vlm.api_key: 已设置
```

---

### 阶段1: 基础连接测试

#### 测试1.1: ROS连接测试
```bash
python test_baxter_connection.py
```

**预期输出**:
```
✓ ROS环境已配置
✓ Baxter话题可访问
✓ 连接成功
```

**常见问题**:
- `ROS_MASTER_URI not set`: 运行 `source ~/catkin_ws/baxter.sh`
- `Unable to communicate with master`: 检查网络连接和Baxter IP

#### 测试1.2: 深度相机测试
```bash
python calibrate_depth_camera.py
```

**预期输出**:
```
✓ RealSense D455 已连接
✓ 图像流正常
保存测试图像: realsense_test_rgb.jpg, realsense_test_depth.jpg
```

**常见问题**:
- `No RealSense devices found`: 检查USB连接，尝试重新插拔
- `Permission denied`: 运行 `sudo chmod 666 /dev/bus/usb/*/*`

---

### 阶段2: Bridge Server启动测试

#### 测试2.1: 启动Bridge Server
```bash
# 方法1: 使用启动脚本（推荐）
./start_with_baxter.sh

# 方法2: 手动启动
python -m bridge.server
```

**预期输出**:
```
Starting Baxter-Claw Bridge Server...
Creating BaxterDriver (real hardware, depth_camera=True)
RealSense D455 depth camera initialized
Enhanced IK solver initialized
Creating VLM client (provider: qwen)
Successfully connected to Baxter robot
Bridge server ready
INFO:     Uvicorn running on http://0.0.0.0:8420
```

**验证服务**:
```bash
# 在新终端
curl http://localhost:8420/
curl http://localhost:8420/health
```

**常见问题**:
- `Address already in use`: 端口8420被占用，运行 `lsof -i :8420` 查找并关闭
- `Failed to connect to Baxter`: 检查ROS环境和Baxter状态
- `Could not initialize depth camera`: 检查RealSense连接

#### 测试2.2: API端点测试
```bash
# 获取状态
curl http://localhost:8420/status

# 使能机器人
curl -X POST http://localhost:8420/enable

# 检查健康状态
curl http://localhost:8420/health
```

---

### 阶段3: 基础运动控制测试

#### 测试3.1: 夹爪控制
```bash
# 在新终端（保持Bridge Server运行）
cd ~/Baxter-claw
conda activate baxter-claw

# 运行夹爪测试
python -c "
import httpx
client = httpx.Client(base_url='http://localhost:8420')

# 打开夹爪
print('打开夹爪...')
r = client.post('/primitives/gripper', json={'arm': 'right', 'command': 'open'})
print(r.json())

import time
time.sleep(2)

# 关闭夹爪
print('关闭夹爪...')
r = client.post('/primitives/gripper', json={'arm': 'right', 'command': 'close'})
print(r.json())
"
```

**预期行为**: 右臂夹爪打开然后关闭

#### 测试3.2: Home位置
```bash
python -c "
import httpx
client = httpx.Client(base_url='http://localhost:8420')

print('移动到Home位置...')
r = client.post('/primitives/home', json={'arm': 'right'})
print(r.json())
"
```

**预期行为**: 右臂移动到预定义的Home位置

#### 测试3.3: 坐标移动
```bash
python -c "
import httpx
client = httpx.Client(base_url='http://localhost:8420')

# 移动到安全测试位置
print('移动到测试位置...')
r = client.post('/primitives/move_to', json={
    'arm': 'right',
    'position': [0.6, -0.2, 0.0],
    'orientation': [0.0, 0.0, 0.0]
})
print(r.json())
"
```

**预期行为**: 右臂移动到指定坐标

**安全提示**: 
- 首次测试使用保守的坐标
- 确保工作空间内无障碍物
- 准备好急停按钮

---

### 阶段4: 视觉系统测试

#### 测试4.1: 图像采集
```bash
python -c "
import httpx
client = httpx.Client(base_url='http://localhost:8420', timeout=10.0)

print('采集图像...')
r = client.post('/camera/capture')
data = r.json()

if data['success']:
    print(f'✓ 图像采集成功')
    print(f'  分辨率: {data.get(\"width\")}x{data.get(\"height\")}')
    print(f'  时间戳: {data.get(\"timestamp\")}')
    
    # 保存图像
    import base64
    with open('test_capture.jpg', 'wb') as f:
        f.write(base64.b64decode(data['image']))
    print('  已保存: test_capture.jpg')
else:
    print(f'✗ 采集失败: {data.get(\"message\")}')
"
```

#### 测试4.2: VLM物体识别
```bash
# 在桌面放置一个明显的物体（如红色杯子）
python -c "
import httpx
import asyncio

async def test_vlm():
    async with httpx.AsyncClient(base_url='http://localhost:8420', timeout=30.0) as client:
        print('识别场景...')
        r = await client.post('/vision/describe_scene')
        data = r.json()
        
        if data['success']:
            print(f'✓ 场景描述:')
            print(f'  {data[\"description\"]}')
        else:
            print(f'✗ 识别失败: {data.get(\"message\")}')

asyncio.run(test_vlm())
"
```

#### 测试4.3: 物体定位
```bash
# 测试定位红色杯子
python -c "
import httpx
import asyncio

async def test_locate():
    async with httpx.AsyncClient(base_url='http://localhost:8420', timeout=30.0) as client:
        print('定位物体: 红色杯子')
        r = await client.post('/vision/locate_object', json={
            'object_name': '红色杯子'
        })
        data = r.json()
        
        if data['success'] and data.get('found'):
            print(f'✓ 物体已找到')
            print(f'  位置: {data[\"position\"]}')
            print(f'  置信度: {data[\"confidence\"]}%')
            print(f'  描述: {data[\"description\"]}')
        else:
            print(f'✗ 未找到物体')

asyncio.run(test_locate())
"
```

---

### 阶段5: 完整抓取测试

#### 测试5.1: 基于名称的抓取
```bash
# 使用完整测试脚本
python test_real_baxter_grasp.py
```

这个脚本会执行完整的测试序列：
1. 基础控制测试
2. 夹爪控制测试
3. 视觉识别测试
4. 完整抓取任务

**预期流程**:
```
1. 连接机器人 ✓
2. 使能机器人 ✓
3. 校准夹爪 ✓
4. 识别物体 ✓
5. 移动到物体上方 ✓
6. 下降并抓取 ✓
7. 提升物体 ✓
8. 移动到放置位置 ✓
9. 放下物体 ✓
10. 返回Home ✓
```

#### 测试5.2: 手动抓取测试
```bash
# 交互式测试
python -c "
import httpx
import asyncio

async def pick_and_place():
    async with httpx.AsyncClient(base_url='http://localhost:8420', timeout=60.0) as client:
        # 1. 使能
        print('1. 使能机器人...')
        await client.post('/enable')
        
        # 2. 打开夹爪
        print('2. 打开夹爪...')
        await client.post('/primitives/gripper', json={'arm': 'right', 'command': 'open'})
        
        # 3. 基于名称抓取
        print('3. 抓取物体...')
        r = await client.post('/primitives/pick_by_name', json={
            'object_name': '红色杯子',
            'arm': 'right'
        })
        print(r.json())
        
        # 4. 放置
        print('4. 放置物体...')
        r = await client.post('/primitives/place', json={
            'arm': 'right',
            'position': [0.5, -0.3, 0.0]
        })
        print(r.json())
        
        # 5. 返回Home
        print('5. 返回Home...')
        await client.post('/primitives/home', json={'arm': 'right'})
        
        print('✓ 测试完成')

asyncio.run(pick_and_place())
"
```

---

### 阶段6: 双臂协作测试

#### 测试6.1: 双臂Home
```bash
python -c "
import httpx
client = httpx.Client(base_url='http://localhost:8420')

print('双臂返回Home...')
r = client.post('/primitives/home', json={'arm': 'both'})
print(r.json())
"
```

#### 测试6.2: 双臂抓取大物体
```bash
python test_dual_arm_plugin.py
```

---

### 阶段7: Web界面测试

#### 测试7.1: 启动Web界面
```bash
# 确保Bridge Server正在运行
# 在新终端
cd ~/Baxter-claw
conda activate baxter-claw
python openclaw_plugin/web_interface.py
```

**预期输出**:
```
============================================================
Baxter-Claw Web 界面
============================================================

启动中...

请在浏览器中打开: http://localhost:5000

按 Ctrl+C 停止服务器
============================================================
```

#### 测试7.2: 浏览器测试
1. 打开浏览器访问 `http://localhost:5000`
2. 测试文本输入: "看看桌上有什么"
3. 测试语音输入: 点击"🎤 语音"按钮，说"打开夹爪"
4. 测试语音反馈: 开启右上角开关
5. 测试摄像头: 点击"刷新图像"

---

### 阶段8: OpenClaw Plugin测试

#### 测试8.1: 插件功能测试
```bash
python openclaw_plugin/test_plugin.py
```

#### 测试8.2: LLM意图识别测试
```bash
python openclaw_plugin/test_llm_intent.py
```

#### 测试8.3: 动态工作流测试
```bash
python openclaw_plugin/test_dynamic_workflow.py
```

---

## 完整测试脚本

我将创建一个自动化测试脚本来执行所有测试...

