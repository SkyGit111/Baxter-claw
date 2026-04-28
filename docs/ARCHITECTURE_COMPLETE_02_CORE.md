# Baxter-Claw 完整架构文档 - 第2节：核心架构详解

## 2. 核心架构组件

### 2.1 Bridge Server (bridge/server.py)

Bridge Server 是系统的核心 API 服务器，基于 FastAPI 实现。

#### 2.1.1 职责

- 提供 REST API 接口
- 管理机器人连接和状态
- 路由请求到对应的 Primitive
- 处理异常和错误响应

#### 2.1.2 主要端点

**控制端点**：
```python
POST /enable          # 使能机器人
POST /disable         # 禁用机器人
GET  /status          # 获取机器人状态
```

**动作原语端点**：
```python
POST /primitives/pick           # 抓取（已知位置）
POST /primitives/place          # 放置（指定位置）
POST /primitives/place_by_name  # 放置（相对物体）
POST /primitives/move_to        # 移动到位置
POST /primitives/home           # 回到原位
POST /primitives/gripper        # 夹爪控制
```

**视觉端点**：
```python
POST /vision/pick_by_name       # 视觉引导抓取
POST /vision/locate_object      # 定位物体
POST /vision/locate_multiview   # 多视角定位
GET  /vision/describe           # 场景描述
GET  /vision/identify           # 识别物体
```

**双臂端点**：
```python
POST /dualarm/bimanual_pick     # 双臂抓取
POST /dualarm/handover          # 手臂间传递
POST /dualarm/synchronized_move # 同步移动
```

**相机端点**：
```python
GET /camera?camera=d455         # 获取相机图像
GET /camera?camera=right_hand   # 获取手腕相机图像
```

#### 2.1.3 启动流程

```python
# 1. 解析命令行参数
parser.add_argument("--config", ...)
parser.add_argument("--enable-grasp-verification", ...)

# 2. 初始化 ArmManager
manager = ArmManager(
    config_path=args.config,
    enable_grasp_verification=args.enable_grasp_verification,
    grasp_verify_retries=args.grasp_verify_retries
)

# 3. 启动 FastAPI 服务器
uvicorn.run(app, host=args.host, port=args.port)
```

#### 2.1.4 配置选项

```bash
# 基础启动
python start_server.py

# 指定配置文件
python start_server.py --config config/baxter.yaml

# 启用抓取验证
python start_server.py --enable-grasp-verification --grasp-verify-retries 3

# 自定义端口
python start_server.py --port 8421
```

### 2.2 ArmManager (bridge/arm_manager.py)

ArmManager 负责机器人的生命周期管理和组件协调。

#### 2.2.1 职责

- 初始化所有组件（Driver、Safety、VLM、Primitives）
- 管理机器人连接状态
- 协调各组件之间的交互
- 处理配置文件

#### 2.2.2 组件初始化顺序

```python
def __init__(self, config_path, enable_grasp_verification, grasp_verify_retries):
    # 1. 加载配置
    self.config = self._load_config(config_path)
    
    # 2. 创建驱动
    self.driver = self._create_driver()  # BaxterDriver 或 MockDriver
    
    # 3. 创建安全验证器
    self.safety = SafetyValidator(config_path)
    
    # 4. 创建 VLM 客户端
    self.vlm_client = self._create_vlm_client()
    
    # 5. 创建抓取验证器（可选）
    self.grasp_verifier = self._create_grasp_verifier(...)
    
    # 6. 创建碰撞检测器（可选）
    self.collision_detector = self._create_collision_detector()
    
    # 7. 创建动作原语
    self.primitives = BaxterPrimitives(
        self.driver,
        self.safety,
        self.vlm_client,
        grasp_verifier=self.grasp_verifier,
        collision_detector=self.collision_detector
    )
```

#### 2.2.3 配置文件结构

```yaml
# config/baxter.yaml
driver:
  type: baxter  # 或 mock
  use_depth_camera: true

robot:
  arms: [left, right]

vlm:
  provider: qwen  # 或 openai, claude
  api_key: ${QWEN_API_KEY}

safety:
  workspace_limits:
    x: [0.3, 1.0]
    y: [-0.8, 0.8]
    z: [-0.3, 0.5]

experimental:
  grasp_verification:
    enabled: false
    max_retries: 2
    debug: true
  
  collision_detection:
    enabled: false
    position_threshold: 0.005
    stagnation_duration: 2.0
```

### 2.3 Primitives (bridge/primitives.py)

Primitives 层实现了所有高层动作原语。

#### 2.3.1 核心原语

**1. pick(arm, position, approach_height, speed)**
- 在已知位置抓取物体
- 执行流程：
  1. 检查可达性
  2. 移动到预抓取位置（上方）
  3. 打开夹爪
  4. 下降到目标位置
  5. 关闭夹爪
  6. 抬起物体

**2. place(arm, position, approach_height, speed)**
- 放置物体到指定位置
- 执行流程：
  1. 抬升到安全高度
  2. 水平移动到目标上方
  3. 下降到目标位置
  4. 打开夹爪
  5. 向上撤回

