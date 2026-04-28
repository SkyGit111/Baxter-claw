# Baxter-Claw 完整架构文档 - 第5节：安全系统

## 5. 安全系统

### 5.1 安全架构概述

Baxter-Claw 实现了多层安全验证机制，确保机器人在安全范围内操作，避免碰撞、超限和意外情况。

#### 5.1.1 安全层次

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: 工作空间限制 (Workspace Limits)               │
│  - 检查目标位置是否在允许范围内                          │
│  - 防止手臂移动到危险区域                                │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: 可达性检查 (Reachability Check)               │
│  - IK 求解验证目标位姿是否可达                           │
│  - 避免无效运动指令                                      │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 3: 运动安全 (Motion Safety)                      │
│  - 速度限制                                              │
│  - 平滑运动轨迹                                          │
│  - 避免突然加速/减速                                     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 4: 碰撞检测 (Collision Detection, 实验性)        │
│  - 实时监测手臂位置                                      │
│  - 检测运动停滞（可能碰撞）                              │
│  - 自动停止并报警                                        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 5: 抓取验证 (Grasp Verification, 实验性)         │
│  - 验证抓取是否成功                                      │
│  - 失败自动重试                                          │
│  - 避免空抓                                              │
└─────────────────────────────────────────────────────────┘
```

### 5.2 SafetyValidator (bridge/safety.py)

SafetyValidator 实现了工作空间限制和基础安全检查。

#### 5.2.1 工作空间定义

```python
class SafetyValidator:
    def __init__(self, config_path=None):
        # 默认工作空间（单位：米）
        self.workspace_limits = {
            'x': [0.3, 1.0],   # 前后：30cm 到 1m
            'y': [-0.8, 0.8],  # 左右：±80cm
            'z': [-0.3, 0.5],  # 上下：-30cm 到 50cm
        }
        
        # 从配置文件加载（如果有）
        if config_path:
            self._load_config(config_path)
```

可视化工作空间：

```
        Z ↑
          |
          |     工作空间
          |   ┌─────────┐
          |   │         │  0.5m
          |   │         │
    ──────┼───┼─────────┼──────→ X
   -0.3m  |   │         │  1.0m
          |   │         │
          |   └─────────┘
          |  -0.8m    0.8m
          |
         Y ⊙ (指向屏幕外)
```

#### 5.2.2 安全检查方法

**1. check_workspace(arm, pose)**
```python
def check_workspace(self, arm: str, pose: List[float]) -> Tuple[bool, str]:
    """检查位姿是否在工作空间内"""
    x, y, z = pose[0], pose[1], pose[2]
    
    # 检查 X 轴
    if not (self.workspace_limits['x'][0] <= x <= self.workspace_limits['x'][1]):
        return False, f"X={x:.3f}m 超出范围 {self.workspace_limits['x']}"
    
    # 检查 Y 轴
    if not (self.workspace_limits['y'][0] <= y <= self.workspace_limits['y'][1]):
        return False, f"Y={y:.3f}m 超出范围 {self.workspace_limits['y']}"
    
    # 检查 Z 轴
    if not (self.workspace_limits['z'][0] <= z <= self.workspace_limits['z'][1]):
        return False, f"Z={z:.3f}m 超出范围 {self.workspace_limits['z']}"
    
    return True, "OK"
```

**2. check_collision_risk(arm, pose)**
```python
def check_collision_risk(self, arm: str, pose: List[float]) -> Tuple[bool, str]:
    """检查是否有碰撞风险"""
    x, y, z = pose[0], pose[1], pose[2]
    
    # 检查是否太靠近桌面
    if z < -0.25:
        return False, f"Z={z:.3f}m 太低，可能碰撞桌面"
    
    # 检查是否太靠近机器人基座
    if x < 0.4 and abs(y) < 0.3:
        return False, "太靠近机器人基座"
    
    # 检查左右手臂是否太近（双臂协同时）
    # TODO: 实现双臂碰撞检测
    
    return True, "OK"