**3. pick_by_name(arm, object_name, use_d455)**
- 视觉引导抓取
- 执行流程：
  1. 使用 VLM 定位物体
  2. 自动选择手臂（如果 arm='auto'）
  3. 调用 pick() 执行抓取
  4. （可选）验证抓取成功

**4. place_by_name(arm, target_object_name, relative_position)**
- 相对物体放置
- 执行流程：
  1. 使用 VLM 定位目标物体
  2. 计算相对位置（next_to/on_top/behind/in_front）
  3. 调用 place() 执行放置

**5. move_to(arm, position, orientation, speed)**
- 移动到指定位姿

**6. home(arm)**
- 回到预定义的原位

**7. gripper_command(arm, command, force)**
- 夹爪控制（open/close）

#### 2.3.2 双臂原语

**1. bimanual_pick(object_name)**
- 双臂协同抓取大物体

**2. handover(from_arm, to_arm)**
- 手臂间传递物体

**3. synchronized_move(left_position, right_position)**
- 双臂同步移动

#### 2.3.3 Home 位姿

```python
self.home_positions = {
    'right': {
        'right_s0': -0.456743,
        'right_s1': -1.424685,
        'right_e0': -0.282252,
        'right_e1': 2.226190,
        'right_w0': -0.052922,
        'right_w1': 1.343000,
        'right_w2': -0.008820,
    },
    'left': {
        'left_s0': 0.456743,   # 镜像对称
        'left_s1': -1.424685,
        'left_e0': 0.282252,
        'left_e1': 2.226190,
        'left_w0': 0.052922,
        'left_w1': 1.343000,
        'left_w2': 0.008820,
    }
}
```

这个位姿的特点：
- 手臂向后收起，避免遮挡相机视野
- 高度抬起，避免与桌面碰撞
- 左右对称，便于维护

### 2.4 Driver 层 (bridge/drivers/)

Driver 层抽象了硬件接口，支持真机和仿真。

#### 2.4.1 驱动架构

```python
# 基类
class ArmDriver(ABC):
    @abstractmethod
    def connect(self) -> bool: pass
    
    @abstractmethod
    def move_to_pose(self, arm, pose, speed) -> bool: pass
    
    @abstractmethod
    def gripper_command(self, arm, command) -> bool: pass
    
    # ... 其他抽象方法

# 真机驱动
class BaxterDriver(ArmDriver):
    def __init__(self, use_depth_camera=True):
        self._limbs = {}
        self._grippers = {}
        self._depth_camera = None
        self._ik_solver = None
    
    def connect(self):
        # 初始化 ROS 节点
        rospy.init_node('baxter_claw_bridge')
        
        # 初始化手臂接口
        self._limbs['right'] = baxter_interface.Limb('right')
        self._limbs['left'] = baxter_interface.Limb('left')
        
        # 初始化夹爪并校准
        self._grippers['right'] = baxter_interface.Gripper('right')
        self._grippers['left'] = baxter_interface.Gripper('left')
        self._grippers['right'].calibrate()
        self._grippers['left'].calibrate()
        
        # 初始化深度相机
        if use_depth_camera:
            self._depth_camera = RealSenseDriver()

# 仿真驱动
class MockDriver(ArmDriver):
    def __init__(self):
        self._mock_state = {...}
    
    def move_to_pose(self, arm, pose, speed):
        # 模拟运动，更新状态
        self._mock_state[arm]['pose'] = pose
        return True
```

#### 2.4.2 BaxterDriver 关键功能

**1. 运动控制**
```python
def move_to_pose(self, arm, pose, speed, retry_with_perturbation=True):
    # 1. 尝试增强 IK 求解器
    if self._ik_solver:
        joint_angles = self._ik_solver.solve_ik_with_fallback(arm, pose, max_attempts=10)
    else:
        joint_angles = self._solve_basic_ik(arm, pose)
    
    # 2. 如果失败，尝试位置扰动
    if joint_angles is None and retry_with_perturbation:
        joint_angles = self._solve_ik_with_perturbations(arm, pose)
    
    # 3. 执行运动
    if joint_angles:
        return self.move_to_joint_positions(arm, joint_angles, speed)
    
    return False
```

**2. 可达性检查**
```python
def check_pose_reachable(self, arm, pose, silent=False):
    # 尝试 IK 求解，不实际移动
    joint_angles = self._solve_basic_ik(arm, pose)
    return joint_angles is not None
```

**3. 手臂自动选择**
```python
def select_arm_by_y_coordinate(self, position, y_threshold=0.0):
    y = position[1]
    if y < y_threshold:
        return 'right'
    else:
        return 'left'
```

#### 2.4.3 RealSenseDriver (深度相机)

```python
class RealSenseDriver:
    def __init__(self, width=640, height=480, fps=30):
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        
        # 配置流
        self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
        self.config.enable_stream(rs.stream.color, width, height, rs.format.rgb8, fps)
        
        # 启动
        self.profile = self.pipeline.start(self.config)
        
        # 对齐深度到彩色
        self.align = rs.align(rs.stream.color)
    
    def capture_rgbd(self):
        frames = self.pipeline.wait_for_frames()
        aligned_frames = self.align.process(frames)
        
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        
        return color_image, depth_image
```

---

**下一节**：[第3节：视觉系统](ARCHITECTURE_COMPLETE_03_VISION.md)