```

#### 5.2.3 在 Primitives 中的应用

```python
# 在 pick() 中
def pick(self, arm, position, approach_height, speed):
    # 1. 检查预抓取位置
    pre_grasp_pose = position.copy()
    pre_grasp_pose[2] += approach_height
    
    is_safe, msg = self.safety.check_workspace(arm, pre_grasp_pose + orientation)
    if not is_safe:
        return {"success": False, "message": f"Pre-grasp pose unsafe: {msg}"}
    
    # 2. 检查目标位置
    target_pose = position + orientation
    is_safe, msg = self.safety.check_workspace(arm, target_pose)
    if not is_safe:
        return {"success": False, "message": f"Target pose unsafe: {msg}"}
    
    # 3. 执行运动
    # ...
```

### 5.3 CollisionDetector (bridge/collision_detector.py)

CollisionDetector 是实验性功能，通过监测手臂位置变化检测碰撞。

#### 5.3.1 检测原理

```
正常运动：位置持续变化
    t0: [0.5, 0.0, 0.1]
    t1: [0.52, 0.0, 0.1]  ← 移动了 2cm
    t2: [0.54, 0.0, 0.1]  ← 移动了 2cm
    ✓ 正常

碰撞/卡住：位置停滞
    t0: [0.5, 0.0, 0.1]
    t1: [0.501, 0.0, 0.1]  ← 只移动了 1mm
    t2: [0.501, 0.0, 0.1]  ← 没有移动
    t3: [0.501, 0.0, 0.1]  ← 没有移动
    ✗ 可能碰撞！
```

#### 5.3.2 实现

```python
class CollisionDetector:
    def __init__(
        self,
        enabled: bool = False,
        position_threshold: float = 0.005,  # 5mm
        stagnation_duration: float = 2.0,   # 2秒
        sample_interval: float = 0.2,       # 200ms
        min_samples: int = 3
    ):
        self.enabled = enabled
        self.position_threshold = position_threshold
        self.stagnation_duration = stagnation_duration
        self.sample_interval = sample_interval
        self.min_samples = min_samples
        
        self.position_history = []
    
    def start_monitoring(self, arm: str):
        """开始监测手臂运动"""
        if not self.enabled:
            return
        
        self.position_history = []
        self.monitoring_arm = arm
        self.start_time = time.time()
    
    def check_collision(self, driver) -> Tuple[bool, str]:
        """检查是否发生碰撞"""
        if not self.enabled:
            return False, "Monitoring disabled"
        
        # 获取当前位置
        current_pose = driver.get_endpoint_pose(self.monitoring_arm)
        if current_pose is None:
            return False, "Cannot get pose"
        
        current_position = current_pose[:3]
        current_time = time.time()
        
        # 记录历史
        self.position_history.append({
            'position': current_position,
            'time': current_time
        })
        
        # 保留最近的样本
        cutoff_time = current_time - self.stagnation_duration
        self.position_history = [
            h for h in self.position_history 
            if h['time'] >= cutoff_time
        ]
        
        # 样本不足
        if len(self.position_history) < self.min_samples:
            return False, "Insufficient samples"
        
        # 计算位置变化
        positions = [h['position'] for h in self.position_history]
        max_displacement = self._calculate_max_displacement(positions)
        
        # 判断是否停滞
        if max_displacement < self.position_threshold:
            return True, f"Position stagnant (displacement: {max_displacement*1000:.1f}mm)"
        
        return False, "OK"
    
    def _calculate_max_displacement(self, positions):
        """计算最大位移"""
        if len(positions) < 2:
            return 0.0
        
        max_disp = 0.0
        for i in range(len(positions)):
            for j in range(i+1, len(positions)):
                disp = np.linalg.norm(
                    np.array(positions[i]) - np.array(positions[j])
                )
                max_disp = max(max_disp, disp)
        
        return max_disp
```

#### 5.3.3 使用方式

```python
# 在 move_to_pose 中
def move_to_pose(self, arm, pose, speed):
    # 启动碰撞监测
    if self.collision_detector:
        self.collision_detector.start_monitoring(arm)
    
    # 执行运动
    success = self._execute_motion(arm, pose, speed)
    
    # 运动过程中定期检查
    while self._is_moving(arm):
        if self.collision_detector:
            collision, msg = self.collision_detector.check_collision(self.driver)
            if collision:
                print(f"[CollisionDetector] ✗ Collision detected: {msg}")
                self.driver.stop_motion(arm)
                return False
        
        time.sleep(0.1)
    
    return success
```

### 5.4 GraspVerifier (bridge/grasp_verifier.py)

GraspVerifier 是实验性功能，验证抓取是否成功。

#### 5.4.1 验证流程

```python
async def verify_grasp(self, arm: str, object_name: str) -> Dict[str, Any]:
    # 1. 捕获手腕相机图像
    camera_name = f"{arm}_hand"
    image_bytes = self.driver.capture_image(camera_name)
    
    # 2. 构建验证 prompt
    prompt = f"""看这张机器人夹爪的手腕相机图像。

机器人刚刚尝试抓取：{object_name}

你的任务：判断夹爪是否成功抓住了物体。

检查：
1. 物体是否在夹爪指间可见？
2. 夹爪是否闭合在物体周围？
3. 物体是否被牢固抓住？

返回 JSON：
{{
    "holding_object": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "简要说明"
}}"""
    
    # 3. 调用 VLM
    vlm_response = await self.vlm.query_image(image_bytes, prompt)
    
    # 4. 解析响应
    result = self._parse_vlm_response(vlm_response)
    
    return result
```

#### 5.4.2 自动重试

```python
async def verify_and_retry_if_needed(
    self,
    arm: str,
    object_name: str,
    pick_function: Callable,
    pick_params: Dict
) -> Dict[str, Any]:
    attempts = 0
    
    while attempts < self.max_retries:
        attempts += 1
        
        # 验证当前抓取
        verification = await self.verify_grasp(arm, object_name)
        
        if verification['success']:
            return {
                'success': True,
                'attempts': attempts,
                'verification_result': verification
            }
        
        # 失败，重试
        if attempts < self.max_retries:
            print(f"[GraspVerifier] Retrying pick operation...")
            
            # 打开夹爪释放
            self.driver.gripper_command(arm, "open")
            await asyncio.sleep(0.5)
            
            # 重新抓取
            result = await pick_function(**pick_params)
            if not result.get('success'):
                break
            
            await asyncio.sleep(1.0)
    
    return {
        'success': False,
        'attempts': attempts,
        'verification_result': verification
    }
```

### 5.5 IK Solver 增强 (bridge/ik_solver.py)

增强的 IK 求解器提高了运动成功率。

#### 5.5.1 多策略求解

```python
class EnhancedIKSolver:
    def solve_ik_with_fallback(self, arm, pose, max_attempts=10):
        # 策略 1: 标准 IK
        joint_angles = self._solve_basic_ik(arm, pose)
        if joint_angles:
            return joint_angles
        
        # 策略 2: 位置扰动
        for i in range(max_attempts):
            perturbed_pose = self._perturb_pose(pose, magnitude=0.01)
            joint_angles = self._solve_basic_ik(arm, perturbed_pose)
            if joint_angles:
                return joint_angles
        
        # 策略 3: 姿态调整
        for roll_offset in [-0.1, 0.1, -0.2, 0.2]:
            adjusted_pose = pose.copy()
            adjusted_pose[3] += roll_offset  # 调整 roll
            joint_angles = self._solve_basic_ik(arm, adjusted_pose)
            if joint_angles:
                return joint_angles
        
        return None
```

### 5.6 安全配置

#### 5.6.1 配置文件

```yaml
# config/baxter.yaml
safety:
  workspace_limits:
    x: [0.3, 1.0]
    y: [-0.8, 0.8]
    z: [-0.3, 0.5]
  
  max_speed: 0.5
  
  collision_check: true

experimental:
  collision_detection:
    enabled: false
    position_threshold: 0.005
    stagnation_duration: 2.0
  
  grasp_verification:
    enabled: false
    max_retries: 2
```

#### 5.6.2 运行时启用

```bash
# 启用抓取验证
python start_server.py --enable-grasp-verification

# 启用碰撞检测（通过配置文件）
# 修改 config/baxter.yaml 中 collision_detection.enabled = true
```

---

**下一节**：[第6节：部署和测试](ARCHITECTURE_COMPLETE_06_DEPLOYMENT.md)
